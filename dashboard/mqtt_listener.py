"""Background MQTT listener that writes incoming payloads into st.session_state."""

from __future__ import annotations

import sys
import os

import paho.mqtt.client as mqtt

# Allow importing schemas from the parent repo without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    OODMetrics,
    SupervisorVerdict,
    TelemetryPayload,
)
from dashboard.config import (
    TOPIC_ACTION_APPROVED,
    TOPIC_OOD_METRICS,
    TOPIC_SUPERVISOR_VERDICT,
    TOPIC_TELEMETRY,
)


# ---------------------------------------------------------------------------
# Individual payload handlers
# ---------------------------------------------------------------------------


def _handle_telemetry(ss: dict, p: TelemetryPayload) -> None:
    ss["steps"].append(p.step)
    ss["t_in"].append(p.t_in)
    ss["co2"].append(p.co2)
    ss["rh"].append(p.rh)
    ss["T_out"].append(p.T_out)
    ss["rad"].append(p.rad)


def _handle_action(ss: dict, p: ActionPayload) -> None:
    ss["uBoil"].append(p.uBoil)
    ss["uCO2"].append(p.uCO2)
    ss["uThScr"].append(p.uThScr)
    ss["uVent"].append(p.uVent)
    ss["uLamp"].append(p.uLamp)
    ss["uBlScr"].append(p.uBlScr)


def _handle_ood(ss: dict, p: OODMetrics) -> None:
    ss["mahal_dist"].append(p.mahalanobis_distance)
    ss["in_distribution"].append(p.in_distribution)
    ss["ood_threshold"] = p.threshold_used


def _handle_verdict(ss: dict, p: SupervisorVerdict) -> None:
    status = {
        "APPROVE": "🟢 SAFE",
        "OVERRIDE": "🟡 WARNING",
        "REJECT": "🔴 ALARM",
    }.get(p.decision, "⚪ UNKNOWN")
    ss["agent_log"].appendleft(
        {
            "step": p.step,
            "status": status,
            "decision": p.decision,
            "reason": p.reason,
            "confidence": p.confidence,
        }
    )


# ---------------------------------------------------------------------------
# Dispatch table: topic → (handler, schema)
# ---------------------------------------------------------------------------

TOPIC_MAP = {
    TOPIC_TELEMETRY: (_handle_telemetry, TelemetryPayload),
    TOPIC_ACTION_APPROVED: (_handle_action, ActionPayload),
    TOPIC_OOD_METRICS: (_handle_ood, OODMetrics),
    TOPIC_SUPERVISOR_VERDICT: (_handle_verdict, SupervisorVerdict),
}


# ---------------------------------------------------------------------------
# Listener class
# ---------------------------------------------------------------------------


class DashboardMQTTListener:
    """Connects to the MQTT broker and writes payloads into *session_state*."""

    def __init__(self, host: str, port: int, session_state: dict) -> None:
        self._ss = session_state
        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.connect(host, port)

    # ------------------------------------------------------------------
    # MQTT callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        self._ss["mqtt_connected"] = rc == 0
        if rc == 0:
            client.subscribe(TOPIC_TELEMETRY, qos=0)
            client.subscribe(TOPIC_ACTION_APPROVED, qos=1)
            client.subscribe(TOPIC_OOD_METRICS, qos=1)
            client.subscribe(TOPIC_SUPERVISOR_VERDICT, qos=1)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        self._ss["mqtt_connected"] = False

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        entry = TOPIC_MAP.get(msg.topic)
        if entry is None:
            return
        handler, schema = entry
        try:
            payload = schema.model_validate_json(msg.payload)
            handler(self._ss, payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[Dashboard MQTT] Parse error on {msg.topic}: {exc}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start a non-blocking network loop in its own daemon thread."""
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
