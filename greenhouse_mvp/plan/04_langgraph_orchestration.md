# Plan 04: LangGraph Orchestration and NotebookLM Agent

## Overview

The orchestration layer is a **LangGraph `StateGraph`** whose single cycle maps
exactly to one simulation timestep. For every tick the graph:

1. Receives telemetry from the MQTT bus.
2. Asks the MPC to propose an action.
3. Checks OOD metrics.
4. Optionally invokes the NotebookLM Supervisor agent.
5. Routes to Approve, Override, or Reject (re-plan).
6. Publishes the final approved action back to the bus.

---

## 1. Graph State (`GraphState`)

Defined in `orchestration/schemas.py` (see Plan 01). Key fields:

```python
class GraphState(TypedDict):
    telemetry: TelemetryPayload | None
    proposed_action: ActionPayload | None
    ood_metrics: OODMetrics | None
    supervisor_verdict: SupervisorVerdict | None
    final_action: ActionPayload | None
    ood_detected: bool
    retry_count: int
    max_retries: int          # default 2
    episode_log: list[dict]
```

---

## 2. Node Catalogue

| Node name | Module | Responsibility |
|---|---|---|
| `ingest_telemetry` | graph_workflow.py | Read the latest `TelemetryPayload` from a thread-safe queue fed by MQTT. |
| `run_mpc` | graph_workflow.py | Call `MPCController.step(telemetry)`. Write `proposed_action` + `ood_metrics` to state. |
| `check_ood` | graph_workflow.py | Set `ood_detected = not ood_metrics.in_distribution`. |
| `supervisor_review` | graph_workflow.py | Call `NotebookLMAgent.review(state)`. Write `supervisor_verdict` to state. |
| `apply_override` | graph_workflow.py | Replace `proposed_action` with `supervisor_verdict.override_action`. |
| `approve_action` | graph_workflow.py | Mark `final_action = proposed_action` with `approved=True`. Publish to MQTT. |
| `reject_replan` | graph_workflow.py | Increment `retry_count`. Clear `proposed_action`. Route back to `run_mpc` or abort. |
| `log_step` | graph_workflow.py | Append a summary dict to `episode_log`. Always runs last. |

---

## 3. Graph Edges and Conditional Routing

```
START
  │
  ▼
ingest_telemetry
  │
  ▼
run_mpc
  │
  ▼
check_ood ──────────────────────────────────────────────┐
  │                                                     │
  │ [ood_detected = False]                              │ [ood_detected = True]
  ▼                                                     ▼
approve_action                                  supervisor_review
  │                                                     │
  │                                      ┌──────────────┼──────────────┐
  │                                      │              │              │
  │                                  APPROVE        OVERRIDE        REJECT
  │                                      │              │              │
  │                                      │         apply_override      │
  │                                      │              │              │
  │                                      └──────┬───────┘              │
  │                                             │                      │
  │                                        approve_action        reject_replan
  │                                             │                      │
  │                                             │          ┌───────────┴────────────┐
  │                                             │          │ retry_count < max_retries│
  │                                             │          │           │             │
  │                                             │      run_mpc   [abort: use fallback]
  │                                             │                     │
  │                                             │                approve_action
  ▼                                             ▼                     ▼
log_step ◄──────────────────────────────────────────────────────────────
  │
  ▼
END (return to event loop for next tick)
```

### Conditional edge: `route_after_check_ood`

```python
def route_after_check_ood(state: GraphState) -> str:
    if state["ood_detected"]:
        return "supervisor_review"
    return "approve_action"
```

### Conditional edge: `route_after_supervisor`

```python
def route_after_supervisor(state: GraphState) -> str:
    verdict = state["supervisor_verdict"]
    if verdict.decision == "APPROVE":
        return "approve_action"
    if verdict.decision == "OVERRIDE":
        return "apply_override"
    # REJECT
    if state["retry_count"] < state["max_retries"]:
        return "reject_replan"
    # Exhausted retries: log warning, approve best-effort fallback
    return "approve_action"
```

---

## 4. Graph Construction (`graph_workflow.py`)

```python
from langgraph.graph import StateGraph, END

def build_graph(mpc_ctrl: MPCController, agent: NotebookLMAgent, bus: MQTTBus):
    sg = StateGraph(GraphState)

    sg.add_node("ingest_telemetry",  make_ingest_node(bus))
    sg.add_node("run_mpc",           make_mpc_node(mpc_ctrl, bus))
    sg.add_node("check_ood",         check_ood_node)
    sg.add_node("supervisor_review", make_supervisor_node(agent))
    sg.add_node("apply_override",    apply_override_node)
    sg.add_node("approve_action",    make_approve_node(bus))
    sg.add_node("reject_replan",     reject_replan_node)
    sg.add_node("log_step",          log_step_node)

    sg.set_entry_point("ingest_telemetry")
    sg.add_edge("ingest_telemetry", "run_mpc")
    sg.add_edge("run_mpc", "check_ood")

    sg.add_conditional_edges("check_ood", route_after_check_ood, {
        "supervisor_review": "supervisor_review",
        "approve_action":    "approve_action",
    })

    sg.add_conditional_edges("supervisor_review", route_after_supervisor, {
        "approve_action": "approve_action",
        "apply_override": "apply_override",
        "reject_replan":  "reject_replan",
    })

    sg.add_edge("apply_override", "approve_action")
    sg.add_edge("reject_replan",  "run_mpc")
    sg.add_edge("approve_action", "log_step")
    sg.add_edge("log_step", END)

    return sg.compile()
```

---

## 5. NotebookLM Agent (`agents/notebooklm_agent.py`)

### 5.1 Role

The `NotebookLMAgent` acts as the **Supervisor**: it receives the current
state (telemetry + proposed action + OOD metrics) and returns a
`SupervisorVerdict` JSON.

### 5.2 Prompt Engineering

The agent formats the state into a structured prompt:

```
SYSTEM:
You are a greenhouse climate control supervisor.
You receive sensor telemetry, an MPC-proposed actuator action,
and out-of-distribution (OOD) metrics.
Your task: decide whether to APPROVE, OVERRIDE, or REJECT the action.
Respond ONLY with a valid JSON object matching this schema:
{
  "step": <int>,
  "decision": "APPROVE" | "REJECT" | "OVERRIDE",
  "override_action": <ActionPayload JSON or null>,
  "reason": "<brief explanation>",
  "confidence": <float 0-1>
}

USER:
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
  Max SINDy Residual   : {max_residual:.4f}
```

### 5.3 Class API

```python
class NotebookLMAgent:
    def __init__(self, api_key: str, notebook_id: str, model: str = "notebooklm"): ...

    def review(self, state: GraphState) -> SupervisorVerdict:
        """
        1. Build prompt from state.
        2. Call NotebookLM API (or compatible OpenAI-format endpoint).
        3. Parse JSON response into SupervisorVerdict.
        4. Return verdict.
        """

    def _build_prompt(self, state: GraphState) -> tuple[str, str]:
        """Returns (system_prompt, user_prompt)."""

    def _parse_verdict(self, raw_json: str, step: int) -> SupervisorVerdict:
        """
        Parse LLM response. If JSON is malformed or decision is invalid,
        default to SupervisorVerdict(decision='APPROVE', reason='Parse error – defaulting to approve').
        Never raise an exception that could stall the simulation.
        """
```

### 5.4 API Contract

NotebookLM does not currently have a public programmatic API that returns
JSON-structured output. The wrapper is designed to be **backend-agnostic**:

- **Production**: Call Google NotebookLM via its HTTP endpoint (when available).
- **Development / MVP**: Use the OpenAI-compatible `chat/completions` endpoint
  (GPT-4o-mini or local Ollama). Swap by changing the constructor parameter.

```python
class NotebookLMAgent:
    def __init__(
        self,
        backend: Literal["openai", "ollama", "notebooklm"] = "openai",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ): ...
```

The abstraction means the rest of the graph is completely decoupled from which
LLM backend is active.

### 5.5 Failure Modes and Safety

| Failure | Behaviour |
|---|---|
| Network timeout | Return `APPROVE` with `confidence=0.0`, log warning |
| Malformed JSON | Return `APPROVE` (fail-safe), log the raw response |
| `OVERRIDE` with invalid action | Fall back to `APPROVE` of MPC proposal |
| Rate limit / 429 | Return `APPROVE`, record in `episode_log` for DAgger |

The principle: **the Supervisor may add safety, but must never halt the simulation**.

---

## 6. Event Loop (`graph_workflow.py`)

The compiled LangGraph is driven by a simple synchronous loop:

```python
def run_episode(graph, initial_state: GraphState) -> list[dict]:
    state = initial_state
    while True:
        state = graph.invoke(state)
        if state.get("_terminated"):   # set by log_step_node when env is done
            break
    return state["episode_log"]
```

`ingest_telemetry` blocks on a `queue.Queue` that the MQTT callback fills.
This keeps the LangGraph loop synchronised with the simulation without polling.

```python
# In SimAdapter: after publishing telemetry, also push to the queue
telemetry_queue.put(telemetry_payload)

# In ingest_telemetry node:
def make_ingest_node(queue: Queue):
    def ingest_telemetry(state: GraphState) -> GraphState:
        tel = queue.get(timeout=60.0)   # blocks here
        return {**state, "telemetry": tel, "retry_count": 0,
                "proposed_action": None, "supervisor_verdict": None}
    return ingest_telemetry
```

---

## 7. DAgger Integration Hook

`log_step_node` appends to `episode_log`. After every N steps (e.g., 96 = 1 day),
an optional `retrain_hook` can be called:

```python
def log_step_node(state: GraphState) -> GraphState:
    entry = {
        "step": state["telemetry"].step,
        "t_in": state["telemetry"].t_in,
        "co2":  state["telemetry"].co2,
        "rh":   state["telemetry"].rh,
        "action": state["final_action"].model_dump(),
        "ood":    state["ood_metrics"].model_dump(),
        "verdict": state["supervisor_verdict"].decision
                   if state["supervisor_verdict"] else "AUTO_APPROVE",
    }
    new_log = state["episode_log"] + [entry]

    if len(new_log) % RETRAIN_INTERVAL == 0:
        trigger_dagger_retrain(new_log)   # async, non-blocking

    return {**state, "episode_log": new_log}
```

`trigger_dagger_retrain` is fire-and-forget (runs in a `threading.Thread`). The
current SINDy model remains active during retraining. Once complete, it calls
`MPCController.update_model(...)` atomically.
