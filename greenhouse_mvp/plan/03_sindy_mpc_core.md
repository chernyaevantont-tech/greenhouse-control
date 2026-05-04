# Plan 03: SINDy + MPC Control Core

## Overview

The control core has two responsibilities:

1. **`sindy_pipeline/`**: Build and maintain a *Physics-Informed SINDy* surrogate
   model of the greenhouse dynamics from observed data.
2. **`mpc_controller.py`**: Embed the SINDy surrogate into a `do_mpc` discrete-time
   MPC and solve the optimal control problem at each step.

---

## 1. Physics Features (`sindy_pipeline/physics_features.py`)

### 1.1 Raw inputs

```
states       = [t_in, co2, rh]                          shape (N, 3)
weather      = [T_out, rad, co2_out]                    shape (N, 3)
time_enc     = [sin_h, cos_h]                           shape (N, 2)
actions_raw  = [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]  shape (N, 6)
```

### 1.2 Non-linear physics terms

These are computed from raw values **before** any StandardScaler is applied.
They encode physical laws that a purely linear library cannot capture.

| Symbol | Formula | Physical meaning |
|---|---|---|
| `psat` | $0.6108 \cdot e^{17.27 \cdot t_{in} / (t_{in} + 237.3)}$ | Saturation vapour pressure [kPa] |
| `vpd` | $(1 - rh/100) \cdot psat$ | Vapour Pressure Deficit [kPa] |
| `S_eff` | $rad \cdot (1 - uThScr)$ | Effective solar gain through screen [W/m²] |
| `t_S_eff` | $t_{in} \cdot S\_eff$ | Cross-term: temperature × solar gain |
| `h_uVent` | $rh \cdot uVent$ | Cross-term: humidity drained by ventilation |
| `dc_uVent` | $(co2 - co2_{out}) \cdot uVent$ | Cross-term: CO₂ gradient × ventilation loss |
| `t_uBoil` | $t_{in} \cdot uBoil$ | Cross-term: temperature response to boiler |

### 1.3 Feature vector `u` fed to SINDy

The complete *control/disturbance* vector (shape `(N, 18)`) is:

```
u = [T_out, rad, co2_out, sin_h, cos_h,          # 5 external
     uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,  # 6 actuators
     psat, vpd, S_eff,                            # 3 physics nonlinear
     t_S_eff, h_uVent, dc_uVent, t_uBoil]         # 4 cross-terms
```

### 1.4 Multicollinearity avoidance rules

- **Do NOT** include `dT = T_out - t_in` as a separate feature. Both `T_out` and
  `t_in` are already present; after StandardScaler this becomes an exact linear
  combination → perfect collinearity.
- **Do NOT** include `dc_ext = co2 - co2_out` as a standalone feature for the same
  reason. It appears only *inside* the cross-term `dc_uVent`.
- Check condition number of the full scaled feature matrix: if $\kappa > 1000$,
  log a warning. If $\kappa > 10000$, refuse to fit and raise `ValueError`.

### 1.5 Public API

```python
def compute_physics_features(
    states_arr: np.ndarray,       # (N, 3)
    weather_arr: np.ndarray,      # (N, 3)
    time_enc_arr: np.ndarray,     # (N, 2)
    actions_raw_arr: np.ndarray,  # (N, 6)
) -> np.ndarray:                  # (N, 18)
    """Pure-NumPy computation of the full physics feature vector."""
```

```python
FEATURE_NAMES: list[str] = [
    "t_in", "co2", "rh",
    "T_out", "rad", "co2_out", "sin_h", "cos_h",
    "uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr",
    "psat", "vpd", "S_eff",
    "t_S_eff", "h_uVent", "dc_uVent", "t_uBoil",
]
```

---

## 2. SINDy Fitter (`sindy_pipeline/sindy_fitter.py`)

### 2.1 Discrete-time formulation

SINDy is used in **discrete-time next-step** mode:

$$
\mathbf{x}_{k+1} = \boldsymbol{\Xi}^\top \boldsymbol{\Theta}(\mathbf{x}_k, \mathbf{u}_k)
$$

where $\boldsymbol{\Theta}$ is `PolynomialLibrary(degree=1, include_bias=True)`:

$$
\boldsymbol{\Theta} = [1,\; t_{in},\; co2,\; rh,\; u_1,\; \ldots,\; u_{18}]
\quad \Rightarrow \quad 22 \text{ terms}
$$

The coefficient matrix $\boldsymbol{\Xi}$ has shape `(3 equations, 22 terms)`.

### 2.2 Fitting procedure

```python
class SINDyFitter:
    DEFAULT_THR   = 0.05
    DEFAULT_ALPHA = 0.01

    def fit(
        self,
        states: np.ndarray,        # (N, 3) raw
        actions_phys: np.ndarray,  # (N, 18) raw physics features
        period: float = 900.0,
    ) -> tuple[ps.SINDy, StandardScaler, StandardScaler]:
```

Steps inside `fit()`:

1. **Scale** `states` and `actions_phys` separately with `StandardScaler`.
2. **Shift** to build `(x_in, u_in, x_out)` pairs:
   - `x_in  = scaled_states[:-1]`
   - `u_in  = scaled_actions[:-1]`
   - `x_out = scaled_states[1:]`
3. **Condition check**: compute SVD of `hstack([x_in, u_in])`, assert $\kappa < 1000$.
4. **Fit**:
   ```python
   model = ps.SINDy(
       optimizer=ps.STLSQ(threshold=THR, alpha=ALPHA, max_iter=200,
                          normalize_columns=False),
       feature_library=ps.PolynomialLibrary(degree=1, include_bias=True),
   )
   model.fit(x_in, u=u_in, x_dot=x_out, t=period,
             feature_names=FEATURE_NAMES)
   ```
5. **Return** `(model, scaler_states, scaler_actions)`.

### 2.3 Persistence

```python
def save(path: str, model, scaler_x, scaler_u) -> None:
    """Pickle the three objects together as a dict."""

def load(path: str) -> tuple[ps.SINDy, StandardScaler, StandardScaler]:
    """Load from pickle."""
```

---

## 3. MPC Controller (`control_core/mpc_controller.py`)

### 3.1 Building the `do_mpc` model

The `do_mpc.model.Model('discrete')` is built symbolically in CasADi. The SINDy
equations are embedded as a matrix multiplication.

#### Variable declarations

```
_x:   t_in, co2, rh                                           (3 states)
_u:   uBoil, uCO2, uThScr, uVent, uLamp, uBlScr              (6 controls)
_tvp: T_out, rad, co2_out, sin_h, cos_h                       (5 time-varying params)
```

#### Symbolic physics features (CasADi)

```python
psat  = 0.6108 * ca.exp(17.27 * t_in / (t_in + 237.3))
vpd   = (1.0 - rh / 100.0) * psat
S_eff = rad * (1.0 - uThScr)

u_raw = ca.vertcat(
    T_out, rad, co2_out, sin_h, cos_h,
    uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
    psat, vpd, S_eff,
    t_in * S_eff,
    rh * uVent,
    (co2 - co2_out) * uVent,
    t_in * uBoil,
)  # shape (18,)
```

#### Normalisation (embedded in model)

```python
x_scaled = (ca.vertcat(t_in, co2, rh) - mu_x) / sigma_x
u_scaled = (u_raw - mu_u) / sigma_u
```

`mu_x, sigma_x, mu_u, sigma_u` are extracted from `scaler_x.mean_`,
`scaler_x.scale_`, etc. and stored as `ca.DM` constants.

#### SINDy prediction

```python
coefs = ca.DM(sindy_model.coefficients())  # shape (3, 22)
theta = ca.vertcat(1, x_scaled, u_scaled)  # shape (22,) — bias first
x_next_scaled = coefs @ theta              # shape (3,)
x_next_raw = x_next_scaled * sigma_x + mu_x
```

```python
model.set_rhs('t_in', x_next_raw[0])
model.set_rhs('co2',  x_next_raw[1])
model.set_rhs('rh',   x_next_raw[2])
model.setup()
```

### 3.2 Cost function design

#### Normalised errors (equal-weight scaling)

```
err_T   = (t_in - 20.0) / 5.0          # 1 unit = 5°C deviation
err_co2 = (co2 - 800.0) / 200.0        # 1 unit = 200 ppm deviation
err_rh  = ca.fmax(0, rh - 85.0) / 5.0 # penalise excess humidity only
```

#### Stage cost (Lagrange term)

```
lterm = 100 * err_T**2
      +  30 * err_co2**2
      +  50 * err_rh**2
      +  20 * uBoil          # linear energy cost (gas)
      +  10 * uLamp          # linear energy cost (electricity)
      +   2 * uCO2
```

#### Terminal cost (Mayer term)

```
mterm = 100 * err_T**2 + 30 * err_co2**2 + 50 * err_rh**2
```

#### Anti-chattering (R term)

```python
mpc.set_rterm(
    uBoil=10.0,    # smooth heating ramp
    uCO2=5.0,
    uThScr=100.0,  # screens are slow mechanical devices
    uVent=50.0,    # ventilation causes strong temperature disturbance
    uLamp=1.0,
    uBlScr=1.0,
)
```

### 3.3 Constraints

| Variable | Lower | Upper | Rationale |
|---|---|---|---|
| `uBoil … uBlScr` | 0.0 | 1.0 | Actuator physical range |
| `uVent` | 0.0 | 0.4 | Winter frost protection |
| `t_in` (_x) | 12.0 | 35.0 | Hard frost and heat damage limits |

### 3.4 `MPCController` class API

```python
class MPCController:
    def __init__(
        self,
        sindy_model: ps.SINDy,
        scaler_x: StandardScaler,
        scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
        horizon: int = 20,
        period: float = 900.0,
    ): ...

    def initialise(self, x0: np.ndarray) -> None:
        """Set mpc.x0 and call mpc.set_initial_guess()."""

    def step(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, OODMetrics]:
        """
        1. Extract x0 from telemetry.
        2. Call mpc.make_step(x0).
        3. Compute OOD metrics (Mahalanobis distance).
        4. Return (ActionPayload, OODMetrics).
        """

    def update_model(
        self,
        new_sindy: ps.SINDy,
        new_scaler_x: StandardScaler,
        new_scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
    ) -> None:
        """Rebuild the do_mpc controller with a retrained SINDy model (DAgger)."""
```

### 3.5 OOD Detection

Mahalanobis distance uses the training-set covariance:

```python
# At training time (SINDyFitter):
X_train = hstack([x_in, u_in])          # (N, 21)
cov_inv = np.linalg.pinv(np.cov(X_train.T))
mu_train = X_train.mean(axis=0)

# At inference time (MPCController.step):
x_cur = scaler_x.transform([[t_in, co2, rh]])[0]
u_cur = scaler_u.transform([u_phys_vec])[0]
feat  = np.concatenate([x_cur, u_cur])
delta = feat - mu_train
dist  = np.sqrt(delta @ cov_inv @ delta)

in_dist = dist < OOD_THRESHOLD   # default threshold = 3.0 sigma
```

### 3.6 MQTT Integration

`MPCController` subscribes to `greenhouse/telemetry` and publishes:
- `greenhouse/action/proposed` after every `mpc.make_step()`.
- `greenhouse/ood/metrics` alongside the proposed action.

The controller does **not** wait for approval. It simply fires the proposal and
lets the `GraphWorkflow` (LangGraph) decide whether to approve or reject it.
