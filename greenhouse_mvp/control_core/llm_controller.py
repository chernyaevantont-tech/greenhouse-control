"""
llm_controller.py — Pure LLM-based greenhouse actuator controller.

Uses the raw openai SDK (not LangChain) to support extra_body parameters
needed to disable Qwen3 extended thinking mode in LM Studio.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Literal

import openai
from pydantic import BaseModel, Field

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    LLMActionPayload,
    TelemetryPayload,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class ActuatorOutput(BaseModel):
    """Structured output schema for LLM actuator decisions."""
    uBoil: float = Field(ge=0.0, le=1.0, description="Boiler heating fraction [0=off, 1=full]")
    uCO2: float = Field(ge=0.0, le=1.0, description="CO2 injection rate [0=off, 1=max]")
    uThScr: float = Field(ge=0.0, le=1.0, description="Thermal screen [0=open, 1=closed]")
    uVent: float = Field(ge=0.0, le=1.0, description="Roof ventilation [0=closed, 1=open]")
    uLamp: float = Field(ge=0.0, le=1.0, description="Supplemental lamps [0=off, 1=full]")
    uBlScr: float = Field(ge=0.0, le=1.0, description="Blackout screen [0=open, 1=closed]")
    reasoning: str = Field(description="One-sentence explanation of the control decision")


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an autonomous greenhouse climate controller.
Given current sensor readings, output ONLY a JSON object with the optimal actuator signals.

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

Respond ONLY with a JSON object with keys: uBoil, uCO2, uThScr, uVent, uLamp, uBlScr, reasoning."""

_USER_TEMPLATE = """\
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
    Pure LLM actuator controller using structured output for reliability.

    Parameters
    ----------
    backend : One of "openai", "ollama", "notebooklm"
    api_key : API key (ignored for Ollama)
    base_url : Chat/completions endpoint
    model : Model identifier
    timeout : HTTP request timeout in seconds (None = no timeout)
    call_interval : Steps between LLM calls (hold cached action between)
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
        self._last_action: ActionPayload | None = None
        self._last_reasoning: str = ""
        self._last_call_step: int = -999
        self._model = model

        self._client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key or "no-key",
            timeout=timeout,
            max_retries=0,
        )

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
            action, reasoning = self._call_llm(telemetry)
            self._last_action = action
            self._last_reasoning = reasoning
            self._last_call_step = current_step
            return action, reasoning
        except Exception as exc:
            logger.exception("LLMController: error at step %d: %s", current_step, exc)
            return self._fallback(current_step), f"Fallback: {exc}"

    def close(self) -> None:
        pass  # Nothing to close with HTTP-based clients

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _call_llm(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, str]:
        """Invoke the LLM via raw openai SDK and parse JSON from the response."""
        user_msg = _USER_TEMPLATE.format(
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

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                # Assistant prefill forces the model to complete the JSON directly,
                # bypassing Qwen3 extended-thinking mode (which burns all tokens on reasoning)
                {"role": "assistant", "content": "{"},
            ],
            temperature=0.2,
            max_tokens=512,
            extra_body={"enable_thinking": False},
        )

        usage = response.usage
        logger.info(
            "LLM usage: prompt=%s completion=%s reasoning=%s",
            usage.prompt_tokens if usage else "?",
            usage.completion_tokens if usage else "?",
            getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", "?") if usage else "?",
        )

        msg = response.choices[0].message
        content: str = msg.content or ""

        # Qwen3 extended thinking: final answer may be in reasoning_content
        if not content:
            content = getattr(msg, "reasoning_content", "") or ""
        if not content:
            raise ValueError(f"Empty response from LLM (reasoning_tokens may have consumed all budget)")

        # Strip <think>...</think> blocks
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # Restore the prefilled '{' that was stripped from the completion
        if content and not content.startswith("{"):
            content = "{" + content

        logger.debug("LLM raw content (first 400): %s", content[:400])

        # Extract JSON: prefer markdown code block, then find object with actuator keys
        # Search from the END — the model's final decision JSON is the last one
        data: dict | None = None
        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        candidates: list[str] = [md_match.group(1)] if md_match else []
        # All {...} blobs reversed (last first = most likely to be the final answer)
        all_blobs = re.findall(r"\{[^{}]+\}", content, re.DOTALL)
        candidates += list(reversed(all_blobs))

        for candidate in candidates:
            try:
                d = json.loads(candidate)
            except json.JSONDecodeError:
                try:
                    d = ast.literal_eval(candidate)
                except Exception:
                    continue
            if "uBoil" in d:
                data = d
                break

        if data is None:
            raise ValueError(f"No valid actuator JSON in LLM response: {content[:300]}")

        result = ActuatorOutput(**data)
        action = ActionPayload(
            step=telemetry.step,
            approved=False,
            uBoil=max(0.0, min(1.0, result.uBoil)),
            uCO2=max(0.0, min(1.0, result.uCO2)),
            uThScr=max(0.0, min(1.0, result.uThScr)),
            uVent=max(0.0, min(1.0, result.uVent)),
            uLamp=max(0.0, min(1.0, result.uLamp)),
            uBlScr=max(0.0, min(1.0, result.uBlScr)),
        )
        logger.info(
            "LLMController step=%d reasoning=%s", telemetry.step, result.reasoning[:80]
        )
        return action, result.reasoning

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
