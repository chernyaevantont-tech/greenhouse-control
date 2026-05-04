"""
SimAdapter — wraps gl_gym/GreenLightTomato-v0 in a synchronous, event-driven
shell that participates in the MQTT bus as a cyber-physical device.

The simulation thread is blocked via threading.Event until the orchestration
layer publishes an approved action on ``greenhouse/action/approved``.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import gl_gym  # noqa: F401 — registers gl_gym namespace with gymnasium
import gymnasium as gym
import numpy as np

from greenhouse_mvp.orchestration.mqtt_bus import MQTTBus
from greenhouse_mvp.orchestration.schemas import ActionPayload, SimControlPayload, TelemetryPayload

logger = logging.getLogger(__name__)


class SimAdapter:
    """
    Wraps a GreenLight gym environment and bridges it to the MQTT bus.

    * ``loop_forever()`` must be called from the **main thread** — it blocks
      until the episode ends.
    * ``on_action_approved()`` is registered as an MQTT callback and is
      invoked from the **Paho network thread**.  It is intentionally
      non-blocking: it just stores the action and fires an event.

    Thread safety note
    ------------------
    ``_pending_action`` is written from the MQTT thread and read from the main
    thread.  In CPython, assignment of a reference is atomic (GIL), so no
    explicit lock is needed for this single-writer / single-reader pattern.
    If porting to a non-CPython runtime, wrap the write/read in a
    ``threading.Lock``.
    """

    def __init__(
        self,
        bus: MQTTBus,
        env_id: str = "gl_gym/GreenLightTomato-v0",
        start_date: str = "2010-02-28",
        n_days: int = 60,
        period: int = 900,
        action_timeout_s: float = 30.0,
    ) -> None:
        self._bus = bus
        self._env_id = env_id
        self._start_date = start_date
        self._n_days = n_days
        self._period = period
        self._action_timeout_s = action_timeout_s

        self._env: Optional[gym.Env] = None
        self._action_event = threading.Event()
        self._pending_action: Optional[np.ndarray] = None
        self._step = 0
        self._done = False

        # Speed / pause control (written from MQTT thread, read from main thread)
        self._pause_event = threading.Event()
        self._pause_event.set()          # start unpaused
        self._step_sleep_s: float = 0.5  # at 1× speed: 0.5 s between steps

        # Register MQTT subscription for approved actions.
        bus.subscribe(
            topic="greenhouse/action/approved",
            schema=ActionPayload,
            handler=self.on_action_approved,
            qos=1,
        )

        # Speed / pause control from dashboard
        bus.subscribe(
            topic="greenhouse/control/speed",
            schema=SimControlPayload,
            handler=self._on_speed_control,
            qos=1,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def loop_forever(self) -> None:
        """
        Run the blocking simulation loop.  Call from the main thread.

        Flow per step:
        1. Observe current state, build TelemetryPayload.
        2. Publish telemetry on ``greenhouse/telemetry``.
        3. Block on ``_action_event`` until an approved action arrives or
           ``action_timeout_s`` elapses.
        4. Step the environment.
        5. Repeat until episode ends.
        """
        self._env = gym.make(
            self._env_id,
            normalize_actions=False,
            observation_modules=[
                "IndoorClimateObservations",
                "WeatherObservations",
                "BasicCropObservations",
            ],
            season_length=self._n_days,
        )

        obs, _ = self._env.reset(options={"start_date": self._start_date}, seed=42)
        self._step = 0
        self._done = False

        self._publish_telemetry(obs, step=0)

        while not self._done:
            arrived = self._action_event.wait(timeout=self._action_timeout_s)
            self._action_event.clear()

            if not arrived:
                logger.warning(
                    "Action timeout at step %d. Using fallback.", self._step
                )
                action_vec = self._safe_fallback_action()
            else:
                action_vec = self._pending_action  # type: ignore[assignment]

            try:
                obs, _reward, terminated, truncated, _info = self._env.step(
                    action_vec
                )
            except Exception:
                logger.exception(
                    "env.step() raised an exception at step %d.", self._step
                )
                self._done = True
                raise

            self._step += 1
            self._done = terminated or truncated

            # Speed control: block while paused, then sleep proportionally
            self._pause_event.wait()
            import time as _time
            _sleep = self._step_sleep_s
            if _sleep > 0:
                _time.sleep(_sleep)

            if not self._done:
                self._publish_telemetry(obs, step=self._step)

        logger.info("Episode finished after %d steps.", self._step)

    def reset(self, seed: Optional[int] = 42) -> TelemetryPayload:
        """Re-initialise the environment and return the initial telemetry."""
        if self._env is None:
            self._env = gym.make(
                self._env_id,
                normalize_actions=False,
                observation_modules=[
                    "IndoorClimateObservations",
                    "WeatherObservations",
                    "BasicCropObservations",
                ],
                season_length=self._n_days,
            )

        obs, _ = self._env.reset(options={"start_date": self._start_date}, seed=seed)
        self._step = 0
        self._done = False
        return self._build_telemetry(obs, step=0)

    def close(self) -> None:
        """Tear down the gym environment and disconnect from the bus."""
        if self._env is not None:
            self._env.close()
            self._env = None
        self._bus.loop_stop()

    # ------------------------------------------------------------------
    # MQTT callback (called from Paho network thread)
    # ------------------------------------------------------------------

    def _on_speed_control(self, msg: SimControlPayload) -> None:
        """Called from Paho network thread when dashboard publishes a speed/pause command."""
        if msg.paused:
            self._pause_event.clear()
            logger.info("sim_adapter: paused by dashboard")
        else:
            self._pause_event.set()
            mult = max(0.1, min(20.0, msg.speed_multiplier))
            # BASE = 0.5 s at 1×; divide by multiplier for higher speeds
            self._step_sleep_s = 0.5 / mult
            logger.info("sim_adapter: speed set to %.2f× (sleep=%.3fs)", mult, self._step_sleep_s)

    def on_action_approved(self, msg: ActionPayload) -> None:
        """
        Invoked by ``MQTTBus`` when a message arrives on
        ``greenhouse/action/approved``.  Must be fast and non-blocking.
        """
        if msg.step != self._step:
            logger.warning(
                "Stale action for step %d (current: %d). Ignoring.",
                msg.step,
                self._step,
            )
            return

        if not msg.approved:
            logger.error("Received unapproved action on approved topic. Ignoring.")
            return

        self._pending_action = np.array(
            [msg.uBoil, msg.uCO2, msg.uThScr, msg.uVent, msg.uLamp, msg.uBlScr],
            dtype=np.float32,
        )
        self._action_event.set()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _publish_telemetry(self, obs: dict, step: int) -> None:
        telemetry = self._build_telemetry(obs, step)
        self._bus.publish("greenhouse/telemetry", telemetry, qos=0)

    def _build_telemetry(self, obs: dict, step: int) -> TelemetryPayload:
        """
        Map a raw gym observation dict to a ``TelemetryPayload``.

        Index mapping (verified against notebook):
          IndoorClimateObservations: [0]=co2_ppm, [1]=t_in, [2]=rh
          WeatherObservations:       [0]=rad, [1]=T_out, [2]=?, [3]=co2_out
        """
        indoor = obs["IndoorClimateObservations"]
        weather = obs["WeatherObservations"]

        hour_of_day = (step * self._period / 3600.0) % 24.0

        return TelemetryPayload(
            step=step,
            timestamp_sim=float(step * self._period),
            t_in=float(indoor[1]),
            co2=float(indoor[0]),
            rh=float(indoor[2]),
            T_out=float(weather[1]),
            rad=float(weather[0]),
            co2_out=float(weather[3]),
            sin_h=float(np.sin(2 * np.pi * hour_of_day / 24.0)),
            cos_h=float(np.cos(2 * np.pi * hour_of_day / 24.0)),
        )

    def _safe_fallback_action(self) -> np.ndarray:
        """
        Minimal safe action used when the orchestration layer times out.

        Keeps heating on at 30%, thermal screen closed, everything else off.
        [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
        """
        return np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)


if __name__ == "__main__":
    import os
    import signal

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from greenhouse_mvp.orchestration.mqtt_bus import MQTTBus

    _host = os.environ.get("MQTT_HOST", "localhost")
    _port = int(os.environ.get("MQTT_PORT", "1883"))
    _start_date = os.environ.get("START_DATE", "2010-02-28")
    _n_days = int(os.environ.get("N_DAYS", "60"))
    _period = int(os.environ.get("PERIOD", "900"))

    _bus = MQTTBus(host=_host, port=_port)
    _bus.loop_start()
    _adapter = SimAdapter(
        bus=_bus,
        start_date=_start_date,
        n_days=_n_days,
        period=_period,
    )

    # Give control_core and orchestration time to connect and subscribe
    import time
    logger.info("sim_adapter: waiting 15s for control_core and orchestration to subscribe...")
    time.sleep(15)

    def _shutdown(*_: object) -> None:
        logger.info("sim_adapter: shutdown signal received.")
        _adapter.close()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        _adapter.loop_forever()
    finally:
        _adapter.close()
