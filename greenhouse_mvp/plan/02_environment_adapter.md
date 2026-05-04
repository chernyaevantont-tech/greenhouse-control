# Plan 02: Environment Adapter (`environment/sim_adapter.py`)

## Overview

The `SimAdapter` wraps `gl_gym/GreenLightTomato-v0` in a **synchronous,
event-driven shell**. The simulation never advances unless it has received an
explicit approved action from the orchestration layer. This is the key principle
that makes the architecture cyber-physical: the sim is just another "device" on
the MQTT bus.

---

## 1. Synchronisation Mechanism

The simulation loop is blocked using a `threading.Event` object called
`_action_event`. The flow is:

```
SimAdapter.loop_forever()
│
├─ env.reset()
│
└─ while not done:
       │
       ├─ 1. Observe: read obs → build TelemetryPayload
       ├─ 2. Publish:  bus.publish("greenhouse/telemetry", telemetry)
       ├─ 3. BLOCK:    _action_event.wait(timeout=T)      ← freezes here
       │                   ↑
       │       [MQTT thread fires on_action_approved()]
       │       [sets self._pending_action and calls _action_event.set()]
       │
       ├─ 4. UNBLOCK:  _action_event.clear()
       ├─ 5. Step:     obs, reward, done, _ = env.step(self._pending_action)
       └─ 6. LOOP
```

The `_action_event.wait(timeout=T)` call blocks the simulation thread without
busy-waiting. If no action arrives within `timeout` seconds (default 30 s), the
adapter falls back to a rule-based safe action and logs a warning. This prevents
the simulation from hanging indefinitely if the orchestration layer crashes.

---

## 2. Class Design

```python
class SimAdapter:
    def __init__(
        self,
        bus: MQTTBus,
        env_id: str = "gl_gym/GreenLightTomato-v0",
        start_date: str = "2010-02-28",
        n_days: int = 60,
        period: int = 900,
        action_timeout_s: float = 30.0,
    ):
        self._bus = bus
        self._env: gym.Env | None = None
        self._action_event = threading.Event()
        self._pending_action: np.ndarray | None = None
        self._step = 0
        self._done = False
        ...
```

### Key Methods

| Method | Thread | Description |
|---|---|---|
| `loop_forever()` | Main | Runs the blocking sim loop. Call from the main thread. |
| `on_action_approved(msg: ActionPayload)` | MQTT | MQTT callback. Unpacks action, sets `_pending_action`, fires `_action_event`. |
| `_build_telemetry(obs, step)` | Main | Constructs `TelemetryPayload` from a raw gym obs dict. |
| `_safe_fallback_action()` | Main | Returns a minimal rule-based action for timeout recovery. |
| `reset(seed)` | Main | Calls `env.reset()` and returns initial telemetry without stepping. |
| `close()` | Main | Calls `env.close()` and disconnects the bus. |

---

## 3. `loop_forever()` — Detailed Logic

```
def loop_forever():
    obs, _ = env.reset(options={"start_date": start_date}, seed=42)
    _publish_telemetry(obs, step=0)

    while not _done:
        # --- BLOCK until action arrives or timeout ---
        arrived = _action_event.wait(timeout=action_timeout_s)
        _action_event.clear()

        if not arrived:
            logger.warning("Action timeout at step %d. Using fallback.", _step)
            action_vec = _safe_fallback_action()
        else:
            action_vec = _pending_action   # set by on_action_approved()

        # --- STEP ---
        obs, reward, terminated, truncated, info = env.step(action_vec)
        _step += 1
        _done = terminated or truncated

        # --- PUBLISH next telemetry ---
        if not _done:
            _publish_telemetry(obs, step=_step)

    logger.info("Episode finished after %d steps.", _step)
```

---

## 4. `on_action_approved()` — MQTT Callback

This method is called by the Paho MQTT **network thread** (not the main thread).
It must be fast and non-blocking.

```
def on_action_approved(msg: ActionPayload):
    # Validate that the action corresponds to the *current* step
    if msg.step != _step:
        logger.warning(
            "Stale action for step %d (current: %d). Ignoring.", msg.step, _step
        )
        return

    if not msg.approved:
        logger.error("Received unapproved action. Ignoring.")
        return

    _pending_action = np.array([
        msg.uBoil, msg.uCO2, msg.uThScr,
        msg.uVent, msg.uLamp, msg.uBlScr
    ], dtype=np.float32)

    _action_event.set()   # Unblocks loop_forever()
```

**Thread safety**: `_pending_action` is written in the MQTT thread and read in
the main thread. The assignment of a reference in CPython is atomic (GIL), so no
explicit lock is needed for a single-writer / single-reader pattern. If porting to
a non-CPython runtime, wrap in `threading.Lock`.

---

## 5. `_build_telemetry()` — Obs Extraction

The gym observation is a dict of module arrays. Map them to `TelemetryPayload`:

```python
def _build_telemetry(self, obs: dict, step: int) -> TelemetryPayload:
    indoor = obs["IndoorClimateObservations"]   # [co2_ppm, t_in, rh]
    weather = obs["WeatherObservations"]         # [rad, T_out, ?, co2_out, ...]
    
    hour_of_day = (step * self._period / 3600.0) % 24.0

    return TelemetryPayload(
        step=step,
        timestamp_sim=float(step * self._period),
        t_in=float(indoor[1]),
        co2=float(indoor[0]),
        rh=float(indoor[2]),
        T_out=float(weather[1]),
        rad=float(weather[0]),
        co2_out=float(weather[3]),
        sin_h=float(np.sin(2 * np.pi * hour_of_day / 24.0)),
        cos_h=float(np.cos(2 * np.pi * hour_of_day / 24.0)),
    )
```

> **Important**: Observation indices are verified against the notebook's working
> code. `IndoorClimateObservations[0]` = co2, `[1]` = t_in, `[2]` = rh.

---

## 6. `_safe_fallback_action()` — Timeout Recovery

When the orchestration layer is slow or unavailable, the adapter applies a minimal
safe action: keep heating on at 30%, ventilation closed, CO2 off.

```python
def _safe_fallback_action(self) -> np.ndarray:
    # [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
    return np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)
```

---

## 7. `tvp_forecast.py` — Weather Preview for MPC

MPC needs a `horizon`-step lookahead of external disturbances. The
`WeatherForecastTVP` class (already prototyped in the notebook) runs a **shadow
episode** of the same env at construction time to pre-harvest weather data.

### Lifecycle

1. `__init__` instantiates a **separate** env (not the main simulation env).
2. Runs for `(n_days * steps_per_day) + horizon` steps with zero actions.
3. Stores `T_out`, `rad`, `co2_out`, `sin_h`, `cos_h` arrays.
4. Exposes `get_mpc_tvp_fun(mpc)` → a closure that returns a filled
   `tvp_template` for `do_mpc`.

### `get_mpc_tvp_fun` Contract

```python
def tvp_fun(t_now: float) -> do_mpc.TVPTemplate:
    k_start = int(t_now / period)
    for k in range(horizon):
        idx = min(k_start + k, len(T_out_arr) - 1)
        tvp_template['_tvp', k, 'T_out']   = T_out_arr[idx]
        tvp_template['_tvp', k, 'rad']     = rad_arr[idx]
        tvp_template['_tvp', k, 'co2_out'] = co2_out_arr[idx]
        tvp_template['_tvp', k, 'sin_h']   = sin_h_arr[idx]
        tvp_template['_tvp', k, 'cos_h']   = cos_h_arr[idx]
    return tvp_template
```

---

## 8. Subscription Registration

`SimAdapter.__init__` registers itself on the bus:

```python
bus.subscribe(
    topic="greenhouse/action/approved",
    schema=ActionPayload,
    handler=self.on_action_approved,
    qos=1,
)
```

---

## 9. Error Handling and Edge Cases

| Scenario | Behaviour |
|---|---|
| Action arrives for wrong step | Ignored; warning logged |
| Unapproved action arrives on approved topic | Ignored; error logged |
| `env.step()` raises an exception | Log + re-raise; episode terminates cleanly |
| MQTT disconnects during wait | `_action_event` never fires → timeout fallback triggers |
| `n_days` exhausted | `terminated=True` → `loop_forever()` exits naturally |
