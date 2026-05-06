"""
notebooklm_agent.py — LangGraph-based LLM supervisor for greenhouse control.

Uses LangChain create_react_agent with a submit_verdict tool.
This is the native LangGraph tool calling mechanism — the LLM autonomously
reasons about the telemetry and MPC proposal, then calls submit_verdict.

Supports: openai, ollama, notebooklm backends.
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
    GraphState,
    OODMetrics,
    SupervisorVerdict,
    TelemetryPayload,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool definition — the agent calls this to submit its verdict
# ---------------------------------------------------------------------------

@tool
def submit_verdict(
    decision: Annotated[Literal["APPROVE", "REJECT", "OVERRIDE"], "Control decision"],
    reason: Annotated[str, "Brief explanation of the decision (1-2 sentences)"],
    confidence: Annotated[float, "Confidence level in this decision [0.0 = unsure, 1.0 = certain]"],
    uBoil: Annotated[float, "Override boiler heating [0-1]. Used only when decision=OVERRIDE."] = -1.0,
    uCO2: Annotated[float, "Override CO2 injection [0-1]. Used only when decision=OVERRIDE."] = -1.0,
    uThScr: Annotated[float, "Override thermal screen [0-1]. Used only when decision=OVERRIDE."] = -1.0,
    uVent: Annotated[float, "Override ventilation [0-1]. Used only when decision=OVERRIDE."] = -1.0,
    uLamp: Annotated[float, "Override lamps [0-1]. Used only when decision=OVERRIDE."] = -1.0,
    uBlScr: Annotated[float, "Override blackout screen [0-1]. Used only when decision=OVERRIDE."] = -1.0,
) -> str:
    """
    Submit your supervision verdict for the current MPC-proposed greenhouse action.
    Call this exactly once after reasoning about the telemetry and proposed action.
    """
    return "Verdict submitted successfully."


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a greenhouse climate control supervisor.
You receive sensor telemetry, an MPC-proposed actuator action, and out-of-distribution (OOD) metrics.

Your task: evaluate the proposed action and call submit_verdict with one of:
  - APPROVE  : Accept the MPC action as-is
  - REJECT   : Reject it (triggers MPC replanning)
  - OVERRIDE : Replace it with your own values (provide all six actuator signals)

Key setpoints:
  Indoor temperature : 18-22 C (setpoint 20 C)
  CO2 concentration  : 600-1000 ppm (setpoint 800 ppm)
  Relative humidity  : 40-85 % (max 85 %)

Prefer APPROVE unless the action is clearly wrong or the system is OOD.
Always call submit_verdict — do not just respond with text."""

_USER_TEMPLATE = """\
=== Telemetry (Step {step}) ===
  Indoor Temperature : {t_in:.2f} C     (setpoint 20 C, range 18-22)
  CO2 Concentration  : {co2:.1f} ppm   (setpoint 800, range 600-1000)
  Relative Humidity  : {rh:.1f} %      (max 85%)
  Outdoor Temp       : {T_out:.2f} C
  Solar Radiation    : {rad:.1f} W/m2

=== MPC Proposed Action ===
  Boiler (uBoil)       : {uBoil:.3f}
  CO2 Injection (uCO2) : {uCO2:.3f}
  Thermal Screen       : {uThScr:.3f}
  Ventilation          : {uVent:.3f}
  Lamps                : {uLamp:.3f}
  Blackout Screen      : {uBlScr:.3f}

=== OOD Metrics ===
  Mahalanobis Distance : {mahalanobis:.3f}  (threshold: {threshold:.1f})
  In Distribution      : {in_distribution}
  Max SINDy Residual   : {max_residual:.4f}

Review the above and call submit_verdict with your decision."""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class NotebookLMAgent:
    """
    Supervisor agent using LangGraph create_react_agent with a verdict tool.

    Parameters
    ----------
    backend : "openai", "ollama", or "notebooklm"
    api_key : API key (ignored for Ollama)
    base_url : Chat/completions endpoint
    model : Model identifier
    timeout : HTTP request timeout in seconds
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
            max_tokens=1024,
            timeout=timeout,
            max_retries=0,
        )
        # create_react_agent: LLM reasons then calls submit_verdict
        self._agent = create_react_agent(llm, [submit_verdict])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(self, state: GraphState) -> SupervisorVerdict:
        """
        Run supervisor review for the current graph state.

        Never raises — on any failure defaults to APPROVE (fail-safe).
        """
        step = state["telemetry"].step if state.get("telemetry") else 0
        try:
            prompt = self._build_prompt(state)
            result = self._agent.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config={"recursion_limit": 10},
            )
            return self._extract_verdict(result["messages"], step, state)
        except Exception as exc:
            logger.warning("NotebookLMAgent: error at step %d: %s — defaulting APPROVE", step, exc)
            return self._safe_approve(step, f"Agent error: {exc}", confidence=0.0)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_prompt(self, state: GraphState) -> str:
        tel: TelemetryPayload = state["telemetry"]
        action: ActionPayload = state["proposed_action"]
        ood: OODMetrics | None = state.get("ood_metrics")

        return _SYSTEM_PROMPT + "\n\n" + _USER_TEMPLATE.format(
            step=tel.step,
            t_in=tel.t_in,
            co2=tel.co2,
            rh=tel.rh,
            T_out=tel.T_out,
            rad=tel.rad,
            uBoil=action.uBoil,
            uCO2=action.uCO2,
            uThScr=action.uThScr,
            uVent=action.uVent,
            uLamp=action.uLamp,
            uBlScr=action.uBlScr,
            mahalanobis=ood.mahalanobis_distance if ood else 0.0,
            threshold=ood.threshold_used if ood else 6.0,
            in_distribution=ood.in_distribution if ood else True,
            max_residual=ood.max_residual if ood else 0.0,
        )

    def _extract_verdict(self, messages, step: int, state: GraphState) -> SupervisorVerdict:
        """Extract submit_verdict tool call args from agent messages."""
        proposed: ActionPayload = state.get("proposed_action")

        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "submit_verdict":
                        args = tc["args"]
                        decision = args.get("decision", "APPROVE")
                        reason = args.get("reason", "")
                        confidence = float(args.get("confidence", 0.8))

                        override_action = None
                        if decision == "OVERRIDE" and proposed is not None:
                            def _safe(v, fallback):
                                return float(v) if isinstance(v, (int, float)) and v >= 0 else fallback
                            override_action = proposed.model_copy(update={
                                "approved": False,
                                "uBoil": _safe(args.get("uBoil"), proposed.uBoil),
                                "uCO2": _safe(args.get("uCO2"), proposed.uCO2),
                                "uThScr": _safe(args.get("uThScr"), proposed.uThScr),
                                "uVent": _safe(args.get("uVent"), proposed.uVent),
                                "uLamp": _safe(args.get("uLamp"), proposed.uLamp),
                                "uBlScr": _safe(args.get("uBlScr"), proposed.uBlScr),
                            })

                        logger.info(
                            "Supervisor step=%d decision=%s confidence=%.2f reason=%s",
                            step, decision, confidence, reason[:60],
                        )
                        return SupervisorVerdict(
                            step=step,
                            decision=decision,
                            override_action=override_action,
                            reason=reason,
                            confidence=confidence,
                        )

        # No tool call found — default to APPROVE
        logger.warning(
            "NotebookLMAgent: no tool call found in response at step %d — defaulting APPROVE", step
        )
        return self._safe_approve(step, "No tool call returned by LLM", confidence=0.0)

    def _safe_approve(self, step: int, reason: str, confidence: float = 1.0) -> SupervisorVerdict:
        return SupervisorVerdict(
            step=step,
            decision="APPROVE",
            override_action=None,
            reason=reason,
            confidence=confidence,
        )
