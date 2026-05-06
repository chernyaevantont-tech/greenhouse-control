"""
llm_controller.py — LLM-based greenhouse actuator controller.

Uses LangGraph create_react_agent with a set_actuators tool.
The LLM reasons about current telemetry and calls set_actuators exactly once,
mirroring the native tool-calling pattern used by NotebookLMAgent.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from greenhouse_mvp.orchestration.schemas import ActionPayload, TelemetryPayload

logger = logging.getLogger(__name__)

# Named tuple for history entries (state + action that was applied at that step)
from typing import NamedTuple


class _HistoryEntry(NamedTuple):
    telemetry: TelemetryPayload
    action: ActionPayload | None  # None for very first step before any action


# ---------------------------------------------------------------------------
# Tool definition — the agent calls this to emit actuator values
# ---------------------------------------------------------------------------

@tool
def set_actuators(
    uBoil: Annotated[float, "Boiler heating fraction [0=off, 1=full heat]"],
    uCO2: Annotated[float, "CO2 injection rate [0=off, 1=max]"],
    uThScr: Annotated[float, "Thermal screen [0=open, 1=closed]"],
    uVent: Annotated[float, "Roof ventilation [0=closed, 1=open]"],
    uLamp: Annotated[float, "Supplemental lamps [0=off, 1=full]"],
    uBlScr: Annotated[float, "Blackout screen [0=open, 1=closed]"],
    reasoning: Annotated[str, "One-sentence explanation of the control decision"],
    fault_report: Annotated[
        str,
        (
            "Anomaly/fault diagnosis. Write 'OK' if all sensors and actuators appear normal. "
            "Otherwise describe the suspected fault: which signal is anomalous, what pattern "
            "(stuck/random/no-effect), and your confidence. "
            "E.g. 'FAULT: t_in=41°C impossible at T_out=1°C — sensor likely stuck high (high confidence)'"
        ),
    ] = "OK",
) -> str:
    """
    Set greenhouse actuator signals for the current control step.
    Call this exactly once after reasoning about the sensor readings.
    All actuator values must be in range [0.0, 1.0].
    Always fill fault_report — 'OK' if nominal, otherwise describe the anomaly.
    """
    return "Actuators set successfully."


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an autonomous greenhouse climate controller.
Analyse the sensor history and call set_actuators with optimal values.

=== SETPOINTS & HARD LIMITS ===
  t_in  : target 18-22 C   (setpoint 20 C)   — NEVER let it fall below 15 C
  co2   : target 600-1000 ppm (setpoint 800)
  rh    : target 40-85 %   — NEVER exceed 87 %

=== ACTUATOR GUIDE (all values [0.0, 1.0]) ===
  uBoil  - boiler heating.     Raise t_in.   Scale with error: +1 C error → 0.2, +3 C → 0.6, +5 C → 1.0
  uCO2   - CO2 injection.      Raise co2.    Use 0.5-1.0 when co2 < 600 ppm; 0 when co2 > 900 ppm
  uThScr - thermal screen.     1=closed reduces heat loss. Always close at night or when T_out < 10 C.
  uVent  - roof ventilation.   Opens to reduce rh and heat. WARNING: also cools greenhouse by ~2 C per 0.3 open.
  uLamp  - supplemental lamps. Adds heat (+~1 C) and light. Use at night when t_in < 19 C.
  uBlScr - blackout screen.    1=closed. Close at night to block light pollution.

=== CONFLICT RESOLUTION ===
  High rh + Low t_in: open vents slightly (0.1-0.2) AND increase boiler — do NOT choose one over the other.
  Low t_in + Cold outside: increase uBoil AND close uThScr, avoid opening vents.
  CO2 too high: open vents briefly, it removes CO2 AND humidity AND cools — compensate with uBoil.

=== RESPONSE MAGNITUDE RULE ===
  Small error (within 1 unit of limit): gentle correction (0.1-0.3 change)
  Medium error (1-3 units past limit): moderate response (0.3-0.6)
  Large error (>3 units past limit): aggressive response (0.6-1.0)
  Trend matters: if a parameter is STILL moving in the wrong direction despite previous action, INCREASE intensity.

Time hint: sin_h > 0 means daytime; sin_h < 0 means nighttime.
Always call set_actuators — do not just respond with text.

=== FAULT DETECTION ===
  Cross-check sensor readings at every step for physical plausibility.

  Sensor fault indicators (write to fault_report if detected):
    - t_in > 38°C or t_in < 3°C while T_out is near-normal and rad=0  → likely stuck/random sensor
    - t_in reads the SAME value for 3+ consecutive steps despite uBoil changes → sensor stuck
    - co2 < 250 ppm or co2 > 2500 ppm                                 → likely sensor fault
    - rh > 100% or rh < 3%                                            → impossible, sensor fault
    - Any sensor jumps erratically ±50%+ between steps with no cause  → random noise fault

  Actuator fault indicators (write to fault_report if detected):
    - uBoil held at >0.5 for 5+ steps but t_in not rising (Δ < 0.1°C/step) → boiler actuator fault
    - uCO2 applied but co2 not rising after 3 steps                        → CO2 actuator fault
    - uVent opened but rh not dropping after 3 steps                       → vent actuator fault

  Control strategy under faults:
    - If a sensor is suspect, weight it less and infer from other sensors + physics.
      (E.g. if t_in seems stuck, use T_out + rad + recent trend to estimate real temperature)
    - If an actuator is dead, compensate with alternatives where possible.
      (E.g. if boiler dead, close uThScr=1 and reduce uVent to retain heat)
    - Always prioritise crop safety: keep t_in > 15°C even under degraded sensing.
    - Log your fault hypothesis in fault_report even if confidence is moderate."""

# Per-step block: state + the action that was applied at that step
_STEP_TEMPLATE = """\
  Step {step} [{tag}] | {time_str} | sin(h)={sin_h:.3f}
    STATE:  t_in={t_in:.2f}C {t_status}  co2={co2:.0f}ppm {c_status}  rh={rh:.1f}% {h_status}
    WEATHER: T_out={T_out:.1f}C  rad={rad:.0f}W/m2  co2_out={co2_out:.0f}ppm
    ACTION:  uBoil={uBoil}  uCO2={uCO2}  uThScr={uThScr}  uVent={uVent}  uLamp={uLamp}  uBlScr={uBlScr}"""


def _status(value: float, lo: float, hi: float, unit: str = "") -> str:
    """Return a short status tag: OK / WARN / CRIT with deviation."""
    if value < lo:
        diff = lo - value
        level = "CRIT" if diff > 3 else "WARN"
        return f"[{level} -{diff:.1f}{unit}]"
    if value > hi:
        diff = value - hi
        level = "CRIT" if diff > 3 else "WARN"
        return f"[{level} +{diff:.1f}{unit}]"
    return "[OK]"


def _fmt_action(a: ActionPayload | None) -> dict:
    if a is None:
        return {k: "?" for k in ("uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr")}
    return {
        "uBoil":  f"{a.uBoil:.2f}",
        "uCO2":   f"{a.uCO2:.2f}",
        "uThScr": f"{a.uThScr:.2f}",
        "uVent":  f"{a.uVent:.2f}",
        "uLamp":  f"{a.uLamp:.2f}",
        "uBlScr": f"{a.uBlScr:.2f}",
    }


def _time_str(sin_h: float, cos_h: float) -> str:
    """Convert sin/cos hour encoding back to approximate HH:MM."""
    import math
    hour = math.atan2(sin_h, cos_h) * 12.0 / math.pi
    if hour < 0:
        hour += 24.0
    h = int(hour)
    m = int((hour - h) * 60)
    return f"{h:02d}:{m:02d}"


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class LLMController:
    """
    LLM actuator controller using LangGraph create_react_agent with set_actuators tool.

    Parameters
    ----------
    backend : One of "openai", "ollama", "notebooklm"
    api_key : API key (ignored for Ollama)
    base_url : Chat/completions endpoint
    model : Model identifier
    timeout : HTTP request timeout in seconds (None = no timeout)
    call_interval : Steps between LLM calls (hold cached action between)
    history_window : How many past telemetry steps to include in the prompt
                     (1 = current step only; N = current + N-1 previous)
    """

    def __init__(
        self,
        backend: Literal["openai", "ollama", "notebooklm"] = "openai",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float | None = None,
        call_interval: int = 1,
        history_window: int = 1,
    ) -> None:
        self._call_interval: int = max(1, call_interval)
        self._history_window: int = max(1, history_window)
        self._history: deque[_HistoryEntry] = deque(maxlen=self._history_window)
        self._last_action: ActionPayload | None = None
        self._last_reasoning: str = ""
        self._last_fault_report: str = "OK"
        self._last_call_step: int = -999
        self._model = model

        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key or "no-key",
            openai_api_base=base_url,
            temperature=0.2,
            max_tokens=1024,
            timeout=timeout,
            max_retries=0,
            # Disable Qwen3 extended thinking — reasoning_tokens consume the entire
            # token budget before the model can emit a tool call (finish_reason=length).
            # extra_body is forwarded as-is by the openai SDK to the request body.
            model_kwargs={"extra_body": {"enable_thinking": False}},
        )
        self._agent = create_react_agent(llm, [set_actuators])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, str]:
        """
        Return actuator values for the current telemetry step.

        Caches the action for call_interval steps; on failure returns safe fallback.

        Returns (ActionPayload, reasoning_str)
        """
        current_step = telemetry.step

        # Return cached action within the hold window.
        if (
            self._last_action is not None
            and (current_step - self._last_call_step) < self._call_interval
        ):
            cached = self._last_action.model_copy(update={"step": current_step})
            logger.debug(
                "LLMController: holding cached action (step %d, last call %d, interval %d)",
                current_step, self._last_call_step, self._call_interval,
            )
            return cached, f"[cached from step {self._last_call_step}] {self._last_reasoning}"

        try:
            action, reasoning, fault_report = self._call_agent(telemetry)
            self._last_action = action
            self._last_reasoning = reasoning
            self._last_fault_report = fault_report
            self._last_call_step = current_step
            return action, reasoning
        except Exception as exc:
            logger.exception("LLMController: error at step %d: %s", current_step, exc)
            return self._fallback(current_step), f"Fallback: {exc}"

    @property
    def last_fault_report(self) -> str:
        return self._last_fault_report

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _call_agent(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, str, str]:
        """Invoke the LangGraph ReAct agent and extract the set_actuators tool call.

        If the model responds with text instead of a tool call, retries once with
        an explicit nudge message. If the second attempt also fails, raises.

        Returns (action, reasoning, fault_report).
        """
        # Append current reading with the action that was active before this step
        self._history.append(_HistoryEntry(telemetry=telemetry, action=self._last_action))

        prompt = _SYSTEM_PROMPT + "\n\n" + self._build_user_prompt()

        messages: list = [HumanMessage(content=prompt)]

        for attempt in range(2):
            result = self._agent.invoke(
                {"messages": messages},
                config={"recursion_limit": 10},
            )
            try:
                return self._extract_action(result["messages"], telemetry.step)
            except ValueError:
                if attempt == 0:
                    # Append agent reply + forceful nudge and retry once
                    messages = result["messages"] + [
                        HumanMessage(
                            content=(
                                "You have not called set_actuators yet. "
                                "You MUST call set_actuators now with all six actuator values. "
                                "Do not write text — invoke the tool immediately."
                            )
                        )
                    ]
                    logger.warning(
                        "LLMController step=%d: no tool call on attempt 1, retrying with nudge",
                        telemetry.step,
                    )
                else:
                    raise

    def _build_user_prompt(self) -> str:
        """Build user prompt with history, per-step actions, and trend summary."""
        history = list(self._history)  # oldest → newest
        n = len(history)
        cur = history[-1].telemetry

        # ---- Per-step history table ----
        lines: list[str] = []
        if n == 1:
            lines.append(f"=== Sensor Readings (Step {cur.step}) ===")
        else:
            lines.append(f"=== Sensor History — last {n} steps (oldest → newest) ===")

        for i, entry in enumerate(history):
            t = entry.telemetry
            tag = "NOW" if i == n - 1 else f"t-{n - 1 - i}"
            af = _fmt_action(entry.action)
            lines.append(_STEP_TEMPLATE.format(
                step=t.step, tag=tag,
                time_str=_time_str(t.sin_h, t.cos_h),
                sin_h=t.sin_h,
                t_in=t.t_in,  t_status=_status(t.t_in, 18, 22, "C"),
                co2=t.co2,    c_status=_status(t.co2, 600, 1000, "ppm"),
                rh=t.rh,      h_status=_status(t.rh, 40, 85, "%"),
                T_out=t.T_out, rad=t.rad, co2_out=t.co2_out,
                **af,
            ))

        # ---- Trend summary (only when we have >1 entry) ----
        if n > 1:
            old = history[0].telemetry
            dt_in  = cur.t_in  - old.t_in
            dco2   = cur.co2   - old.co2
            drh    = cur.rh    - old.rh
            steps  = n - 1

            def _trend(delta: float, unit: str) -> str:
                rate = delta / steps
                arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                return f"{arrow}{abs(delta):.1f}{unit} total ({rate:+.2f}{unit}/step)"

            lines.append("")
            lines.append("=== TRENDS (over last {} steps) ===".format(steps))
            lines.append(f"  t_in  : {_trend(dt_in, 'C')}   current error vs setpoint 20C: {cur.t_in - 20:+.1f}C")
            lines.append(f"  co2   : {_trend(dco2, 'ppm')} current error vs setpoint 800: {cur.co2 - 800:+.0f}ppm")
            lines.append(f"  rh    : {_trend(drh, '%')}  current vs limit 85%: {cur.rh - 85:+.1f}%")

            # Warn if previous actions had no effect
            last_a = history[-1].action
            if last_a is not None and dt_in < -0.5 and last_a.uBoil < 0.5:
                lines.append("  ⚠ t_in is falling despite heating — consider INCREASING uBoil significantly.")
            if last_a is not None and drh > 1.0 and last_a.uVent < 0.3:
                lines.append("  ⚠ rh is rising — consider INCREASING uVent (and compensate with uBoil).")

        lines.append("")
        lines.append("Review the above and call set_actuators for the NEXT step.")
        return "\n".join(lines)

    def _extract_action(self, messages, step: int) -> tuple[ActionPayload, str, str]:
        """Extract set_actuators tool call args from agent messages.

        Returns (action, reasoning, fault_report).
        """
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "set_actuators":
                        args = tc["args"]
                        reasoning = args.get("reasoning", "")
                        fault_report = args.get("fault_report", "OK")
                        action = ActionPayload(
                            step=step,
                            approved=False,
                            uBoil=float(max(0.0, min(1.0, args.get("uBoil", 0.3)))),
                            uCO2=float(max(0.0, min(1.0, args.get("uCO2", 0.0)))),
                            uThScr=float(max(0.0, min(1.0, args.get("uThScr", 1.0)))),
                            uVent=float(max(0.0, min(1.0, args.get("uVent", 0.0)))),
                            uLamp=float(max(0.0, min(1.0, args.get("uLamp", 0.0)))),
                            uBlScr=float(max(0.0, min(1.0, args.get("uBlScr", 0.0)))),
                        )
                        if fault_report and fault_report != "OK":
                            logger.warning(
                                "LLMController step=%d FAULT_REPORT: %s", step, fault_report
                            )
                        else:
                            logger.info(
                                "LLMController step=%d reasoning=%s", step, reasoning[:80]
                            )
                        return action, reasoning, fault_report
        raise ValueError("No set_actuators tool call found in agent response")

    def _fallback(self, step: int) -> ActionPayload:
        """Safe fallback action: minimal heating, screen closed."""
        return ActionPayload(
            step=step,
            approved=False,
            uBoil=0.3,
            uCO2=0.0,
            uThScr=1.0,
            uVent=0.0,
            uLamp=0.0,
            uBlScr=0.0,
        )
