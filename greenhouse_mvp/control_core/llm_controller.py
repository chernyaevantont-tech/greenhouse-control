"""
llm_controller.py — Pure LLM-based greenhouse actuator controller.

The LLM receives full telemetry and autonomously decides all six actuator
signals without any MPC or physics model.  Uses LangChain's @tool decorator
and bind_tools so the model emits a structured tool-call instead of free text.

MQTT outputs
------------
greenhouse/llm/action  QoS 0  LLMActionPayload  (step + reasoning + actuator values)
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    LLMActionPayload,
    TelemetryPayload,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

@tool
def set_greenhouse_actuators(
    uBoil: Annotated[float, "Boiler heating fraction [0=off, 1=full heat]"],
    uCO2: Annotated[float, "CO2 injection rate [0=off, 1=maximum]"],
    uThScr: Annotated[float, "Thermal screen [0=fully open, 1=fully closed]"],
    uVent: Annotated[float, "Roof ventilation opening [0=closed, 1=fully open]"],
    uLamp: Annotated[float, "Supplemental lamp intensity [0=off, 1=full]"],
    uBlScr: Annotated[float, "Blackout screen [0=open, 1=closed]"],
    reasoning: Annotated[str, "One-sentence explanation of the control decision"],
) -> str:
    """
    Set all six greenhouse actuator signals to maintain optimal indoor climate.

    Target ranges:
      Indoor temperature : 18-22 C  (setpoint 20 C)
      CO2 concentration  : 600-1000 ppm (setpoint 800 ppm)
      Relative humidity  : 40-85 %  (max 85 %)
    """
    # This function is only used as a schema carrier — the controller reads
    # the tool-call arguments from the LLM response without executing it.
    return "ok"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an autonomous greenhouse climate controller.
Given current sensor readings, compute optimal actuator signals to maintain:

  Indoor temperature : 18-22 C    (setpoint 20 C)
  CO2 concentration  : 600-1000 ppm (setpoint 800 ppm)
  Relative humidity  : 40-85 %    (max 85 %)

Actuator guide (all values in range [0.0, 1.0]):
  uBoil  - boiler heating     (0=off, 1=full heat; use to raise temperature)
  uCO2   - CO2 injection      (0=off, 1=full; use to raise CO2)
  uThScr - thermal screen     (0=open, 1=closed; reduces heat loss - useful at night/cold)
  uVent  - roof ventilation   (0=closed, 1=fully open; removes excess heat & humidity)
  uLamp  - supplemental lamps (0=off, 1=full; adds heat and DLI in dark periods)
  uBlScr - blackout screen    (0=open, 1=closed; blocks natural light - use at night)

Time hint: sin_h > 0 means daytime; sin_h < 0 means nighttime.

Call set_greenhouse_actuators with all six actuator values and a one-sentence reasoning."""

_USER_TEMPLATE = """\
/nothink
=== Sensor Readings (Step {step}) ===
  Indoor Temperature : {t_in:.2f} C      (target 18-22, setpoint 20)
  CO2 Concentration  : {co2:.1f} ppm    (target 600-1000, setpoint 800)
  Relative Humidity  : {rh:.1f} %       (target 40-85, max 85)
  Outdoor Temperature: {T_out:.2f} C
  Solar Radiation    : {rad:.1f} W/m2
  Outdoor CO2        : {co2_out:.1f} ppm
  Time encoding      : sin(h)={sin_h:.3f}  cos(h)={cos_h:.3f}  (sin>0 ~ daytime)"""


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class LLMController:
    """
    Pure LLM actuator controller - no MPC, no physics model.

    Parameters
    ----------
    backend:
        One of "openai", "ollama", or "notebooklm".
    api_key:
        API key for OpenAI / NotebookLM backends. Ignored for Ollama.
    base_url:
        Base URL of the chat/completions endpoint.
    model:
        Model identifier forwarded to the backend.
    timeout:
        HTTP request timeout in seconds, or None for no timeout.
    call_interval:
        How many simulation steps to hold the same action before querying
        the LLM again.  1 means call every step (default).  4 means
        the LLM is queried once every 4 steps (~1 hour at 15-min timesteps).
    """

    def __init__(
        self,
        backend: Literal["openai", "ollama", "notebooklm"] = "openai",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float | None = None,
        call_interval: int = 1,
    ) -> None:
        self._call_interval: int = max(1, call_interval)

        # Cache: reused between LLM calls when call_interval > 1
        self._last_action: ActionPayload | None = None
        self._last_reasoning: str = ""
        self._last_call_step: int = -999

        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key or "no-key",
            openai_api_base=base_url,
            temperature=0.2,
            max_tokens=2048,
            timeout=timeout,
            max_retries=0,
        )
        # Bind the tool schema so the model knows the expected call signature.
        # Do NOT pass tool_choice="required" — LM Studio Qwen3 aborts immediately
        # when tool_choice is forced, producing near-empty reasoning_content.
        self._llm = llm.bind_tools([set_greenhouse_actuators])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, str]:
        """
        Return actuator values for the current telemetry step.

        The LLM is called only once every call_interval steps; between
        calls the previous action is returned unchanged (with the step number
        updated) so the simulation is never stalled.

        Returns
        -------
        (ActionPayload, reasoning_str)
            ActionPayload.approved is False; the graph sets it to True.
            On any LLM failure a safe fallback action is returned.
        """
        current_step = telemetry.step

        # Return cached action if within the hold window.
        if (
            self._last_action is not None
            and (current_step - self._last_call_step) < self._call_interval
        ):
            cached = self._last_action.model_copy(update={"step": current_step})
            logger.debug(
                "LLMController: holding cached action "
                "(step %d, last LLM call step %d, interval %d)",
                current_step, self._last_call_step, self._call_interval,
            )
            return cached, f"[cached from step {self._last_call_step}] {self._last_reasoning}"

        # Time to query the LLM.
        _success = False
        try:
            action, reasoning = self._call_llm(telemetry)
            _success = True
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "LLMController: unexpected error at step %d: %s", current_step, exc
            )
            action, reasoning = self._fallback(current_step), f"Fallback: {exc}"

        # Only advance the call window on a successful LLM response.
        if _success:
            self._last_action = action
            self._last_reasoning = reasoning
            self._last_call_step = current_step
        return action, reasoning

    def close(self) -> None:
        """No-op - LangChain client has no persistent connection to close."""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_llm(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, str]:
        """Invoke the LLM and extract actuator values from the tool call."""
        user_text = _USER_TEMPLATE.format(
            step=telemetry.step,
            t_in=telemetry.t_in,
            co2=telemetry.co2,
            rh=telemetry.rh,
            T_out=telemetry.T_out,
            rad=telemetry.rad,
            co2_out=telemetry.co2_out,
            sin_h=telemetry.sin_h,
            cos_h=telemetry.cos_h,
        )
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ]
        response = self._llm.invoke(messages)

        # --- Standard tool_calls path ---
        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            args: dict = tool_calls[0]["args"]
            logger.debug("LLMController: tool_calls at step %d: %s", telemetry.step, args)
            return self._args_to_action(args, telemetry.step)

        logger.error(
            "LLMController: no tool call at step %d | response=%r",
            telemetry.step, response,
        )
        raise ValueError("LLM returned no tool call")

    @staticmethod
    def _args_to_action(
        args: dict, step: int
    ) -> tuple[ActionPayload, str]:
        """Convert tool-call args dict to (ActionPayload, reasoning) tuple."""
        reasoning = str(args.get("reasoning", ""))
        action = ActionPayload(
            step=step,
            approved=False,
            uBoil=float(args.get("uBoil", 0.5)),
            uCO2=float(args.get("uCO2", 0.0)),
            uThScr=float(args.get("uThScr", 0.5)),
            uVent=float(args.get("uVent", 0.1)),
            uLamp=float(args.get("uLamp", 0.0)),
            uBlScr=float(args.get("uBlScr", 0.0)),
        )
        return action, reasoning

    @staticmethod
    def _fallback(step: int) -> ActionPayload:
        """Safe fallback when LLM is unavailable or returns invalid output."""
        return ActionPayload(
            step=step,
            approved=False,
            uBoil=0.3,
            uCO2=0.0,
            uThScr=0.5,
            uVent=0.1,
            uLamp=0.0,
            uBlScr=0.0,
        )


def build_llm_action_payload(action: ActionPayload, reasoning: str) -> LLMActionPayload:
    """Convenience builder - combines an ActionPayload with LLM reasoning text."""
    return LLMActionPayload(
        step=action.step,
        reasoning=reasoning,
        uBoil=action.uBoil,
        uCO2=action.uCO2,
        uThScr=action.uThScr,
        uVent=action.uVent,
        uLamp=action.uLamp,
        uBlScr=action.uBlScr,
    )
