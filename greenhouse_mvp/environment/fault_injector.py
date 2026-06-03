"""
fault_injector.py — Configurable fault injection for sensors and actuators.

Faults are applied transparently to the simulation to stress-test the LLM
anomaly-detection capability.  The controller never sees the "real" signal;
it must infer faults from cross-sensor consistency and actuator-response checks.

Sensor faults  → applied to TelemetryPayload before it reaches the LLM.
Actuator faults → applied to the numpy action vector before it reaches gym.step().
"""

from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from greenhouse_mvp.orchestration.schemas import ActionPayload, FaultSpec, TelemetryPayload

logger = logging.getLogger(__name__)

_SENSOR_FIELDS    = {"t_in", "co2", "rh"}
_ACTUATOR_FIELDS  = {"uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"}
_ACTUATOR_ORDER   = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]


def _apply(original: float, fault: "FaultSpec") -> float:
    ft = fault.fault_type
    if ft == "stuck_high":
        return fault.value
    if ft == "stuck_low":
        return fault.value
    if ft == "random":
        return _random.uniform(fault.value_lo, fault.value_hi)
    if ft == "offset":
        return original + fault.value
    if ft == "dead":          # actuators only
        return 0.0
    if ft == "min_floor":     # actuator can't go below value
        return max(original, fault.value)
    if ft == "max_cap":       # actuator can't exceed value
        return min(original, fault.value)
    return original


class FaultInjector:
    """Apply a list of :class:`FaultSpec` instances to telemetry and action vectors.

    Usage::

        injector = FaultInjector(config.faults)

        # In the sim loop, before passing telemetry to LLM:
        telemetry = injector.inject_sensor(raw_telemetry, step)

        # Just before env.step(), after the LLM returned its action:
        action_vec = injector.inject_actuator(action_vec, step)
    """

    def __init__(self, faults: "list[FaultSpec]") -> None:
        self._faults = list(faults)
        if faults:
            summary = ", ".join(f"{f.target}({f.fault_type})" for f in faults)
            logger.info("FaultInjector: active faults = [%s]", summary)

    # ------------------------------------------------------------------

    def inject_sensor(
        self, telemetry: "TelemetryPayload", step: int
    ) -> "TelemetryPayload":
        """Return a new TelemetryPayload with sensor faults applied."""
        active = [f for f in self._faults if f.target in _SENSOR_FIELDS and step >= f.start_step]
        if not active:
            return telemetry
        data = telemetry.model_dump()
        for f in active:
            original = data[f.target]
            data[f.target] = _apply(original, f)
            logger.debug(
                "FaultInjector step=%d: sensor %s %s → %.2f (was %.2f)",
                step, f.target, f.fault_type, data[f.target], original,
            )
        from greenhouse_mvp.orchestration.schemas import TelemetryPayload as _TP
        return _TP(**data)

    def inject_actuator(
        self, action_vec: np.ndarray, step: int
    ) -> np.ndarray:
        """Return a new action vector with actuator faults applied."""
        active = [f for f in self._faults if f.target in _ACTUATOR_FIELDS and step >= f.start_step]
        if not active:
            return action_vec
        vec = action_vec.copy()
        for f in active:
            idx = _ACTUATOR_ORDER.index(f.target)
            original = float(vec[idx])
            vec[idx] = float(np.clip(_apply(original, f), 0.0, 1.0))
            logger.debug(
                "FaultInjector step=%d: actuator %s[%d] %s → %.2f (was %.2f)",
                step, f.target, idx, f.fault_type, vec[idx], original,
            )
        return vec

    # ------------------------------------------------------------------

    @property
    def has_faults(self) -> bool:
        return bool(self._faults)

    def active_faults_at(self, step: int) -> list["FaultSpec"]:
        return [f for f in self._faults if step >= f.start_step]

    def summary(self) -> list[dict]:
        return [f.model_dump() for f in self._faults]
