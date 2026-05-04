"""
notebooklm_agent.py — Backend-agnostic LLM supervisor for greenhouse control.

Supports:
  - "openai"    : OpenAI-compatible chat/completions (default: GPT-4o-mini)
  - "ollama"    : Local Ollama endpoint (OpenAI-compatible)
  - "notebooklm": Google NotebookLM HTTP endpoint (when available)

The rest of the LangGraph is completely decoupled from which backend is active.
See plan/04_langgraph_orchestration.md §5 for the full design spec.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Literal

import httpx
from pydantic import ValidationError

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    GraphState,
    OODMetrics,
    SupervisorVerdict,
    TelemetryPayload,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a greenhouse climate control supervisor.
You receive sensor telemetry, an MPC-proposed actuator action, \
and out-of-distribution (OOD) metrics.
Your task: decide whether to APPROVE, OVERRIDE, or REJECT the action.
Respond ONLY with a valid JSON object matching this schema:
{{
  "step": <int>,
  "decision": "APPROVE" | "REJECT" | "OVERRIDE",
  "override_action": <ActionPayload JSON or null>,
  "reason": "<brief explanation>",
  "confidence": <float 0-1>
}}"""

_USER_TEMPLATE = """\
=== Telemetry (Step {step}) ===
  Indoor Temperature : {t_in:.2f} °C   (setpoint: 20°C)
  CO2 Concentration  : {co2:.1f} ppm  (setpoint: 800 ppm)
  Relative Humidity  : {rh:.1f} %     (max: 85%)
  Outdoor Temp       : {T_out:.2f} °C
  Solar Radiation    : {rad:.1f} W/m²

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
  Max SINDy Residual   : {max_residual:.4f}"""

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class NotebookLMAgent:
    """
    Supervisor agent that wraps a configurable LLM backend.

    Parameters
    ----------
    backend:
        One of ``"openai"``, ``"ollama"``, or ``"notebooklm"``.
    api_key:
        API key for OpenAI / NotebookLM backends. Ignored for Ollama.
    base_url:
        Base URL of the chat/completions endpoint.
    model:
        Model identifier forwarded to the backend.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        backend: Literal["openai", "ollama", "notebooklm"] = "openai",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
    ) -> None:
        self._backend = backend
        self._model = model
        self._timeout = timeout

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self._http = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(self, state: GraphState) -> SupervisorVerdict:
        """
        Run the supervisor review for the current graph state.

        Never raises — on any failure the returned verdict defaults to APPROVE
        (fail-safe) so the simulation is never stalled.

        Parameters
        ----------
        state:
            The current LangGraph GraphState (telemetry + proposed_action + OOD).

        Returns
        -------
        SupervisorVerdict
        """
        step = state["telemetry"].step if state.get("telemetry") else 0
        try:
            system_prompt, user_prompt = self._build_prompt(state)
            raw = self._call_backend(system_prompt, user_prompt)
            return self._parse_verdict(raw, step)
        except httpx.TimeoutException:
            logger.warning("NotebookLMAgent: request timed out at step %d – defaulting APPROVE", step)
            return self._safe_approve(step, "Network timeout – defaulting to approve", confidence=0.0)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("NotebookLMAgent: rate-limited at step %d – defaulting APPROVE", step)
                return self._safe_approve(step, "Rate-limited – defaulting to approve", confidence=0.0)
            logger.error("NotebookLMAgent: HTTP %d at step %d", exc.response.status_code, step)
            return self._safe_approve(step, f"HTTP {exc.response.status_code} – defaulting to approve")
        except Exception as exc:  # noqa: BLE001
            logger.exception("NotebookLMAgent: unexpected error at step %d: %s", step, exc)
            return self._safe_approve(step, f"Unexpected error: {exc}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, state: GraphState) -> tuple[str, str]:
        """Format system and user prompts from the current state."""
        tel: TelemetryPayload = state["telemetry"]
        act: ActionPayload = state["proposed_action"]
        ood: OODMetrics = state["ood_metrics"]

        user_prompt = _USER_TEMPLATE.format(
            step=tel.step,
            t_in=tel.t_in,
            co2=tel.co2,
            rh=tel.rh,
            T_out=tel.T_out,
            rad=tel.rad,
            uBoil=act.uBoil,
            uCO2=act.uCO2,
            uThScr=act.uThScr,
            uVent=act.uVent,
            uLamp=act.uLamp,
            uBlScr=act.uBlScr,
            mahalanobis=ood.mahalanobis_distance,
            threshold=ood.threshold_used,
            in_distribution=ood.in_distribution,
            max_residual=ood.max_residual,
        )
        return _SYSTEM_PROMPT, user_prompt

    def _call_backend(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call the configured backend and return the raw text response.

        All three backends expose an OpenAI-compatible ``/chat/completions``
        endpoint so the same request body works for all of them.
        """
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
        }

        response = self._http.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_verdict(self, raw_json: str, step: int) -> SupervisorVerdict:
        """
        Parse the LLM text into a SupervisorVerdict.

        On any parse / validation failure, defaults to APPROVE (fail-safe).
        Never raises an exception.
        """
        try:
            # Some models wrap JSON in markdown code blocks or add extra text;
            # try to extract the first {...} block if direct parse fails.
            text = raw_json.strip()
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                import re as _re
                m = _re.search(r"\{.*\}", text, _re.DOTALL)
                if m:
                    obj = json.loads(m.group())
                else:
                    raise
            # Inject step if the LLM omitted it
            obj.setdefault("step", step)
            # Validate decision value
            if obj.get("decision") not in {"APPROVE", "REJECT", "OVERRIDE"}:
                raise ValueError(f"Unknown decision: {obj.get('decision')!r}")
            # If OVERRIDE, validate the nested action
            if obj.get("decision") == "OVERRIDE" and obj.get("override_action"):
                try:
                    obj["override_action"] = ActionPayload(**obj["override_action"])
                except (ValidationError, TypeError):
                    logger.warning(
                        "NotebookLMAgent: invalid override_action at step %d; falling back to APPROVE",
                        step,
                    )
                    obj["decision"] = "APPROVE"
                    obj["override_action"] = None
            return SupervisorVerdict(**obj)
        except (json.JSONDecodeError, ValidationError, ValueError, KeyError) as exc:
            logger.warning("NotebookLMAgent: parse error at step %d (%s); defaulting APPROVE", step, exc)
            logger.debug("Raw response was: %s", raw_json)
            return self._safe_approve(step, "Parse error – defaulting to approve")

    @staticmethod
    def _safe_approve(
        step: int,
        reason: str,
        confidence: float = 1.0,
    ) -> SupervisorVerdict:
        return SupervisorVerdict(
            step=step,
            decision="APPROVE",
            override_action=None,
            reason=reason,
            confidence=confidence,
        )

    def close(self) -> None:
        """Release the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> "NotebookLMAgent":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


if __name__ == "__main__":
    import json
    import os
    from http.server import BaseHTTPRequestHandler, HTTPServer

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from greenhouse_mvp.orchestration.schemas import (
        ActionPayload,
        GraphState,
        OODMetrics,
        TelemetryPayload,
    )

    _agent = NotebookLMAgent(
        backend=os.environ.get("LLM_BACKEND", "openai"),
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    )

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:  # noqa: D102
            logger.info(fmt, *args)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/review":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            state: GraphState = {
                "telemetry": TelemetryPayload(**body["telemetry"]),
                "proposed_action": ActionPayload(**body["proposed_action"]),
                "ood_metrics": OODMetrics(**body["ood_metrics"]),
                "supervisor_verdict": None,
                "final_action": None,
                "ood_detected": True,
                "retry_count": 0,
                "max_retries": 2,
                "episode_log": [],
            }
            verdict = _agent.review(state)
            payload = verdict.model_dump_json().encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    _http_port = int(os.environ.get("AGENT_PORT", "8081"))
    _server = HTTPServer(("0.0.0.0", _http_port), _Handler)
    logger.info("NotebookLMAgent HTTP server listening on :%d /review", _http_port)
    try:
        _server.serve_forever()
    finally:
        _agent.close()
