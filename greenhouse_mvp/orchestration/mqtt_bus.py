"""
Thread-safe MQTT bus with Pydantic v2 schema validation.

Every message is serialised/deserialised at the bus boundary so that
application code never sees raw dicts or bytes.

Topic map (see plan/01_schemas_and_mqtt.md):
  greenhouse/telemetry          QoS 0  TelemetryPayload
  greenhouse/action/proposed    QoS 1  ActionPayload
  greenhouse/action/approved    QoS 1  ActionPayload
  greenhouse/supervisor/verdict QoS 1  SupervisorVerdict
  greenhouse/ood/metrics        QoS 0  OODMetrics
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Exponential back-off delays in seconds (5 attempts).
_RECONNECT_DELAYS = [1, 2, 4, 8, 16]


class MQTTBus:
    """
    Thin, schema-enforcing wrapper around ``paho.mqtt.client.Client``.

    Usage::

        bus = MQTTBus(host="localhost", port=1883)
        bus.subscribe("greenhouse/telemetry", TelemetryPayload, on_telemetry)
        bus.loop_start()
        ...
        bus.publish("greenhouse/action/proposed", action_payload, qos=1)
        ...
        bus.loop_stop()
    """

    def __init__(self, host: str, port: int = 1883) -> None:
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        # topic -> (schema_class, handler)
        self._subscriptions: dict[str, tuple[type[BaseModel], Callable[[BaseModel], None], int]] = {}
        self._reconnect_attempt = 0
        self._stopping = False

        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        self._client.connect(host, port)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(self, topic: str, payload: BaseModel, qos: int = 0) -> None:
        """Serialise *payload* to JSON and publish on *topic*."""
        data: bytes = payload.model_dump_json().encode("utf-8")
        self._client.publish(topic, data, qos=qos)

    def subscribe(
        self,
        topic: str,
        schema: type[BaseModel],
        handler: Callable[[BaseModel], None],
        qos: int = 0,
    ) -> None:
        """
        Register a typed handler for *topic*.

        Deserialisation and validation happen in ``on_message`` before the
        handler is invoked.  If validation fails the message is discarded
        (fail-safe) and an error is logged.
        """
        with self._lock:
            self._subscriptions[topic] = (schema, handler, qos)
        self._client.subscribe(topic, qos=qos)

    def loop_start(self) -> None:
        """Start the Paho background network thread."""
        self._stopping = False
        self._client.loop_start()

    def loop_stop(self) -> None:
        """Gracefully stop the background network thread and disconnect."""
        self._stopping = True
        self._client.loop_stop()
        self._client.disconnect()

    # ------------------------------------------------------------------
    # Paho callbacks
    # ------------------------------------------------------------------

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        rc: int,
    ) -> None:
        if rc == 0:
            logger.info("MQTT connected to %s:%s", self._host, self._port)
            self._reconnect_attempt = 0
            # Re-subscribe after reconnect.
            with self._lock:
                subs = list(self._subscriptions.items())
            for topic, (_, _, qos) in subs:
                client.subscribe(topic, qos=qos)
        else:
            logger.error("MQTT connection refused (rc=%s)", rc)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
    ) -> None:
        if self._stopping:
            logger.info("MQTT disconnected (intentional).")
            return
        logger.warning("MQTT unexpectedly disconnected (rc=%s). Scheduling reconnect.", rc)
        self._schedule_reconnect()

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        topic: str = msg.topic
        with self._lock:
            entry = self._subscriptions.get(topic)
        if entry is None:
            logger.debug("Received message on unregistered topic %s – ignoring.", topic)
            return

        schema, handler, _ = entry
        try:
            validated = schema.model_validate_json(msg.payload)
        except (ValidationError, ValueError) as exc:
            logger.error(
                "Validation error for topic %s (schema=%s): %s",
                topic,
                schema.__name__,
                exc,
            )
            return  # Fail-safe: do not invoke handler with invalid data.

        try:
            handler(validated)
        except Exception:
            logger.exception("Handler for topic %s raised an unhandled exception.", topic)

    # ------------------------------------------------------------------
    # Reconnect logic
    # ------------------------------------------------------------------

    def _schedule_reconnect(self) -> None:
        attempt = self._reconnect_attempt
        if attempt >= len(_RECONNECT_DELAYS):
            logger.error("MQTT: max reconnect attempts (%s) exceeded. Giving up.", len(_RECONNECT_DELAYS))
            return
        delay = _RECONNECT_DELAYS[attempt]
        self._reconnect_attempt += 1
        logger.info("MQTT reconnect attempt %s/%s in %ss.", attempt + 1, len(_RECONNECT_DELAYS), delay)

        def _reconnect() -> None:
            time.sleep(delay)
            if self._stopping:
                return
            try:
                self._client.reconnect()
            except Exception as exc:
                logger.error("MQTT reconnect failed: %s", exc)
                self._schedule_reconnect()

        thread = threading.Thread(target=_reconnect, daemon=True, name=f"mqtt-reconnect-{attempt}")
        thread.start()
