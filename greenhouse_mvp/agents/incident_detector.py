"""
incident_detector.py — LLM-based incident detection and repair recommendation agent.

Uses LangGraph create_react_agent with a submit_incident_report tool.
The agent analyses recent telemetry history, action history, and OOD metrics to:
  1. Identify the type of incident / anomaly (or declare "nominal").
  2. List affected systems.
  3. Provide ordered repair steps for the operator.
  4. Suggest immediate mitigation actuator values for the controller.
  5. Assign an urgency level.

The detector is triggered by heuristic rules (cheap Python checks) and then calls
the LLM only when a cooldown period has elapsed.  This prevents excessive LLM calls.

Heuristic triggers (any one is sufficient):
  - OOD Mahalanobis distance >= threshold (ood_detected)
  - uBoil > 0.5 for HEURISTIC_WINDOW steps but t_in not rising (Δ < 0.05 °C/step)
  - uCO2  > 0.3 for HEURISTIC_WINDOW steps but co2  not rising (Δ < 5 ppm/step)
  - co2 < 300 ppm  or  co2 > 3000 ppm
  - rh  < 5 %      or  rh  > 97 %
  - t_in reading constant for HEURISTIC_WINDOW steps (sensor stuck)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    IncidentReport,
    OODMetrics,
    TelemetryPayload,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

HEURISTIC_WINDOW = 5          # steps needed to confirm a heuristic trigger
DETECTOR_COOLDOWN = 30        # min steps between LLM calls
DETECTOR_WARMUP   = 20        # steps before first detector activation


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

@tool
def submit_incident_report(
    detected_type: Annotated[
        str,
        (
            "Incident type key, OR 'nominal' if no anomaly, OR 'unknown_anomaly' if something "
            "is wrong but type unclear. Valid keys: door_open, heater_failure, co2_supply_failure, "
            "ventilation_stuck_open, ventilation_stuck_closed, lamp_failure, "
            "thermal_screen_broken, sensor_temp_stuck, sensor_co2_drift, sensor_rh_failure, "
            "power_surge, high_humidity_event."
        ),
    ],
    confidence: Annotated[float, "Confidence in the detection [0.0=unsure, 1.0=certain]"],
    affected_systems: Annotated[
        list[str],
        "List of affected subsystems, e.g. ['heating', 'temperature', 'boiler']",
    ],
    urgency: Annotated[
        Literal["low", "medium", "high", "critical"],
        "low=monitor, medium=schedule repair, high=repair soon, critical=immediate action",
    ],
    repair_steps: Annotated[
        list[str],
        "Ordered list of repair/diagnostic steps for the operator (3–6 steps)",
    ],
    reasoning: Annotated[str, "Brief reasoning (2–4 sentences) explaining the diagnosis"],
    uBoil: Annotated[float, "Suggested boiler [0-1]. Use -1 if no change recommended."] = -1.0,
    uCO2: Annotated[float, "Suggested CO2 injection [0-1]. Use -1 if no change."] = -1.0,
    uThScr: Annotated[float, "Suggested thermal screen [0-1]. Use -1 if no change."] = -1.0,
    uVent: Annotated[float, "Suggested ventilation [0-1]. Use -1 if no change."] = -1.0,
    uLamp: Annotated[float, "Suggested lamps [0-1]. Use -1 if no change."] = -1.0,
    uBlScr: Annotated[float, "Suggested blackout screen [0-1]. Use -1 if no change."] = -1.0,
) -> str:
    """
    Submit your incident detection report.
    Call this exactly once after reasoning about the telemetry and action history.
    """
    return "Incident report submitted."


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a greenhouse anomaly detection specialist.
Your task: analyse recent sensor readings and actuator responses to identify
equipment failures, environmental incidents, or sensor faults.

=== POSSIBLE INCIDENT TYPES ===
  door_open              — Uncontrolled air exchange (t_in drifting toward T_out, CO2 dropping)
  heater_failure         — uBoil commanded high but t_in still falling
  co2_supply_failure     — uCO2 commanded but CO2 not rising / falling toward ~400 ppm
  ventilation_stuck_open — uVent commanded close but climate continues as if vents open
  ventilation_stuck_closed — uVent commanded open but humidity/temp not responding
  lamp_failure           — uLamp commanded but no expected temp contribution
  thermal_screen_broken  — uThScr commanded close but heat loss pattern unchanged
  sensor_temp_stuck      — t_in reads the same value for multiple consecutive steps
  sensor_co2_drift       — CO2 readings moving steadily in one direction without cause
  sensor_rh_failure      — rh readings are erratic / physically impossible
  power_surge            — All actuators briefly unresponsive / system-wide anomaly
  high_humidity_event    — rh rising rapidly with no actuator explanation
  nominal                — No anomaly detected; system behaving within expectations
  unknown_anomaly        — Something is wrong but does not fit known incident types

=== NORMAL SETPOINTS ===
  t_in  : 18–22 °C (setpoint 20 °C)
  co2   : 600–1000 ppm (setpoint 800 ppm)
  rh    : 40–85 %
  Expected rates: uBoil=1.0 raises t_in ~0.5–1.0 °C/step; uCO2=1.0 raises CO2 ~30–80 ppm/step

=== DIAGNOSIS APPROACH ===
  1. Check if sensor values are within physical limits.
  2. Compare actuator commands to observed sensor responses.
  3. If a commanded actuator has no measurable effect after 3+ steps → actuator failure.
  4. If a sensor value is static or physically impossible → sensor failure.
  5. If climate is changing in a direction inconsistent with actuators → physical event.

Call submit_incident_report exactly once after your analysis.
If everything is nominal, set detected_type='nominal' and confidence > 0.8."""

_STEP_TEMPLATE = (
    "  Step {step} | t_in={t_in:.1f}°C  co2={co2:.0f}ppm  rh={rh:.0f}%  "
    "T_out={T_out:.1f}°C  rad={rad:.0f}W/m²\n"
    "            | uBoil={uBoil:.2f}  uCO2={uCO2:.2f}  uThScr={uThScr:.2f}  "
    "uVent={uVent:.2f}  uLamp={uLamp:.2f}  uBlScr={uBlScr:.2f}"
)


def _fmt_step(tel: TelemetryPayload, action: ActionPayload | None) -> str:
    act = action or ActionPayload(
        step=tel.step, approved=False,
        uBoil=0.0, uCO2=0.0, uThScr=0.0, uVent=0.0, uLamp=0.0, uBlScr=0.0,
    )
    return _STEP_TEMPLATE.format(
        step=tel.step,
        t_in=tel.t_in, co2=tel.co2, rh=tel.rh,
        T_out=tel.T_out, rad=tel.rad,
        uBoil=act.uBoil, uCO2=act.uCO2, uThScr=act.uThScr,
        uVent=act.uVent, uLamp=act.uLamp, uBlScr=act.uBlScr,
    )


# ---------------------------------------------------------------------------
# Heuristic triggers (cheap — no LLM)
# ---------------------------------------------------------------------------

def should_trigger(
    episode_log: list[dict],
    ood_detected: bool,
    step: int,
    warmup: int = DETECTOR_WARMUP,
    window: int = HEURISTIC_WINDOW,
) -> tuple[bool, str]:
    """
    Check cheap heuristic conditions to decide whether to invoke the LLM detector.

    Returns (triggered: bool, reason: str).
    """
    if step < warmup:
        return False, "warmup"

    if ood_detected:
        return True, "OOD detected"

    # Need at least `window` recent entries to compute trends
    if len(episode_log) < window:
        return False, "insufficient history"

    recent = episode_log[-window:]

    # --- Sensor range checks (current step only) ---
    last = recent[-1]
    if last.get("co2", 800) < 300 or last.get("co2", 800) > 3000:
        return True, f"CO2 out of range: {last.get('co2'):.0f} ppm"
    if last.get("rh", 60) < 5 or last.get("rh", 60) > 97:
        return True, f"RH out of range: {last.get('rh'):.1f}%"
    if last.get("t_in", 20) < 3 or last.get("t_in", 20) > 40:
        return True, f"t_in out of range: {last.get('t_in'):.1f}°C"

    # --- Actuator response checks ---
    t_in_vals  = [e.get("t_in", 20)  for e in recent]
    co2_vals   = [e.get("co2", 800)  for e in recent]

    def _action_val(e: dict, key: str) -> float:
        a = e.get("action")
        if isinstance(a, dict):
            return float(a.get(key, 0))
        return 0.0

    boil_avg = sum(_action_val(e, "uBoil") for e in recent) / max(1, len(recent))
    co2_cmd_avg = sum(_action_val(e, "uCO2") for e in recent) / max(1, len(recent))

    # Boiler commanded high but t_in not rising
    if boil_avg > 0.5:
        dt_in = t_in_vals[-1] - t_in_vals[0]
        if dt_in < 0.05 * window:   # less than 0.05 °C/step increase
            return True, f"uBoil avg={boil_avg:.2f} but t_in Δ={dt_in:.2f}°C over {window} steps"

    # CO2 commanded but not rising
    if co2_cmd_avg > 0.3:
        dco2 = co2_vals[-1] - co2_vals[0]
        if dco2 < 5 * window:       # less than 5 ppm/step increase
            return True, f"uCO2 avg={co2_cmd_avg:.2f} but co2 Δ={dco2:.0f}ppm over {window} steps"

    # Temperature sensor stuck (all values within 0.1 °C)
    if max(t_in_vals) - min(t_in_vals) < 0.1:
        return True, f"t_in constant at {t_in_vals[-1]:.2f}°C for {window} steps"

    return False, "nominal"


# ---------------------------------------------------------------------------
# IncidentDetector agent
# ---------------------------------------------------------------------------

class IncidentDetector:
    """
    LLM-based incident detector.

    Triggered by heuristic rules; calls the LLM to classify the anomaly and
    generate repair recommendations.  On failure, returns a safe "nominal" report.
    """

    def __init__(
        self,
        backend: Literal["openai", "ollama", "notebooklm"] = "openai",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
    ) -> None:
        self._model_name = model
        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key or "no-key",
            openai_api_base=base_url,
            temperature=0.1,
            max_tokens=1500,
            timeout=timeout,
            max_retries=0,
        )
        self._agent = create_react_agent(llm, [submit_incident_report])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        current_telemetry: TelemetryPayload,
        episode_log: list[dict],
        ood_metrics: OODMetrics | None,
        active_incidents: list[dict],
        heuristic_reason: str = "",
    ) -> IncidentReport:
        """
        Run incident detection for the current step.

        Never raises — on any failure returns a safe "nominal" report.
        """
        step = current_telemetry.step
        try:
            prompt = self._build_prompt(
                current_telemetry, episode_log, ood_metrics, active_incidents, heuristic_reason
            )
            result = self._agent.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config={"recursion_limit": 10},
            )
            return self._extract_report(result["messages"], step, current_telemetry)
        except Exception as exc:
            logger.warning(
                "IncidentDetector: error at step %d: %s — returning nominal", step, exc
            )
            return IncidentReport(
                step=step,
                detected_type="nominal",
                confidence=0.0,
                affected_systems=[],
                repair_steps=[],
                reasoning=f"Detector error: {exc}",
                urgency="low",
            )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        tel: TelemetryPayload,
        episode_log: list[dict],
        ood: OODMetrics | None,
        active_incidents: list[dict],
        heuristic_reason: str,
    ) -> str:
        window = min(10, len(episode_log))
        recent_log = episode_log[-window:] if episode_log else []

        lines = [_SYSTEM_PROMPT, ""]

        # Active incidents context
        if active_incidents:
            lines.append("=== ALREADY KNOWN INCIDENTS (DO NOT re-report these) ===")
            for inc in active_incidents:
                lines.append(
                    f"  [{inc.get('incident_id')}] {inc.get('incident_type')} "
                    f"(severity={inc.get('severity', 1.0):.2f})"
                )
            lines.append("")

        # Recent history table
        lines.append(f"=== RECENT HISTORY — last {len(recent_log)} steps ===")

        # Reconstruct telemetry + action pairs from episode_log
        from greenhouse_mvp.orchestration.schemas import TelemetryPayload as _TP
        for entry in recent_log:
            try:
                t = _TP(
                    step=entry["step"],
                    timestamp_sim=float(entry["step"] * 900),
                    t_in=entry["t_in"], co2=entry["co2"], rh=entry["rh"],
                    T_out=entry["T_out"], rad=entry["rad"], co2_out=entry.get("co2_out", 400),
                    sin_h=entry.get("sin_h", 0.0), cos_h=entry.get("cos_h", 1.0),
                )
                a = None
                if entry.get("action"):
                    ad = entry["action"]
                    a = ActionPayload(
                        step=entry["step"], approved=True,
                        uBoil=ad.get("uBoil", 0), uCO2=ad.get("uCO2", 0),
                        uThScr=ad.get("uThScr", 0), uVent=ad.get("uVent", 0),
                        uLamp=ad.get("uLamp", 0), uBlScr=ad.get("uBlScr", 0),
                    )
                lines.append(_fmt_step(t, a))
            except Exception:
                pass

        lines.append("")

        # OOD info
        if ood:
            lines.append(
                f"=== OOD METRICS ===\n"
                f"  Mahalanobis distance: {ood.mahalanobis_distance:.3f} "
                f"(threshold: {ood.threshold_used:.1f})  "
                f"In-distribution: {ood.in_distribution}"
            )
        if heuristic_reason and heuristic_reason != "nominal":
            lines.append(f"\n  Heuristic trigger: {heuristic_reason}")

        lines.append("\nAnalyse the above and call submit_incident_report with your diagnosis.")
        return "\n".join(lines)

    def _extract_report(
        self,
        messages: list,
        step: int,
        tel: TelemetryPayload,
    ) -> IncidentReport:
        """Extract submit_incident_report tool call from agent messages."""
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "submit_incident_report":
                        args = tc["args"]

                        # Build optional mitigation action
                        mitigation = None
                        actuals = {
                            "uBoil": args.get("uBoil", -1.0),
                            "uCO2": args.get("uCO2", -1.0),
                            "uThScr": args.get("uThScr", -1.0),
                            "uVent": args.get("uVent", -1.0),
                            "uLamp": args.get("uLamp", -1.0),
                            "uBlScr": args.get("uBlScr", -1.0),
                        }
                        if any(v >= 0 for v in actuals.values()):
                            # Use 0.3 boiler as fallback for unspecified values
                            defaults = {"uBoil": 0.3, "uCO2": 0.0, "uThScr": 1.0,
                                        "uVent": 0.0, "uLamp": 0.0, "uBlScr": 0.0}
                            resolved = {
                                k: (float(v) if v >= 0 else defaults[k])
                                for k, v in actuals.items()
                            }
                            mitigation = ActionPayload(
                                step=step, approved=False, **resolved
                            )

                        report = IncidentReport(
                            step=step,
                            detected_type=args.get("detected_type", "unknown_anomaly"),
                            confidence=float(args.get("confidence", 0.5)),
                            affected_systems=list(args.get("affected_systems", [])),
                            repair_steps=list(args.get("repair_steps", [])),
                            mitigation_action=mitigation,
                            reasoning=args.get("reasoning", ""),
                            urgency=args.get("urgency", "medium"),
                        )
                        logger.info(
                            "IncidentDetector step=%d: %s (confidence=%.2f urgency=%s)",
                            step, report.detected_type, report.confidence, report.urgency,
                        )
                        return report

        # No tool call — return nominal
        logger.warning("IncidentDetector step=%d: no tool call in response — returning nominal", step)
        return IncidentReport(
            step=step,
            detected_type="nominal",
            confidence=0.0,
            affected_systems=[],
            repair_steps=[],
            reasoning="No tool call returned by LLM.",
            urgency="low",
        )
