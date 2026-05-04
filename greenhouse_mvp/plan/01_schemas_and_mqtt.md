# Plan 01: Pydantic Schemas and MQTT Bus

## Overview

All inter-module communication travels over a single MQTT broker. Every message is
validated at the boundary using **Pydantic v2** models. Nothing enters or leaves a
module as a raw dict.

---

## 1. MQTT Topic Map

| Topic | Direction | Publisher | Subscriber(s) | Payload Schema |
|---|---|---|---|---|
| `greenhouse/telemetry` | Sim → Bus | `SimAdapter` | `GraphWorkflow`, `MPCController` | `TelemetryPayload` |
| `greenhouse/action/proposed` | MPC → Bus | `MPCController` | `GraphWorkflow` (Supervisor node) | `ActionPayload` |
| `greenhouse/action/approved` | Bus → Sim | `GraphWorkflow` | `SimAdapter` | `ActionPayload` |
| `greenhouse/supervisor/verdict` | Agent → Bus | `NotebookLMAgent` | `GraphWorkflow` | `SupervisorVerdict` |
| `greenhouse/ood/metrics` | Core → Bus | `MPCController` | `GraphWorkflow` | `OODMetrics` |

**QoS levels**:
- Telemetry: QoS 0 (best-effort, high frequency)
- Action proposals/approvals: QoS 1 (at-least-once, must not be lost)
- Supervisor verdicts: QoS 1

---

## 2. Pydantic Schemas (`orchestration/schemas.py`)

### 2.1 `TelemetryPayload`

Published by `SimAdapter` after every `env.step()` call.

```python
class TelemetryPayload(BaseModel):
    step: int                    # Global simulation step counter
    timestamp_sim: float         # Simulation time in seconds from episode start
    # Controlled states
    t_in: float                  # Indoor temperature [°C]
    co2: float                   # Indoor CO2 concentration [ppm]
    rh: float                    # Relative humidity [%]
    # External disturbances (TVP for MPC)
    T_out: float                 # Outdoor temperature [°C]
    rad: float                   # Solar radiation [W/m²]
    co2_out: float               # Outdoor CO2 [ppm]
    # Time encoding
    sin_h: float                 # sin(2π * hour_of_day / 24)
    cos_h: float                 # cos(2π * hour_of_day / 24)
```

### 2.2 `ActionPayload`

Used for both proposed (MPC → Bus) and approved (Bus → Sim) actions.
The `approved` flag distinguishes the two.

```python
class ActionPayload(BaseModel):
    step: int                    # Must match the triggering TelemetryPayload.step
    approved: bool = False       # False = proposed; True = approved by Supervisor
    # Actuator signals [0.0, 1.0]
    uBoil: float                 # Boiler heating
    uCO2: float                  # CO2 injection
    uThScr: float                # Thermal screen
    uVent: float                 # Ventilation
    uLamp: float                 # Supplementary lighting
    uBlScr: float                # Blackout screen

    @model_validator(mode='after')
    def clamp_actuators(self) -> 'ActionPayload':
        for field in ['uBoil', 'uCO2', 'uThScr', 'uVent', 'uLamp', 'uBlScr']:
            setattr(self, field, max(0.0, min(1.0, getattr(self, field))))
        return self
```

### 2.3 `OODMetrics`

Published by `MPCController` alongside the proposed action to quantify how far the
current state is from the SINDy training distribution.

```python
class OODMetrics(BaseModel):
    step: int
    mahalanobis_distance: float  # Distance from training set centroid
    max_residual: float          # Max absolute SINDy one-step prediction error
    in_distribution: bool        # True if mahalanobis_distance < threshold
    threshold_used: float        # The threshold applied (e.g., 3.0 sigma)
```

### 2.4 `SupervisorVerdict`

Returned by the `NotebookLMAgent` after evaluating the proposed action and OOD metrics.

```python
class SupervisorVerdict(BaseModel):
    step: int
    decision: Literal['APPROVE', 'REJECT', 'OVERRIDE']
    # If OVERRIDE, these values replace the MPC proposal
    override_action: ActionPayload | None = None
    reason: str                  # Human-readable explanation from LLM
    confidence: float            # [0.0, 1.0] LLM self-reported confidence
```

### 2.5 `GraphState` (LangGraph)

The shared mutable state that flows through the LangGraph `StateGraph`.
Each node reads from it and writes back to it.

```python
class GraphState(TypedDict):
    # Current tick data
    telemetry: TelemetryPayload | None
    proposed_action: ActionPayload | None
    ood_metrics: OODMetrics | None
    supervisor_verdict: SupervisorVerdict | None
    # Final resolved action (may be MPC proposal or LLM override)
    final_action: ActionPayload | None
    # Routing flags
    ood_detected: bool
    retry_count: int             # Number of times MPC was asked to re-plan
    max_retries: int             # Config: abort to fallback after N retries
    # Accumulator for logging / DAgger data collection
    episode_log: list[dict]
```

---

## 3. MQTT Bus Client (`orchestration/mqtt_bus.py`)

The bus is a thin wrapper around `paho.mqtt.client.Client`. It must be:
- **Thread-safe**: callbacks fire in the Paho network thread; handlers must not
  block it.
- **Schema-enforcing**: `publish()` accepts a `BaseModel` and serialises it;
  `subscribe()` deserialises into the declared schema before calling the handler.

### Key API

```python
class MQTTBus:
    def __init__(self, host: str, port: int = 1883): ...

    def publish(self, topic: str, payload: BaseModel, qos: int = 0) -> None:
        """Serialise payload to JSON and publish."""

    def subscribe(
        self,
        topic: str,
        schema: type[BaseModel],
        handler: Callable[[BaseModel], None],
        qos: int = 0,
    ) -> None:
        """Register a typed handler; deserialisation + validation happen here."""

    def loop_start(self) -> None: ...   # Start background network thread
    def loop_stop(self) -> None: ...    # Graceful shutdown
```

### Design Notes

- `publish` calls `payload.model_dump_json()` → bytes, then `client.publish()`.
- `subscribe` stores `(schema, handler)` keyed by topic. `on_message` looks up the
  pair, calls `schema.model_validate_json(msg.payload)`, then calls `handler`.
- If validation fails, log the error and **do not** call the handler (fail-safe).
- Reconnect logic: use `on_disconnect` to schedule exponential back-off reconnects
  (max 5 attempts, delays 1 s → 2 s → 4 s → 8 s → 16 s).

---

## 4. Serialisation Contract

All schemas must be serialisable to JSON with no custom types:
- `float` for all numeric values (no `np.float32`).
- `int` for step counters.
- `Literal` strings for categorical decisions.
- Timestamps as `float` (seconds).

At the publisher boundary, convert numpy scalars: `float(np.float32(x))`.
