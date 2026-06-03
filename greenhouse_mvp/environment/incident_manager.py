"""
incident_manager.py — Manages greenhouse incidents / abnormal events.

Each IncidentSpec is a named, semantic event (e.g. "door_open", "heater_failure").
The manager translates it into two categories of physical effects:

  1. Actuator constraints  — applied to the numpy action vector AFTER the controller
     makes its decision, but BEFORE the gym.step() call.  This models actuator failures
     and mechanical limitations the controller cannot override.

  2. Physics disturbances  — applied to the TelemetryPayload BEFORE the controller
     sees it. This models uncontrolled environmental changes (door air exchange,
     irrigation humidity spike, etc.) that the gym physics cannot simulate on its own.

Usage in the simulation loop::

    mgr = IncidentManager()
    mgr.add(spec, current_step=step)

    # Before passing telemetry to the controller:
    telemetry = mgr.apply_to_telemetry(telemetry, step)

    # After controller produces action_vec, before env.step():
    action_vec = mgr.apply_to_action(action_vec, step)

    # Check for expired incidents:
    alerts = mgr.expire_check(step)   # returns list[IncidentAlert]
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from greenhouse_mvp.orchestration.schemas import (
        IncidentAlert,
        IncidentSpec,
        TelemetryPayload,
    )

logger = logging.getLogger(__name__)

_ACTUATOR_ORDER = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]


# ---------------------------------------------------------------------------
# Incident catalogue — static metadata for each incident type
# ---------------------------------------------------------------------------

INCIDENT_CATALOG: dict[str, dict] = {
    "door_open": {
        "label": "Door Open",
        "description": "Greenhouse door opened — uncontrolled air exchange with outside",
        "affected_systems": ["temperature", "co2", "humidity", "thermal_screen", "ventilation"],
        "repair_steps": [
            "Close the greenhouse door immediately",
            "Verify door latch mechanism is functional",
            "Inspect door seal / gasket for damage",
            "Increase boiler output to compensate for heat loss while door is open",
            "Increase CO2 injection — indoor CO2 is diluting toward ambient (~400 ppm)",
        ],
        "mitigation_hints": (
            "Door is open — uncontrolled air exchange with outside is occurring. "
            "Increase heating (uBoil) significantly to compensate for heat loss. "
            "Increase CO2 injection (uCO2) — indoor CO2 equalises with outside (~400 ppm). "
            "Thermal screen cannot close while door is open. "
            "Physical intervention required to close the door."
        ),
    },
    "heater_failure": {
        "label": "Heater Failure",
        "description": "Boiler heating system failure — heat output is zero regardless of commands",
        "affected_systems": ["heating", "temperature"],
        "repair_steps": [
            "Check boiler pressure gauge (should be 1.5–2.5 bar)",
            "Check fuel / gas supply — is the shut-off valve open?",
            "Reset thermal safety switch (red reset button on boiler body)",
            "Check ignition sequence / pilot light",
            "Call maintenance technician if above steps fail",
        ],
        "mitigation_hints": (
            "Boiler has failed — no heating available. "
            "Close thermal screen (uThScr=1) to minimise heat loss. "
            "Close ventilation (uVent=0) to retain warmth. "
            "Use lamps (uLamp) for supplemental heat if available. "
            "Alert immediately if t_in drops below 15 °C — crop is at risk."
        ),
    },
    "co2_supply_failure": {
        "label": "CO2 Supply Failure",
        "description": "CO2 supply system failure — CO2 injection has no effect",
        "affected_systems": ["co2", "crop_photosynthesis"],
        "repair_steps": [
            "Check CO2 tank pressure — may be empty",
            "Inspect CO2 supply line for blockages or leaks",
            "Verify solenoid valve on CO2 line is opening (listen/feel for flow)",
            "Switch to backup CO2 supply cylinder if available",
            "Check wiring / signal from controller to CO2 dosing unit",
        ],
        "mitigation_hints": (
            "CO2 injection system has failed. "
            "CO2 will gradually drop toward ambient level (~400 ppm). "
            "Reduce ventilation to slow CO2 loss. "
            "CO2 commands (uCO2) will have no effect — physical repair needed. "
            "Maintain temperature to partially compensate for reduced photosynthesis."
        ),
    },
    "ventilation_stuck_open": {
        "label": "Ventilation Stuck Open",
        "description": "Roof vents are stuck open and cannot be closed",
        "affected_systems": ["ventilation", "temperature", "humidity", "co2"],
        "repair_steps": [
            "Check ventilation drive motor / rack-and-pinion actuator",
            "Inspect for mechanical obstruction on roof vent rails",
            "Check motor controller is receiving close signal",
            "Attempt manual emergency close if override mechanism exists",
            "Call maintenance for motor or actuator replacement",
        ],
        "mitigation_hints": (
            "Ventilation is stuck open — cold outside air entering continuously. "
            "Increase boiler heating significantly (uBoil=1.0) to compensate heat loss. "
            "Increase CO2 injection (uCO2) — CO2 is continuously vented out. "
            "Ventilation close commands will have no effect until repaired. "
            "Focus on heating and CO2 compensation."
        ),
    },
    "ventilation_stuck_closed": {
        "label": "Ventilation Stuck Closed",
        "description": "Roof vents are stuck closed and cannot be opened",
        "affected_systems": ["ventilation", "humidity", "co2", "temperature"],
        "repair_steps": [
            "Check ventilation drive motor / rack-and-pinion actuator",
            "Inspect for debris or mechanical obstruction blocking vent opening",
            "Verify ventilation open signal is reaching motor controller",
            "Open vents manually via emergency override if available",
            "Call maintenance — monitor humidity closely in the meantime",
        ],
        "mitigation_hints": (
            "Ventilation stuck closed — cannot reduce humidity or excess temperature. "
            "Reduce boiler output to avoid overheating. "
            "Monitor humidity carefully — risk of Botrytis above 85 %. "
            "Ventilation open commands will have no effect until repaired."
        ),
    },
    "lamp_failure": {
        "label": "Lamp Failure",
        "description": "Supplemental lighting system failure — lamps produce no light or heat",
        "affected_systems": ["lighting", "temperature"],
        "repair_steps": [
            "Check lamp power supply and circuit breakers",
            "Inspect individual lamp units for burned-out HPS / LED elements",
            "Verify lamp controller is receiving on-signal",
            "Check wiring for short circuits or loose connections",
            "Replace failed lamp units or call electrician",
        ],
        "mitigation_hints": (
            "Lamps have failed — less light and supplemental heat available. "
            "Increase boiler output slightly to compensate for lost lamp heat (~1 °C contribution). "
            "Lamp commands (uLamp) will have no effect — repair needed."
        ),
    },
    "thermal_screen_broken": {
        "label": "Thermal Screen Broken",
        "description": "Thermal screen drive failed — screen cannot close for insulation",
        "affected_systems": ["thermal_screen", "temperature", "heating"],
        "repair_steps": [
            "Check thermal screen drive motor (usually above gutter level)",
            "Inspect screen fabric for tears or entanglement in the rail",
            "Verify motor control signal from controller cabinet",
            "Check tension cables and guide pulleys",
            "Call maintenance — manually secure screen fabric if possible",
        ],
        "mitigation_hints": (
            "Thermal screen cannot close — significantly higher heat loss during night. "
            "Increase boiler output to compensate (especially between 22:00–06:00). "
            "Screen close commands (uThScr) will have no effect until repaired."
        ),
    },
    "sensor_temp_stuck": {
        "label": "Temp Sensor Stuck",
        "description": "Indoor temperature sensor frozen — readings are static regardless of real t_in",
        "affected_systems": ["temperature_sensing"],
        "repair_steps": [
            "Check sensor wiring and connector at the sensor head",
            "Verify signal at controller input terminal",
            "Clean sensor — possible condensation on sensor element",
            "Replace temperature sensor element (Pt100 / thermocouple)",
            "Cross-validate with a portable thermometer at the same location",
        ],
        "mitigation_hints": (
            "Temperature sensor appears stuck — t_in readings are not changing. "
            "Use outdoor temperature (T_out) and solar radiation (rad) as rough proxies. "
            "Be conservative: maintain moderate heating to avoid crop damage. "
            "Alert maintenance for sensor inspection and replacement."
        ),
    },
    "sensor_co2_drift": {
        "label": "CO2 Sensor Drift",
        "description": "CO2 sensor drifting — readings increasingly offset from real value",
        "affected_systems": ["co2_sensing"],
        "repair_steps": [
            "Perform CO2 sensor zero / span calibration using certified gas",
            "Check sensor for contamination or moisture ingress",
            "Inspect sample tube for blockage (for aspirating sensors)",
            "Replace sensor if calibration drift exceeds specification",
            "Cross-validate with a portable NDIR CO2 analyser if available",
        ],
        "mitigation_hints": (
            "CO2 sensor readings are unreliable — drifting from actual value. "
            "Apply moderate CO2 injection as a precaution (risk of under-supplying crop). "
            "Alert maintenance for calibration or sensor replacement."
        ),
    },
    "sensor_rh_failure": {
        "label": "Humidity Sensor Failure",
        "description": "Humidity sensor producing random / erratic readings",
        "affected_systems": ["humidity_sensing"],
        "repair_steps": [
            "Check humidity sensor for condensation on capacitive element",
            "Replace sensor element (capacitive humidity sensors degrade in wet conditions)",
            "Verify wiring and signal conditioning module",
            "Use conservative ventilation strategy until sensor is repaired",
            "Cross-validate with a portable hygrometer if available",
        ],
        "mitigation_hints": (
            "Humidity sensor is producing erratic readings — cannot trust rh values. "
            "Use conservative ventilation to prevent potential humidity build-up. "
            "Alert maintenance for sensor replacement."
        ),
    },
    "power_surge": {
        "label": "Power Surge",
        "description": "Power surge — all actuators are momentarily unresponsive",
        "affected_systems": ["all_actuators", "control_system"],
        "repair_steps": [
            "Check main circuit breakers and reset any tripped breakers",
            "Inspect UPS / power conditioning system status",
            "Check for electrical damage to motor controllers",
            "Restart SCADA / control system if it did not auto-recover",
            "Call electrical maintenance if power quality issues persist",
        ],
        "mitigation_hints": (
            "Power surge — all actuators are temporarily offline. "
            "System should recover automatically when surge ends. "
            "After surge: verify all actuators respond and check setpoints. "
            "Monitor for sustained electrical anomalies."
        ),
    },
    "high_humidity_event": {
        "label": "High Humidity Event",
        "description": "Unexpected humidity spike — condensation, irrigation fault, or fogging system",
        "affected_systems": ["humidity", "ventilation", "crop_disease_risk"],
        "repair_steps": [
            "Check irrigation system for leaks or unintended activation",
            "Inspect fogging / misting system for malfunctions",
            "Increase ventilation immediately to dehumidify",
            "Check drainage in growing trays and floor channels",
            "Inspect for cold spots causing condensation",
        ],
        "mitigation_hints": (
            "Humidity is spiking due to an external event (irrigation/condensation). "
            "Increase ventilation (uVent) to dehumidify — open to 0.4–0.8. "
            "Compensate heat loss from ventilation with increased boiler (uBoil). "
            "Physical inspection needed to identify and stop humidity source."
        ),
    },
}


# ---------------------------------------------------------------------------
# Physical effect definitions per incident type (parametrised by severity)
# ---------------------------------------------------------------------------

def _actuator_constraints(incident_type: str, severity: float) -> list[tuple[str, str, float]]:
    """
    Return a list of (actuator, mode, value) constraints for the given incident type.

    Modes:
      "dead"     — actuator output forced to 0 regardless of command
      "fixed"    — actuator output fixed to value regardless of command
      "min"      — actuator cannot go below value  (max(cmd, value))
      "max"      — actuator cannot go above value  (min(cmd, value))
    """
    s = max(0.0, min(1.0, severity))
    if incident_type == "door_open":
        # Door forces some ventilation; blocks thermal screen from closing
        return [
            ("uVent",  "min",  0.15 + s * 0.40),   # vent can't close below 0.15–0.55
            ("uThScr", "max",  max(0.0, 0.3 - s * 0.3)),  # screen can't close fully
        ]
    if incident_type == "heater_failure":
        return [("uBoil", "dead", 0.0)]
    if incident_type == "co2_supply_failure":
        return [("uCO2", "dead", 0.0)]
    if incident_type == "ventilation_stuck_open":
        forced = 0.4 + s * 0.5          # stuck between 40% and 90% open
        return [("uVent", "fixed", forced)]
    if incident_type == "ventilation_stuck_closed":
        return [("uVent", "dead", 0.0)]
    if incident_type == "lamp_failure":
        return [("uLamp", "dead", 0.0)]
    if incident_type == "thermal_screen_broken":
        return [("uThScr", "dead", 0.0)]
    if incident_type == "power_surge":
        # All actuators offline
        return [(a, "dead", 0.0) for a in _ACTUATOR_ORDER]
    # No actuator constraints for sensor faults or humidity event
    return []


def _physics_disturbances(
    incident_type: str,
    severity: float,
) -> list[tuple[str, str, float]]:
    """
    Return a list of (field, mode, param) physics disturbance specs.

    Modes:
      "drift_to_T_out"  — field drifts toward T_out:  field += param * (T_out - field) per step
      "drift_to_co2_out"— field drifts toward co2_out: field += param * (co2_out - field) per step
      "add"             — field += param  (constant delta per step)
      "random"          — field = random(field - param, field + param)
      "stuck"           — field is frozen at its value when incident started
      "growing_offset"  — field += cumulative param per step (sensor drift)
    """
    s = max(0.0, min(1.0, severity))
    if incident_type == "door_open":
        return [
            ("t_in",  "drift_to_T_out",   0.02 + s * 0.04),  # faster equalization at high severity
            ("co2",   "drift_to_co2_out", 0.02 + s * 0.03),
            ("rh",    "add",              -0.5 + s * 2.0),    # rh changes with outside air
        ]
    if incident_type == "high_humidity_event":
        return [("rh", "add", 0.8 + s * 2.5)]                 # 0.8–3.3 % rh increase per step
    if incident_type == "sensor_temp_stuck":
        return [("t_in", "stuck", 0.0)]
    if incident_type == "sensor_co2_drift":
        return [("co2", "growing_offset", 2.0 * s)]            # +2–50 ppm per step cumulative drift
    if incident_type == "sensor_rh_failure":
        return [("rh", "random", 40.0 * s)]                    # ±40% random noise at full severity
    return []


# ---------------------------------------------------------------------------
# IncidentManager
# ---------------------------------------------------------------------------

class IncidentManager:
    """
    Thread-safe manager for greenhouse incidents.

    The simulation runner holds one instance.  It is called from the simulation
    background thread, but incident add/remove are called from the FastAPI thread,
    so all mutation is protected by a lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # incident_id → (IncidentSpec, added_step)
        self._incidents: dict[str, tuple["IncidentSpec", int]] = {}
        # Sticky sensor values for "stuck" sensors: incident_id → frozen value
        self._stuck_values: dict[str, float] = {}
        # Cumulative drift per-incident for "growing_offset": incident_id → accumulated offset
        self._drift_accum: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def add(self, spec: "IncidentSpec", current_step: int) -> None:
        with self._lock:
            self._incidents[spec.incident_id] = (spec, current_step)
            logger.info(
                "IncidentManager: added %s id=%s severity=%.2f start_step=%d duration=%s",
                spec.incident_type, spec.incident_id,
                spec.severity, spec.start_step,
                str(spec.duration_steps),
            )

    def remove(self, incident_id: str) -> bool:
        with self._lock:
            if incident_id in self._incidents:
                del self._incidents[incident_id]
                self._stuck_values.pop(incident_id, None)
                self._drift_accum.pop(incident_id, None)
                logger.info("IncidentManager: removed incident id=%s", incident_id)
                return True
            return False

    def reset(self) -> None:
        """Clear all incidents on episode reset."""
        with self._lock:
            self._incidents.clear()
            self._stuck_values.clear()
            self._drift_accum.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_active(self, step: int) -> list["IncidentSpec"]:
        """Return incidents that are currently active at the given step."""
        with self._lock:
            return [
                spec
                for spec, _added in self._incidents.values()
                if step >= spec.start_step
                and (spec.duration_steps is None or step < spec.start_step + spec.duration_steps)
            ]

    def expire_check(self, step: int) -> list["IncidentAlert"]:
        """
        Remove incidents that have exceeded their duration.
        Returns a list of IncidentAlert for each expired incident.
        """
        from greenhouse_mvp.orchestration.schemas import IncidentAlert

        expired: list["IncidentAlert"] = []
        with self._lock:
            to_remove = []
            for iid, (spec, _added) in self._incidents.items():
                if (
                    spec.duration_steps is not None
                    and step >= spec.start_step + spec.duration_steps
                ):
                    to_remove.append(iid)
                    expired.append(IncidentAlert(
                        incident_id=spec.incident_id,
                        incident_type=spec.incident_type,
                        action="expired",
                        step=step,
                        severity=spec.severity,
                        description=spec.description or INCIDENT_CATALOG.get(
                            spec.incident_type, {}
                        ).get("description", ""),
                    ))
            for iid in to_remove:
                del self._incidents[iid]
                self._stuck_values.pop(iid, None)
                self._drift_accum.pop(iid, None)
                logger.info("IncidentManager: expired incident id=%s at step=%d", iid, step)
        return expired

    def summary(self) -> list[dict]:
        with self._lock:
            return [spec.model_dump() for spec, _ in self._incidents.values()]

    # ------------------------------------------------------------------
    # Effect application
    # ------------------------------------------------------------------

    def apply_to_telemetry(
        self, telemetry: "TelemetryPayload", step: int
    ) -> "TelemetryPayload":
        """Apply physics disturbances to the telemetry before the controller sees it."""
        active = self.get_active(step)
        if not active:
            return telemetry

        data = telemetry.model_dump()
        for spec in active:
            disturbances = _physics_disturbances(spec.incident_type, spec.severity)
            for field, mode, param in disturbances:
                if field not in data:
                    continue
                original = float(data[field])
                if mode == "drift_to_T_out":
                    t_out = float(data.get("T_out", original))
                    data[field] = original + param * (t_out - original)
                elif mode == "drift_to_co2_out":
                    co2_out = float(data.get("co2_out", original))
                    data[field] = original + param * (co2_out - original)
                elif mode == "add":
                    data[field] = max(0.0, original + param)
                    if field == "rh":
                        data[field] = min(100.0, data[field])
                elif mode == "random":
                    import random as _random
                    noise = _random.uniform(-param, param)
                    data[field] = original + noise
                    if field == "rh":
                        data[field] = max(0.0, min(100.0, data[field]))
                    if field == "t_in":
                        data[field] = max(-10.0, min(60.0, data[field]))
                elif mode == "stuck":
                    key = f"{spec.incident_id}_{field}"
                    if key not in self._stuck_values:
                        self._stuck_values[key] = original
                    data[field] = self._stuck_values[key]
                elif mode == "growing_offset":
                    key = f"{spec.incident_id}_{field}"
                    self._drift_accum[key] = self._drift_accum.get(key, 0.0) + param
                    data[field] = original + self._drift_accum[key]

                logger.debug(
                    "IncidentManager step=%d: %s disturbance %s.%s %s → %.2f (was %.2f)",
                    step, spec.incident_type, field, mode, param, data[field], original,
                )

        from greenhouse_mvp.orchestration.schemas import TelemetryPayload as _TP
        return _TP(**data)

    def apply_to_action(self, action_vec: np.ndarray, step: int) -> np.ndarray:
        """Apply actuator constraints after the controller decision, before gym.step()."""
        active = self.get_active(step)
        if not active:
            return action_vec

        vec = action_vec.copy()
        for spec in active:
            constraints = _actuator_constraints(spec.incident_type, spec.severity)
            for actuator, mode, value in constraints:
                if actuator not in _ACTUATOR_ORDER:
                    continue
                idx = _ACTUATOR_ORDER.index(actuator)
                original = float(vec[idx])
                if mode == "dead":
                    vec[idx] = 0.0
                elif mode == "fixed":
                    vec[idx] = float(np.clip(value, 0.0, 1.0))
                elif mode == "min":
                    vec[idx] = float(np.clip(max(original, value), 0.0, 1.0))
                elif mode == "max":
                    vec[idx] = float(np.clip(min(original, value), 0.0, 1.0))
                logger.debug(
                    "IncidentManager step=%d: %s actuator %s[%d] %s → %.2f (was %.2f)",
                    step, spec.incident_type, actuator, idx, mode, vec[idx], original,
                )

        return vec

    # ------------------------------------------------------------------
    # Context string for LLM prompts
    # ------------------------------------------------------------------

    def get_context_str(self, step: int) -> str:
        """Return a human-readable description of active incidents for LLM prompts."""
        active = self.get_active(step)
        if not active:
            return "No active incidents — system should be nominal."

        lines = ["=== ACTIVE INCIDENTS ==="]
        for spec in active:
            meta = INCIDENT_CATALOG.get(spec.incident_type, {})
            label = meta.get("label", spec.incident_type)
            desc = spec.description or meta.get("description", "")
            lines.append(
                f"  [{spec.incident_id}] {label} (severity={spec.severity:.2f}): {desc}"
            )
            hints = meta.get("mitigation_hints", "")
            if hints:
                lines.append(f"    Mitigation: {hints}")
        return "\n".join(lines)
