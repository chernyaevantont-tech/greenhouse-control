# Greenhouse Control — Architecture Overview

## Services

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Docker Compose Stack                               │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │sindy_bootstrap│  │  sim_adapter │   │ control_core │   │orchestration│ │
│  │  (runs once) │  │   port —     │   │   port —     │   │   port —    │ │
│  └──────┬───────┘  └──────┬───────┘   └──────┬───────┘   └──────┬──────┘ │
│         │                 │                   │                   │        │
│         │ model_store     │ MQTT              │ MQTT              │ MQTT   │
│         ▼ (volume)        ▼                   ▼                   ▼        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │               Eclipse Mosquitto 2 (mqtt_broker)                      │  │
│  │               TCP :1883  ·  WebSocket :9001                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────┐   ┌──────────────────────────────────────────────────┐   │
│  │  llm_agent   │   │  dashboard  (nginx:alpine)                       │   │
│  │  port 8081   │   │  port 8080  · dashboard/static/index.html        │   │
│  └──────────────┘   └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## One simulation step — full data flow

```
  gl_gym env                    sim_adapter
  ──────────────────────────────────────────────────────
  env.step(action) ──► obs dict
                           │
                           ▼
                    TelemetryPayload
                    {step, t_in, co2, rh,
                     T_out, rad, co2_out,
                     sin_h, cos_h}
                           │
                           │ MQTT  greenhouse/telemetry  QoS 0
                           ▼
  ──────────────────────────────────────────────────────
                      orchestration  (LangGraph StateGraph)
  ──────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────────────────┐
  │ ingest_telemetry                                                │
  │   blocks on telemetry_queue.get()                              │
  │   resets per-tick state fields                                 │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ run_mpc  (control_core.MPCController.step)                      │
  │                                                                 │
  │  1. Scale state:  [t_in, co2, rh] → StandardScaler             │
  │  2. Compute physics features (18-d):                            │
  │       [T_out, rad, co2_out, sin_h, cos_h,                       │
  │        uBoil…uBlScr,                                            │
  │        psat, vpd, S_eff, t_S_eff, h_uVent, dc_uVent, t_uBoil] │
  │  3. OOD check: Mahalanobis distance on feature space            │
  │       d = sqrt((f-μ)ᵀ Σ⁻¹ (f-μ))                              │
  │       in_distribution = d < OOD_THRESHOLD (3.0 σ)              │
  │  4. do_mpc solve over horizon H=20 steps                        │
  │       model: x_{k+1} = Ξᵀ · Θ(x_k, u_k)  (SINDy equations)   │
  │       TVP:   weather forecast pre-computed by WeatherForecastTVP│
  │       objective: minimise (t_in−20)² + (co2−800)²              │
  │  5. Publish proposed ActionPayload on greenhouse/action/proposed│
  │  6. Publish OODMetrics on greenhouse/ood/metrics                │
  │                                                                 │
  │  returns → (ActionPayload, OODMetrics)                          │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ check_ood                                                       │
  │   ood_detected = not OODMetrics.in_distribution                │
  └────────────────────────┬────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
       in_distribution             out-of-distribution
              │                         │
              ▼                         ▼
       approve_action          supervisor_review
                               (NotebookLMAgent)
                                        │
                               LLM POST /v1/chat/completions
                               model: qwen3.5-9b via LM Studio
                               returns SupervisorVerdict
                               {decision: APPROVE|REJECT|OVERRIDE,
                                override_action?, reason, confidence}
                                        │
                        ┌──────────────┬┴──────────────┐
                     APPROVE        OVERRIDE          REJECT
                        │               │                │
                        ▼               ▼         retry_count < max?
                approve_action   apply_override          │
                                  (replace action)  ┌───┴──────┐
                                        │           yes        no
                                        ▼            │          │
                                approve_action   reject_replan  approve_action
                                                (→ run_mpc)    (best-effort)

  ┌─────────────────────────────────────────────────────────────────┐
  │ approve_action                                                  │
  │   action.approved = True                                        │
  │   MQTT publish  greenhouse/action/approved  QoS 1              │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ log_step                                                        │
  │   append to episode_log                                         │
  │   every 96 steps → _trigger_dagger_retrain()                   │
  └────────────────────────┬────────────────────────────────────────┘
                           │ END → loop back to ingest_telemetry
                           ▼
  ──────────────────────────────────────────────────────
  sim_adapter receives greenhouse/action/approved
  on_action_approved() → _action_event.set()
  env.step(action_vec) → next obs
  ──────────────────────────────────────────────────────
```

---

## SINDy Model (bootstrap phase)

```
  sindy_bootstrap (runs once at startup)
  ─────────────────────────────────────────────────────────────────
  gl_gym headless episode (season_length=30 days, heuristic policy)
         │
         ▼ collect N≈5760 steps
  states (N,3):     [t_in, co2, rh]
  weather (N,5):    [T_out, rad, co2_out, sin_h, cos_h]
  actions (N,6):    [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
         │
         ▼ compute_physics_features()
  phys_features (N,18):  raw + psat, vpd, S_eff, cross-terms
         │
         ▼ SINDyFitter.fit()
  1. StandardScaler on states → scaler_x
  2. StandardScaler on phys_features → scaler_u
  3. ps.SINDy(STLSQ(threshold=0.05, alpha=0.01),
              PolynomialLibrary(degree=1),
              feature_names=FEATURE_NAMES)
     .fit(x_in_scaled, u=u_in_scaled, x_dot=x_out_scaled, t=900)
  4. Ξ matrix: shape (3, 22)  — 3 equations, 22 library terms
         │
         ▼ SINDyFitter.save(path)
  /app/models/sindy_model.pkl
  bundle keys: {model, scaler_x, scaler_u,
                mu_train, cov_inv, feature_names}
```

---

## MQTT Topic Map

| Topic | QoS | Schema | Direction |
|-------|-----|--------|-----------|
| `greenhouse/telemetry` | 0 | `TelemetryPayload` | sim_adapter → all |
| `greenhouse/action/proposed` | 1 | `ActionPayload` | control_core → (internal) |
| `greenhouse/action/approved` | 1 | `ActionPayload` | orchestration → sim_adapter + dashboard |
| `greenhouse/ood/metrics` | 0 | `OODMetrics` | control_core → orchestration + dashboard |
| `greenhouse/supervisor/verdict` | 1 | `SupervisorVerdict` | orchestration → dashboard |

---

## SINDy Surrogate — State Equations

$$x_{k+1} = \Xi^T \cdot \Theta(x_k, u_k)$$

| State | Symbol | Setpoint |
|-------|--------|----------|
| Indoor temperature | $t_{in}$ [°C] | 20 °C |
| CO₂ concentration | $co_2$ [ppm] | 800 ppm |
| Relative humidity | $rh$ [%] | max 85 % |

**Actuators** $u \in [0,1]$: `uBoil` · `uCO2` · `uThScr` · `uVent` · `uLamp` · `uBlScr`

**Physics features** (non-linear cross-terms):
- $p_{sat}$ — saturation vapour pressure: $611 \cdot e^{17.27 \cdot t_{in} / (t_{in}+237.3)}$
- $\text{vpd}$ — vapour pressure deficit: $p_{sat} \cdot (1 - rh/100)$
- $S_{eff}$ — effective solar gain: $\text{rad} \cdot (1 - u_{ThScr})$
- $t \cdot S_{eff}$, $h \cdot u_{Vent}$, $dc \cdot u_{Vent}$, $t \cdot u_{Boil}$ — coupling terms

---

## OOD Detection

Mahalanobis distance on the 18-d scaled feature vector:

$$d = \sqrt{(\mathbf{f} - \boldsymbol{\mu})^T \Sigma^{-1} (\mathbf{f} - \boldsymbol{\mu})}$$

- $\boldsymbol{\mu}$, $\Sigma$ estimated on the bootstrap training set  
- Threshold: **3.0 σ** (configurable via `OOD_THRESHOLD`)  
- If $d \geq 3.0$ → LLM supervisor is called before approving the action

---

## Ports

| Service | Port | Protocol |
|---------|------|----------|
| mqtt_broker | 1883 | TCP MQTT |
| mqtt_broker | 9001 | WebSocket MQTT |
| llm_agent | 8081 | HTTP (POST /review) |
| dashboard | 8080 | HTTP (nginx static) |
