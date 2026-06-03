# Greenhouse Control Architecture

This document describes the current implementation. The runtime architecture is
FastAPI + Server-Sent Events + a single in-process simulation runner. The older
MQTT/Streamlit architecture has been removed from the active code path.

## Runtime Services

The default stack is defined in `docker-compose.yml`.

```text
docker compose
  |
  +-- sindy_bootstrap
  |     command: python -m greenhouse_mvp.sindy_pipeline.bootstrap
  |     output : /app/models/sindy_model.pkl in model_store volume
  |
  +-- api_server
  |     command: python -m greenhouse_mvp.api.server
  |     port   : 8000
  |     uses   : model_store volume
  |
  +-- dashboard
        build  : ./dashboard
        port   : 8080
        serves : React app through nginx
        proxy  : /api/* -> api_server:8000/api/*
```

The API service depends on the bootstrap service completing successfully. This
means the controller starts with a SINDy artifact already available.

## Data Flow

```text
React dashboard
  |
  | REST commands
  |   POST /api/start
  |   POST /api/stop
  |   POST /api/reset
  |   POST /api/control
  |   POST /api/controller
  |   POST /api/agent
  |   GET/POST /api/config
  |   POST /api/incidents           ← trigger a named incident
  |   DELETE /api/incidents/{id}    ← resolve an incident
  |   GET /api/incidents            ← list active incidents
  |   GET /api/incidents/catalog    ← available incident types
  |
  | SSE events
  |   GET /api/events
  v
FastAPI server
  v
SimulationRunner background thread
  v
gl_gym/GreenLightTomato-v0
  |
  +-- obs_to_telemetry()
  +-- optional sensor fault injection   (FaultInjector)
  +-- incident physics disturbances     (IncidentManager.apply_to_telemetry)
  +-- LangGraph workflow
  |     |
  |     +-- MPC controller, or
  |     +-- LLM controller
  |     +-- optional LLM supervisor on OOD
  |     +-- IncidentDetector node (LLM anomaly detection + repair recommendations)
  |
  +-- optional actuator fault injection (FaultInjector)
  +-- incident actuator constraints     (IncidentManager.apply_to_action)
  +-- env.step(action)
```

## One Simulation Step

1. `SimulationRunner._run()` receives the current observation from the GreenLight
   Gym environment.
2. `obs_to_telemetry()` maps the observation into `TelemetryPayload`.
3. `FaultInjector.inject_sensor()` optionally modifies sensor telemetry (low-level faults).
4. `IncidentManager.apply_to_telemetry()` applies physics disturbances from active
   incidents (e.g., temperature drift from door open, humidity spike).
5. The telemetry event is emitted to SSE subscribers.
6. The active controller mode is read from live runner state:
   - `mpc` routes to `MPCController.step()`;
   - `llm` routes to `LLMController.step()`.
7. MPC mode computes:
   - an `ActionPayload`;
   - `OODMetrics` using scaled physics features and Mahalanobis distance.
8. If OOD is detected and the supervisor is enabled, `NotebookLMAgent.review()`
   may approve, reject, or override the action.
9. The resolved action is marked approved and emitted through SSE.
10. `IncidentDetector` node runs if heuristic triggers fire and cooldown elapsed:
    - Analyses telemetry history and actuator response patterns.
    - Emits `incident_report` SSE event with detected type, repair steps, urgency.
11. `FaultInjector.inject_actuator()` optionally modifies the action vector.
12. `IncidentManager.apply_to_action()` applies actuator constraints from active
    incidents (e.g., boiler dead from heater failure, forced vent open from stuck vent).
13. `env.step(action_vec)` advances the simulator.

## Backend Modules

| Module | Responsibility |
| --- | --- |
| `greenhouse_mvp.api.server` | FastAPI app, REST endpoints, SSE endpoint |
| `greenhouse_mvp.api.simulation_runner` | lifecycle and background simulation loop |
| `greenhouse_mvp.orchestration.graph_workflow` | LangGraph workflow for one control step |
| `greenhouse_mvp.orchestration.schemas` | Pydantic models shared by API, runner, dashboard |
| `greenhouse_mvp.environment.sim_adapter` | conversion between gym observations/actions and schemas |
| `greenhouse_mvp.environment.fault_injector` | sensor and actuator fault injection (low-level) |
| `greenhouse_mvp.environment.incident_manager` | named incident catalogue, physics disturbances, actuator constraints |
| `greenhouse_mvp.environment.tvp_forecast` | MPC time-varying weather forecast provider |
| `greenhouse_mvp.control_core.mpc_controller` | SINDy-backed do-mpc controller and OOD metrics |
| `greenhouse_mvp.control_core.llm_controller` | direct LLM actuator controller |
| `greenhouse_mvp.agents.notebooklm_agent` | LLM supervisor for MPC proposals |
| `greenhouse_mvp.agents.incident_detector` | LLM anomaly detector with repair recommendations |
| `greenhouse_mvp.sindy_pipeline.bootstrap` | data collection and SINDy artifact creation |
| `greenhouse_mvp.sindy_pipeline.physics_features` | vector and scalar physics feature builders |
| `greenhouse_mvp.sindy_pipeline.sindy_fitter` | SINDy training and persistence helpers |

## SINDy Bootstrap

`sindy_bootstrap` runs before the API server.

```text
gl_gym headless episode
  |
  +-- rule-based controller with small exploration noise
  +-- states      : [t_in, co2, rh]
  +-- weather     : [T_out, rad, co2_out]
  +-- time_enc    : [sin_h, cos_h]
  +-- actions     : [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
  v
compute_physics_features()
  v
SINDyFitter.fit()
  v
/app/models/sindy_model.pkl
```

The artifact contains:

- `model`: fitted `pysindy.SINDy` model;
- `scaler_x`: state scaler;
- `scaler_u`: physics feature scaler;
- `mu_train`, `cov_inv`: OOD statistics;
- raw training arrays for future retraining/debugging.

## MPC Controller

The MPC controller embeds the SINDy dynamics in a discrete `do_mpc` model:

```text
x(k+1) = Xi * Theta(x(k), u(k), weather(k), time(k))
```

Controlled state:

- `t_in`: indoor temperature;
- `co2`: indoor CO2 concentration;
- `rh`: relative humidity.

Actuators:

- `uBoil`;
- `uCO2`;
- `uThScr`;
- `uVent`;
- `uLamp`;
- `uBlScr`.

Targets:

- temperature: 18-22 C, setpoint 20 C;
- CO2: 600-1000 ppm, setpoint 800 ppm;
- relative humidity: max 85%.

`WeatherForecastTVP` is created with the same horizon as `MPCController`, so the
time-varying parameter template matches the configured MPC horizon.

## OOD Detection

OOD is computed on the scaled feature vector used by the SINDy model:

```text
d = sqrt((f - mu_train)^T * cov_inv * (f - mu_train))
```

The feature vector is built by `compute_physics_features_single()` for online
control paths and by `compute_physics_features()` for bootstrap batches. The
current threshold is `OOD_THRESHOLD = 6.0`.

If `d >= threshold`:

- the step is marked out-of-distribution;
- if the supervisor is enabled and warmup/cooldown allow it, the LLM supervisor
  reviews the MPC proposal.

## LLM Modes

There are two LLM uses:

| Mode | Trigger | Output |
| --- | --- | --- |
| LLM controller | `controller_mode = "llm"` | direct actuator action through `set_actuators` |
| LLM supervisor | `controller_mode = "mpc"` and OOD detected | `APPROVE`, `REJECT`, or `OVERRIDE` verdict |

Both use an OpenAI-compatible chat endpoint configured through:

- `OPENAI_API_KEY`;
- `OPENAI_BASE_URL`;
- `LLM_MODEL`;
- `LLM_TIMEOUT`.

## Dashboard

The active dashboard is the React/Vite app in `dashboard/src`.

It consumes:

- REST endpoints for control/config actions;
- `/api/events` SSE for telemetry, actions, OOD metrics, supervisor verdicts,
  and LLM reasoning logs.

The production dashboard image serves static files through nginx and proxies
`/api/*` to the backend service.

## API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/status` | current runner status (includes `active_incidents`) |
| `GET` | `/api/config` | current simulation config |
| `POST` | `/api/config` | update config for next start/reset |
| `POST` | `/api/start` | start simulation |
| `POST` | `/api/stop` | stop simulation |
| `POST` | `/api/reset` | reset current episode (clears all incidents) |
| `POST` | `/api/control` | pause/resume and speed multiplier |
| `POST` | `/api/controller` | switch `mpc` / `llm` |
| `POST` | `/api/agent` | enable/disable LLM supervisor |
| `GET` | `/api/events` | SSE stream |
| `GET` | `/api/incidents` | list active incidents |
| `GET` | `/api/incidents/catalog` | available incident types with metadata |
| `POST` | `/api/incidents` | trigger a named incident (`IncidentSpec` body) |
| `DELETE` | `/api/incidents/{id}` | resolve an active incident |

## SSE Event Types

| Type | When emitted | Payload |
| --- | --- | --- |
| `telemetry` | Every step | `TelemetryPayload` |
| `action` | Every step | `ActionPayload` (approved) |
| `ood` | Every MPC step | `OODMetrics` |
| `verdict` | When supervisor runs | `SupervisorVerdict` |
| `llm_action` | Every LLM controller step | reasoning + actuator values |
| `incident` | On trigger / resolve / expiry | `IncidentAlert` |
| `incident_report` | When detector runs | detection type, repair steps, urgency |
| `reset` | On episode reset | `{}` |
| `episode_done` | Episode terminated | `{"step": N}` |
| `heartbeat` | Every 25 s of inactivity | `{}` |

## Incident System

### Incident Types

| Key | Effect |
| --- | --- |
| `door_open` | Temperature drifts toward T_out; CO2 dilutes; forced minimum ventilation |
| `heater_failure` | Boiler actuator dead — t_in will drop |
| `co2_supply_failure` | CO2 injector dead — CO2 drops toward ambient |
| `ventilation_stuck_open` | Vent fixed at 40–90% open (severity scaled) |
| `ventilation_stuck_closed` | Vent actuator dead at 0 |
| `lamp_failure` | Lamp actuator dead |
| `thermal_screen_broken` | Thermal screen actuator dead at 0 |
| `sensor_temp_stuck` | t_in reading frozen at value when incident started |
| `sensor_co2_drift` | CO2 reading drifts up/down with growing offset |
| `sensor_rh_failure` | rh reading replaced with random noise |
| `power_surge` | All actuators dead for `duration_steps` |
| `high_humidity_event` | rh increases each step until incident resolved |

### Incident Detection

The `IncidentDetector` LLM agent is triggered by heuristics:
- OOD Mahalanobis distance ≥ threshold
- `uBoil > 0.5` for 5 steps but t_in not rising
- `uCO2 > 0.3` for 5 steps but CO2 not rising
- CO2 < 300 ppm or > 3000 ppm; RH < 5% or > 97%
- t_in constant for 5 steps (sensor stuck indicator)

30-step cooldown and 20-step warmup prevent excessive LLM calls.
Detection results emitted as `incident_report` SSE events.

## Ports

| Service | Port |
| --- | --- |
| API server | `8000` |
| Dashboard | `8080` |
