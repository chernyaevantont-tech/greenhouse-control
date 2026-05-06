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
) -> str:
    """
    Set greenhouse actuator signals for the current control step.
    Call this exactly once after reasoning about the sensor readings.
    All actuator values must be in range [0.0, 1.0].
    """
    return "Actuators set successfully."


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an autonomous greenhouse climate controller.
Analyse the sensor readings and call set_actuators with optimal values.

Target ranges:
  Indoor temperature : 18-22 C    (setpoint 20 C)
  CO2 concentration  : 600-1000 ppm (setpoint 800 ppm)
  Relative humidity  : 40-85 %    (max 85 %)

Actuator guide (all values in range [0.0, 1.0]):
  uBoil  - boiler heating     (0=off, 1=full heat; use to raise temperature)
  uCO2   - CO2 injection      (0=off, 1=full; use to raise CO2)
  uThScr - thermal screen     (0=open, 1=closed; reduces heat loss at night/cold)
  uVent  - roof ventilation   (0=closed, 1=open; removes excess heat & humidity)
  uLamp  - supplemental lamps (0=off, 1=full; adds heat and light in dark periods)
  uBlScr - blackout screen    (0=open, 1=closed; blocks natural light at night)

Time hint: sin_h > 0 means daytime; sin_h < 0 means nighttime.
Always call set_actuators — do not just respond with text."""

# Single-step block used for each history entry and the current reading
_STEP_TEMPLATE = """\
  Step {step} | sin(h)={sin_h:.3f}  cos(h)={cos_h:.3f}
    t_in={t_in:.2f} C   co2={co2:.1f} ppm   rh={rh:.1f} %
    T_out={T_out:.2f} C   rad={rad:.1f} W/m2   co2_out={co2_out:.1f} ppm"""


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
        self._history: deque[TelemetryPayload] = deque(maxlen=self._history_window)
        self._last_action: ActionPayload | None = None
        self._last_reasoning: str = ""
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
            action, reasoning = self._call_agent(telemetry)
            self._last_action = action
            self._last_reasoning = reasoning
            self._last_call_step = current_step
            return action, reasoning
        except Exception as exc:
            logger.exception("LLMController: error at step %d: %s", current_step, exc)
            return self._fallback(current_step), f"Fallback: {exc}"

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _call_agent(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, str]:
        """Invoke the LangGraph ReAct agent and extract the set_actuators tool call."""
        # Append current reading to history before building the prompt
        self._history.append(telemetry)

        prompt = _SYSTEM_PROMPT + "\n\n" + self._build_user_prompt()

        result = self._agent.invoke(
            {"messages": [HumanMessage(content=prompt)]},
            config={"recursion_limit": 10},
        )
        return self._extract_action(result["messages"], telemetry.step)

    def _build_user_prompt(self) -> str:
        """Build the user-facing part of the prompt from the rolling history."""
        history = list(self._history)  # oldest first
        n = len(history)

        if n == 1:
            # Single step — concise single-block format
            t = history[0]
            lines = [
                f"=== Sensor Readings (Step {t.step}) ===",
                _STEP_TEMPLATE.format(
                    step=t.step, t_in=t.t_in, co2=t.co2, rh=t.rh,
                    T_out=t.T_out, rad=t.rad, co2_out=t.co2_out,
                    sin_h=t.sin_h, cos_h=t.cos_h,
                ),
                "",
                "  Targets: t_in 18-22 C (set 20) | co2 600-1000 ppm (set 800) | rh ≤ 85%",
            ]
        else:
            lines = [
                f"=== Sensor History (last {n} steps, newest last) ===",
                "  Targets: t_in 18-22 C (set 20) | co2 600-1000 ppm (set 800) | rh ≤ 85%",
                "",
            ]
            for i, t in enumerate(history):
                tag = "[CURRENT]" if i == n - 1 else f"[t-{n - 1 - i}]"
                lines.append(f"{tag}" + _STEP_TEMPLATE.format(
                    step=t.step, t_in=t.t_in, co2=t.co2, rh=t.rh,
                    T_out=t.T_out, rad=t.rad, co2_out=t.co2_out,
                    sin_h=t.sin_h, cos_h=t.cos_h,
                ))

        lines.append("")
        lines.append("Review the above and call set_actuators with your control decision.")
        return "\n".join(lines)

    def _extract_action(self, messages, step: int) -> tuple[ActionPayload, str]:
        """Extract set_actuators tool call args from agent messages."""
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "set_actuators":
                        args = tc["args"]
                        reasoning = args.get("reasoning", "")
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
                        logger.info(
                            "LLMController step=%d reasoning=%s", step, reasoning[:80]
                        )
                        return action, reasoning
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
