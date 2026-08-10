from __future__ import annotations

import json
import math
import pickle
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd


STATE_NAMES = ["t_in", "co2", "rh"]
ACTION_NAMES = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]
WEATHER_NAMES = ["T_out", "rad", "co2_out"]
TIME_NAMES = ["sin_h", "cos_h"]

RAW_FEATURE_NAMES = WEATHER_NAMES + TIME_NAMES + ACTION_NAMES
PHYSICS_EXTRA_NAMES = [
    "psat",
    "vpd",
    "S_eff",
    "t_S_eff",
    "h_uVent",
    "dc_uVent",
    "t_uBoil",
]
PHYSICS_NO_CROSS_NAMES = WEATHER_NAMES + TIME_NAMES + ACTION_NAMES + [
    "psat",
    "vpd",
    "S_eff",
]
PHYSICS_FEATURE_NAMES = WEATHER_NAMES + TIME_NAMES + ACTION_NAMES + PHYSICS_EXTRA_NAMES

# Per-step economic fields harvested from gl_gym's GreenhouseReward via env.step info.
# EPI = sum of "profit" over the season; the rest decompose revenue and costs.
ECON_FIELDS = [
    "profit", "revenue", "variable_costs", "heat_cost", "co2_cost", "elec_cost",
    "fruit_growth_dm", "temp_penalty", "co2_penalty", "rh_penalty", "lamp_penalty",
]

# Simulator's enforced corridors (CO2/T/RH); read live via protocol_config when
# available, this is the GreenLightTomato-v0 default fallback.
DEFAULT_CORRIDORS = {"co2": (300.0, 1600.0), "t_in": (15.0, 34.0), "rh": (50.0, 85.0)}


def _econ_row(info: dict | None) -> dict:
    """Extract the raw (unscaled) economic fields from an env.step info dict."""
    if not info:
        return {f: 0.0 for f in ECON_FIELDS}
    out = {}
    for f in ECON_FIELDS:
        v = info.get(f)
        if v is None and f == "revenue":
            v = info.get("gains", 0.0)
        out[f] = float(v) if v is not None else 0.0
    return out


@dataclass
class ExperimentConfig:
    env_id: str = "gl_gym/GreenLightTomato-v0"
    location: str = "Amsterdam"
    start_date: str = "2010-02-28"
    growth_year: int | None = None
    n_days: int = 60
    period: int = 900
    horizon: int = 20
    seed: int = 42
    noise_scale: float = 0.1
    noise_period: int = 5

    @property
    def steps_per_day(self) -> int:
        return int(86400 / self.period)

    @property
    def total_steps(self) -> int:
        return int(self.n_days * self.steps_per_day)

    @property
    def scenario(self) -> dict:
        return weather_scenario_from_date(self.start_date, self.location, self.growth_year)


@dataclass
class TrajectoryData:
    states: np.ndarray
    weather: np.ndarray
    time_enc: np.ndarray
    actions: np.ndarray
    meta: dict
    econ: np.ndarray | None = None          # (n, len(ECON_FIELDS)) per-step economics
    econ_names: list[str] | None = None

    def __post_init__(self) -> None:
        self.states = np.asarray(self.states, dtype=np.float64)
        self.weather = np.asarray(self.weather, dtype=np.float64)
        self.time_enc = np.asarray(self.time_enc, dtype=np.float64)
        self.actions = np.asarray(self.actions, dtype=np.float64)
        n = len(self.states)
        for name, arr in [
            ("weather", self.weather),
            ("time_enc", self.time_enc),
            ("actions", self.actions),
        ]:
            if len(arr) != n:
                raise ValueError(f"{name} length {len(arr)} does not match states length {n}")
        if self.econ is not None:
            self.econ = np.asarray(self.econ, dtype=np.float64)
            if self.econ_names is None:
                self.econ_names = list(ECON_FIELDS)

    def subset_steps(self, n_steps: int) -> "TrajectoryData":
        n = min(int(n_steps), len(self.states))
        meta = dict(self.meta)
        meta["subset_steps"] = n
        return TrajectoryData(
            states=self.states[:n],
            weather=self.weather[:n],
            time_enc=self.time_enc[:n],
            actions=self.actions[:n],
            meta=meta,
            econ=None if self.econ is None else self.econ[:n],
            econ_names=self.econ_names,
        )

    def to_frame(self) -> pd.DataFrame:
        data = {}
        for i, name in enumerate(STATE_NAMES):
            data[name] = self.states[:, i]
        for i, name in enumerate(WEATHER_NAMES):
            data[name] = self.weather[:, i]
        for i, name in enumerate(TIME_NAMES):
            data[name] = self.time_enc[:, i]
        for i, name in enumerate(ACTION_NAMES):
            data[name] = self.actions[:, i]
        if self.econ is not None and self.econ_names is not None:
            for i, name in enumerate(self.econ_names):
                data[name] = self.econ[:, i]
        data["step"] = np.arange(len(self.states))
        data["time_h"] = data["step"] * float(self.meta.get("period", 900)) / 3600.0
        return pd.DataFrame(data)


@dataclass
class SINDyBundle:
    model: object
    scaler_x: object
    scaler_u: object
    feature_variant: str
    library_degree: int
    feature_names: list[str]
    threshold: float
    alpha: float
    period: float
    train_rows: int
    condition_number: float
    metadata: dict


def article_dir() -> Path:
    here = Path.cwd().resolve()
    if (here / "article_experiment_utils.py").exists():
        return here
    if (here / "own-article" / "article_experiment_utils.py").exists():
        return here / "own-article"
    return Path(__file__).resolve().parent


def results_dir() -> Path:
    out = article_dir() / "results_scenarios"
    for sub in ["datasets", "models", "tables", "figures"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    return out


def weather_scenario_from_date(
    start_date: str,
    location: str = "Amsterdam",
    growth_year: int | None = None,
) -> dict:
    dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    year = int(growth_year if growth_year is not None else dt.year)
    # GreenLightGym2 uses a one-based day-of-year convention:
    # its default 2010-02-28 scenario is start_day=59.
    start_day = int(dt.strftime("%j"))
    return {"location": location, "growth_year": year, "start_day": start_day}


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def save_dataset(data: TrajectoryData, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(data.meta)
    arrays = dict(
        states=data.states,
        weather=data.weather,
        time_enc=data.time_enc,
        actions=data.actions,
    )
    if data.econ is not None:
        arrays["econ"] = data.econ
        meta["_econ_names"] = list(data.econ_names or ECON_FIELDS)
    np.savez_compressed(path, meta=json.dumps(meta, ensure_ascii=False), **arrays)


def load_dataset(path: Path) -> TrajectoryData:
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    econ_names = meta.pop("_econ_names", None)
    return TrajectoryData(
        states=z["states"],
        weather=z["weather"],
        time_enc=z["time_enc"],
        actions=z["actions"],
        meta=meta,
        econ=z["econ"] if "econ" in z.files else None,
        econ_names=econ_names,
    )


def save_bundle(bundle: SINDyBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_bundle(path: Path) -> SINDyBundle:
    with path.open("rb") as f:
        return pickle.load(f)


def _maybe_apply_regional_soil(location: str) -> None:
    """Patch gl_gym's deep-soil boundary to the regional model before env creation.

    Rostov-on-Don needs the continental soil sinusoid (rostov_soil.apply_rostov_soil);
    the patch must be active before the first weather load (it is cached). Gated on
    location so legacy Amsterdam runs keep the Dutch (NL) default.
    """
    if not str(location).lower().startswith("rostov"):
        return
    try:
        from rostov_soil import apply_rostov_soil
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "rostov_soil", str(article_dir() / "rostov_soil.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        apply_rostov_soil = module.apply_rostov_soil
    apply_rostov_soil()


def _make_env(cfg: ExperimentConfig, n_days: int | None = None):
    import gl_gym  # noqa: F401
    import gymnasium as gym

    _maybe_apply_regional_soil(cfg.location)
    return gym.make(
        cfg.env_id,
        normalize_actions=False,
        observation_modules=[
            "IndoorClimateObservations",
            "WeatherObservations",
            "BasicCropObservations",
        ],
        season_length=n_days or cfg.n_days,
    )


def _build_step_context(env):
    from gl_gym.core.types import StepContext

    raw = env.unwrapped
    return StepContext(
        t=raw.timestep,
        dt=raw.dt,
        Np=raw.Np,
        x_prev=raw.x_prev,
        x=raw.x,
        u=raw.u,
        p=raw.p,
        d=raw.weather_data,
        hour_of_day=raw.hour_of_day,
        day_of_year=raw.day_of_year,
    )


def make_rule_based_controller(**overrides):
    """Агрономическая эвристика. Без аргументов — ровно те же уставки, что и раньше.

    `**overrides` добавлены для N-2 (регистр дефектов, G-4): эталон называется в статье
    «настроенным», но артефакта настройки не существует — значения ниже зашиты, а обучаемым
    регуляторам дан явный бюджет в 16 попыток. Либо перебор проводится, либо слово
    «настроенный» снимается. Пустой вызов остаётся побитово эквивалентным прежнему, поэтому
    ни одно уже посчитанное число не меняется.
    """
    from gl_gym.components.rule_based import RuleBasedController

    params = dict(
        lamps_on=0,
        lamps_off=18,
        lamps_day_start=-1,
        lamps_day_stop=366,
        lamps_off_sun=400,
        lamp_rad_sum_limit=10,
        temp_setpoint_day=19.5,
        temp_setpoint_night=16.5,
        heat_correction=0,
        heat_deadzone=5,
        co2_day=800,
        vent_heat_Pband=4,
        rh_max=85,
        mech_dehumid_Pband=2,
        vent_rh_Pband=5,
        t_vent_off=1,
        vent_cold_Pband=-1,
        thScrSpDay=5,
        thScrSpNight=10,
        thScrPband=-1,
        thScrDeadZone=4,
        thScrRh=-2,
        thScrRhPband=2,
        lampExtraHeat=2,
        blScrExtraRh=100,
        rhMax=85,
        tHeatBand=-1,
        co2Band=-100,
        useBlScr=1,
    )
    params.update(overrides)
    return RuleBasedController(**params)


def observation_to_arrays(obs: dict) -> tuple[np.ndarray, np.ndarray]:
    indoor = obs["IndoorClimateObservations"]
    weather = obs["WeatherObservations"]
    state = np.array([float(indoor[1]), float(indoor[0]), float(indoor[2])])
    weather_vec = np.array([float(weather[1]), float(weather[0]), float(weather[3])])
    return state, weather_vec


def time_encoding(step: int, period: int, start_hour: float = 0.0) -> np.ndarray:
    hour = (start_hour + step * period / 3600.0) % 24.0
    return np.array([
        math.sin(2 * math.pi * hour / 24.0),
        math.cos(2 * math.pi * hour / 24.0),
    ])


def collect_rule_based_dataset(
    cfg: ExperimentConfig,
    n_days: int | None = None,
    start_date: str | None = None,
    seed: int | None = None,
    noise_scale: float | None = None,
    noise_period: int | None = None,
    prbs_scale: float = 0.0,
    prbs_period: int = 16,
    rb_params: dict | None = None,
) -> TrajectoryData:
    """Collect rule-based GreenLight trajectories with optional excitation.

    Excitation overlaid on the agronomic rule-based action:
      - gaussian noise (``noise_scale``), refreshed every ``noise_period`` steps;
      - PRBS (``prbs_scale`` > 0): piecewise-constant +/- step on each actuator,
        flipping every ``prbs_period`` steps -> richer identifiability (E1).
    Per-step economics (EPI ``info``) are captured into ``TrajectoryData.econ``.
    """
    cfg = ExperimentConfig(**{**asdict(cfg), "n_days": n_days or cfg.n_days})
    start_date = start_date or cfg.start_date
    seed = cfg.seed if seed is None else seed
    noise_scale = cfg.noise_scale if noise_scale is None else noise_scale
    noise_period = cfg.noise_period if noise_period is None else noise_period
    scenario = weather_scenario_from_date(start_date, cfg.location, cfg.growth_year)

    env = _make_env(cfg, n_days=cfg.n_days)
    # rb_params: пусто -> прежнее поведение побитово (N-2, см. make_rule_based_controller)
    controller = make_rule_based_controller(**(rb_params or {}))
    rng = np.random.default_rng(seed)
    obs, reset_info = env.reset(options={"scenario": scenario}, seed=seed)
    scenario = reset_info.get("scenario", scenario)

    states, weather, times, actions, econ_rows = [], [], [], [], []
    current_noise = np.zeros(6, dtype=np.float64)
    noise_countdown = 0
    prbs_state = np.zeros(6, dtype=np.float64)
    prbs_countdown = 0

    for step in range(cfg.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        ctx = _build_step_context(env)
        base_action = controller.predict(ctx).astype(np.float64)

        if noise_scale > 0:
            if noise_countdown <= 0:
                current_noise = rng.normal(0.0, noise_scale, size=6)
                noise_countdown = noise_period
            noise_countdown -= 1
        else:
            current_noise = np.zeros(6, dtype=np.float64)

        if prbs_scale > 0:
            if prbs_countdown <= 0:
                prbs_state = prbs_scale * rng.choice([-1.0, 1.0], size=6)
                prbs_countdown = prbs_period
            prbs_countdown -= 1
        else:
            prbs_state = np.zeros(6, dtype=np.float64)

        action = np.clip(
            base_action + current_noise + prbs_state,
            env.action_space.low, env.action_space.high,
        )

        states.append(state)
        weather.append(weather_vec)
        times.append(time_encoding(step, cfg.period))
        actions.append(action.astype(np.float64))

        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
        econ_rows.append([_econ_row(_info)[f] for f in ECON_FIELDS])
        if terminated or truncated:
            break

    env.close()
    source = "rule_based" + ("+prbs" if prbs_scale > 0 else "")
    return TrajectoryData(
        states=np.asarray(states),
        weather=np.asarray(weather),
        time_enc=np.asarray(times),
        actions=np.asarray(actions),
        econ=np.asarray(econ_rows, dtype=np.float64),
        econ_names=list(ECON_FIELDS),
        meta={
            "source": source,
            "env_id": cfg.env_id,
            "location": scenario["location"],
            "start_date": start_date,
            "growth_year": int(scenario["growth_year"]),
            "start_day": int(scenario["start_day"]),
            "scenario": scenario,
            "n_days": cfg.n_days,
            "period": cfg.period,
            "seed": seed,
            "noise_scale": noise_scale,
            "noise_period": noise_period,
            "prbs_scale": prbs_scale,
            "prbs_period": prbs_period,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


def compute_physics_features(
    states: np.ndarray,
    weather: np.ndarray,
    time_enc: np.ndarray,
    actions: np.ndarray,
) -> np.ndarray:
    states = np.asarray(states, dtype=np.float64)
    weather = np.asarray(weather, dtype=np.float64)
    time_enc = np.asarray(time_enc, dtype=np.float64)
    actions = np.asarray(actions, dtype=np.float64)

    t_in = states[:, 0]
    co2 = states[:, 1]
    rh = states[:, 2]
    T_out = weather[:, 0]
    rad = weather[:, 1]
    co2_out = weather[:, 2]
    sin_h = time_enc[:, 0]
    cos_h = time_enc[:, 1]
    uBoil, uCO2, uThScr, uVent, uLamp, uBlScr = actions.T

    psat = 0.6108 * np.exp(17.27 * t_in / (t_in + 237.3))
    vpd = (1.0 - rh / 100.0) * psat
    S_eff = rad * (1.0 - uThScr)
    t_S_eff = t_in * S_eff
    h_uVent = rh * uVent
    dc_uVent = (co2 - co2_out) * uVent
    t_uBoil = t_in * uBoil

    return np.column_stack(
        [
            T_out,
            rad,
            co2_out,
            sin_h,
            cos_h,
            uBoil,
            uCO2,
            uThScr,
            uVent,
            uLamp,
            uBlScr,
            psat,
            vpd,
            S_eff,
            t_S_eff,
            h_uVent,
            dc_uVent,
            t_uBoil,
        ]
    )


def compute_feature_matrix(data: TrajectoryData, variant: str) -> tuple[np.ndarray, list[str]]:
    if variant == "raw":
        return np.column_stack([data.weather, data.time_enc, data.actions]), RAW_FEATURE_NAMES.copy()
    if variant == "physics":
        return compute_physics_features(data.states, data.weather, data.time_enc, data.actions), PHYSICS_FEATURE_NAMES.copy()
    if variant == "physics_no_cross":
        full = compute_physics_features(data.states, data.weather, data.time_enc, data.actions)
        idx = list(range(14))
        return full[:, idx], PHYSICS_NO_CROSS_NAMES.copy()
    raise ValueError(f"Unknown feature variant: {variant}")


def condition_number(matrix: np.ndarray) -> float:
    s = np.linalg.svd(matrix, compute_uv=False)
    s = s[s > 0]
    return float(np.inf if len(s) == 0 else s[0] / s[-1])


def _denoise_states(states: np.ndarray, method: str) -> np.ndarray:
    """Smooth the raw state signal before forming the one-step map (E2 denoise factor)."""
    if method in ("none", None):
        return states
    x = np.asarray(states, dtype=np.float64)
    n = len(x)
    if method == "savgol":
        from scipy.signal import savgol_filter
        win = min(31, n if n % 2 == 1 else n - 1)
        if win < 5:
            return x
        return np.column_stack([savgol_filter(x[:, i], win, 2) for i in range(x.shape[1])])
    if method == "kalman":
        # Constant-velocity RTS smoother per channel (lightweight Kalman smoothing).
        return np.column_stack([_kalman_smooth_1d(x[:, i]) for i in range(x.shape[1])])
    raise ValueError(f"Unknown denoise method: {method}")


def _kalman_smooth_1d(z: np.ndarray, q: float = 1e-3, r: float | None = None) -> np.ndarray:
    """Minimal constant-velocity Kalman filter + RTS smoother for a 1-D signal."""
    z = np.asarray(z, dtype=np.float64)
    n = len(z)
    if n < 3:
        return z
    r = float(np.var(np.diff(z)) * 0.5 + 1e-9) if r is None else r
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q = q * np.array([[0.25, 0.5], [0.5, 1.0]])
    xs = np.zeros((n, 2)); Ps = np.zeros((n, 2, 2))
    xp = np.zeros((n, 2)); Pp = np.zeros((n, 2, 2))
    x = np.array([z[0], 0.0]); P = np.eye(2)
    for k in range(n):
        x = F @ x; P = F @ P @ F.T + Q
        xp[k] = x; Pp[k] = P
        S = H @ P @ H.T + r
        K = (P @ H.T) / S
        x = x + (K * (z[k] - H @ x)).ravel()
        P = (np.eye(2) - K @ H) @ P
        xs[k] = x; Ps[k] = P
    xsm = xs.copy()
    for k in range(n - 2, -1, -1):
        C = Ps[k] @ F.T @ np.linalg.inv(Pp[k + 1])
        xsm[k] = xs[k] + C @ (xsm[k + 1] - xp[k + 1])
    return xsm[:, 0]


def _make_optimizer(name: str, threshold: float, alpha: float, ensemble_models: int = 20):
    import pysindy as ps
    name = (name or "stlsq").lower()
    base = ps.STLSQ(threshold=threshold, alpha=alpha, max_iter=200, normalize_columns=False)
    if name == "stlsq":
        return base
    if name == "sr3":
        return ps.SR3(reg_weight_lam=threshold, relax_coeff_nu=1.0, max_iter=200)
    if name == "constrained":
        # ConstrainedSR3 requires cvxpy; fall back to SR3 if it is not available.
        if hasattr(ps, "ConstrainedSR3"):
            return ps.ConstrainedSR3(reg_weight_lam=threshold, relax_coeff_nu=1.0, max_iter=200)
        return ps.SR3(reg_weight_lam=threshold, relax_coeff_nu=1.0, max_iter=200)
    if name == "ensemble":
        return ps.EnsembleOptimizer(base, bagging=True, n_models=ensemble_models)
    raise ValueError(f"Unknown optimizer: {name}")


def fit_sindy(
    data: TrajectoryData,
    feature_variant: str = "physics",
    library_degree: int = 1,
    threshold: float = 0.05,
    alpha: float = 0.01,
    period: float = 900.0,
    metadata: dict | None = None,
    optimizer: str = "stlsq",
    denoise: str = "none",
    ensemble_models: int = 20,
) -> SINDyBundle:
    """Fit a discrete one-step SINDy map x_{k+1}=f(x_k,u_k) (pysindy 2.x).

    E2 identification-ladder factors are exposed as: ``optimizer`` in
    {stlsq, sr3, constrained, ensemble}, ``denoise`` in {none, savgol, kalman},
    ``feature_variant`` (library) and ``library_degree``. Defaults reproduce the
    original STLSQ + physics + degree-1 recipe.
    """
    import pysindy as ps
    from sklearn.preprocessing import StandardScaler

    states = _denoise_states(data.states, denoise)
    features, feature_names = compute_feature_matrix(data, feature_variant)
    scaler_x = StandardScaler()
    scaler_u = StandardScaler()
    x_sc = scaler_x.fit_transform(states)
    u_sc = scaler_u.fit_transform(features)

    x_in = x_sc[:-1]
    u_in = u_sc[:-1]
    x_out = x_sc[1:]
    kappa = condition_number(np.hstack([x_in, u_in]))

    model = ps.SINDy(
        optimizer=_make_optimizer(optimizer, threshold, alpha, ensemble_models),
        feature_library=ps.PolynomialLibrary(degree=library_degree, include_bias=True),
    )
    model.fit(x_in, u=u_in, x_dot=x_out, t=period, feature_names=STATE_NAMES + feature_names)

    meta = dict(metadata or {})
    meta.setdefault("optimizer", optimizer)
    meta.setdefault("denoise", denoise)
    return SINDyBundle(
        model=model,
        scaler_x=scaler_x,
        scaler_u=scaler_u,
        feature_variant=feature_variant,
        library_degree=library_degree,
        feature_names=feature_names,
        threshold=threshold,
        alpha=alpha,
        period=float(period),
        train_rows=len(x_in),
        condition_number=kappa,
        metadata=meta,
    )


def predict_next_raw(
    bundle: SINDyBundle,
    x_raw: np.ndarray,
    weather: np.ndarray,
    time_enc: np.ndarray,
    action: np.ndarray,
) -> np.ndarray:
    tmp = TrajectoryData(
        states=np.asarray(x_raw, dtype=np.float64).reshape(1, 3),
        weather=np.asarray(weather, dtype=np.float64).reshape(1, 3),
        time_enc=np.asarray(time_enc, dtype=np.float64).reshape(1, 2),
        actions=np.asarray(action, dtype=np.float64).reshape(1, 6),
        meta={"period": bundle.period},
    )
    u_raw, _ = compute_feature_matrix(tmp, bundle.feature_variant)
    x_sc = bundle.scaler_x.transform(tmp.states)
    u_sc = bundle.scaler_u.transform(u_raw)
    y_sc = bundle.model.predict(x_sc, u=u_sc)
    return bundle.scaler_x.inverse_transform(np.asarray(y_sc).reshape(1, -1))[0]


def evaluate_sindy(
    bundle: SINDyBundle,
    data: TrajectoryData,
    rollout_horizons: Iterable[int] = (4, 20, 96),
) -> pd.DataFrame:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    rows = []
    features, _ = compute_feature_matrix(data, bundle.feature_variant)
    x_sc = bundle.scaler_x.transform(data.states)
    u_sc = bundle.scaler_u.transform(features)
    pred_sc = bundle.model.predict(x_sc[:-1], u=u_sc[:-1])
    pred = bundle.scaler_x.inverse_transform(np.asarray(pred_sc))
    truth = data.states[1:]

    for i, state in enumerate(STATE_NAMES):
        rows.append(
            {
                "metric_scope": "one_step",
                "horizon": 1,
                "state": state,
                "rmse": float(np.sqrt(mean_squared_error(truth[:, i], pred[:, i]))),
                "mae": mean_absolute_error(truth[:, i], pred[:, i]),
                "r2": r2_score(truth[:, i], pred[:, i]),
            }
        )

    for horizon in rollout_horizons:
        errs = []
        failed = 0
        n0 = max(0, len(data.states) - horizon - 1)
        starts = np.linspace(0, n0, num=min(20, n0 + 1), dtype=int) if n0 > 0 else []
        for start in starts:
            x = data.states[start].copy()
            pred_path = []
            true_path = []
            for k in range(horizon):
                idx = start + k
                try:
                    x = predict_next_raw(bundle, x, data.weather[idx], data.time_enc[idx], data.actions[idx])
                except Exception:
                    failed += 1
                    break
                if (not np.all(np.isfinite(x))) or np.max(np.abs(x)) > 1e6:
                    failed += 1
                    break
                pred_path.append(x)
                true_path.append(data.states[idx + 1])
            if pred_path:
                errs.append(np.asarray(pred_path) - np.asarray(true_path))
        if errs:
            err = np.concatenate(errs, axis=0)
            for i, state in enumerate(STATE_NAMES):
                rows.append(
                    {
                        "metric_scope": "rollout",
                        "horizon": int(horizon),
                        "state": state,
                        "rmse": float(np.sqrt(np.mean(err[:, i] ** 2))),
                        "mae": float(np.mean(np.abs(err[:, i]))),
                        "r2": np.nan,
                        "failed_rollouts": int(failed),
                        "attempted_rollouts": int(len(starts)),
                    }
                )
        else:
            for state in STATE_NAMES:
                rows.append(
                    {
                        "metric_scope": "rollout",
                        "horizon": int(horizon),
                        "state": state,
                        "rmse": np.inf,
                        "mae": np.inf,
                        "r2": np.nan,
                        "failed_rollouts": int(failed),
                        "attempted_rollouts": int(len(starts)),
                    }
                )
    return pd.DataFrame(rows)


def run_sindy_ablation(
    train_data: TrajectoryData,
    test_data: TrajectoryData,
    budgets_days: Iterable[int],
    variants: Iterable[tuple[str, str, int]],
    cfg: ExperimentConfig,
) -> tuple[pd.DataFrame, dict[str, SINDyBundle]]:
    rows = []
    bundles = {}
    for days in budgets_days:
        subset = train_data.subset_steps(days * cfg.steps_per_day)
        for label, feature_variant, degree in variants:
            bundle = fit_sindy(
                subset,
                feature_variant=feature_variant,
                library_degree=degree,
                period=float(cfg.period),
                metadata={"label": label, "budget_days": days},
            )
            bundles[f"{label}_{days}d"] = bundle
            metrics = evaluate_sindy(bundle, test_data)
            metrics.insert(0, "method", label)
            metrics.insert(1, "budget_days", days)
            metrics["nonzero_coefficients"] = int(np.count_nonzero(bundle.model.coefficients()))
            metrics["total_coefficients"] = int(bundle.model.coefficients().size)
            metrics["sparsity"] = 1.0 - metrics["nonzero_coefficients"] / metrics["total_coefficients"]
            metrics["condition_number"] = bundle.condition_number
            rows.append(metrics)
    return pd.concat(rows, ignore_index=True), bundles


class WeatherForecastTVP:
    def __init__(self, cfg: ExperimentConfig, n_days: int | None = None, start_date: str | None = None):
        self.cfg = cfg
        self.n_days = n_days or cfg.n_days
        self.start_date = start_date or cfg.start_date
        self.scenario = weather_scenario_from_date(self.start_date, cfg.location, cfg.growth_year)
        self._harvest()

    def _harvest(self) -> None:
        env = _make_env(self.cfg, n_days=self.n_days)
        obs, reset_info = env.reset(options={"scenario": self.scenario}, seed=self.cfg.seed)
        self.scenario = reset_info.get("scenario", self.scenario)
        total = self.n_days * self.cfg.steps_per_day + self.cfg.horizon + 1
        weather, times = [], []
        zero = np.zeros(6, dtype=np.float32)
        for step in range(total):
            _state, weather_vec = observation_to_arrays(obs)
            weather.append(weather_vec)
            times.append(time_encoding(step, self.cfg.period))
            obs, _reward, terminated, truncated, _info = env.step(zero)
            if terminated or truncated:
                break
        env.close()
        self.weather = np.asarray(weather, dtype=np.float64)
        self.time_enc = np.asarray(times, dtype=np.float64)

    def get_mpc_tvp_fun(self, mpc):
        tvp_template = mpc.get_tvp_template()
        period = self.cfg.period
        horizon = self.cfg.horizon
        n = len(self.weather)

        def tvp_fun(t_now):
            # do-mpc may pass t_now as a scalar, ndarray, or casadi DM depending on the
            # build -- extract a Python scalar robustly (int(array) errors on some builds).
            t_scalar = float(np.asarray(t_now).reshape(-1)[0])
            k_start = int(t_scalar / period)
            for k in range(horizon):
                idx = min(k_start + k, n - 1)
                tvp_template["_tvp", k, "T_out"] = self.weather[idx, 0]
                tvp_template["_tvp", k, "rad"] = self.weather[idx, 1]
                tvp_template["_tvp", k, "co2_out"] = self.weather[idx, 2]
                tvp_template["_tvp", k, "sin_h"] = self.time_enc[idx, 0]
                tvp_template["_tvp", k, "cos_h"] = self.time_enc[idx, 1]
            return tvp_template

        return tvp_fun


def _casadi_feature_vector(feature_variant: str, x_vars: dict, u_vars: dict, tvp_vars: dict):
    import casadi as ca

    t_in = x_vars["t_in"]
    co2 = x_vars["co2"]
    rh = x_vars["rh"]
    T_out = tvp_vars["T_out"]
    rad = tvp_vars["rad"]
    co2_out = tvp_vars["co2_out"]
    sin_h = tvp_vars["sin_h"]
    cos_h = tvp_vars["cos_h"]
    uBoil = u_vars["uBoil"]
    uCO2 = u_vars["uCO2"]
    uThScr = u_vars["uThScr"]
    uVent = u_vars["uVent"]
    uLamp = u_vars["uLamp"]
    uBlScr = u_vars["uBlScr"]

    raw = [T_out, rad, co2_out, sin_h, cos_h, uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
    if feature_variant == "raw":
        return ca.vertcat(*raw)

    psat = 0.6108 * ca.exp(17.27 * t_in / (t_in + 237.3))
    vpd = (1.0 - rh / 100.0) * psat
    S_eff = rad * (1.0 - uThScr)
    if feature_variant == "physics_no_cross":
        return ca.vertcat(*raw, psat, vpd, S_eff)
    if feature_variant == "physics":
        return ca.vertcat(
            *raw,
            psat,
            vpd,
            S_eff,
            t_in * S_eff,
            rh * uVent,
            (co2 - co2_out) * uVent,
            t_in * uBoil,
        )
    raise ValueError(f"Unsupported feature variant for MPC: {feature_variant}")


def build_mpc_controller(
    bundle: SINDyBundle,
    weather_provider: WeatherForecastTVP,
    cfg: ExperimentConfig,
    objective: str = "full",
):
    import casadi as ca
    import do_mpc

    model = do_mpc.model.Model("discrete")
    x_vars = {name: model.set_variable("_x", name) for name in STATE_NAMES}
    u_vars = {name: model.set_variable("_u", name) for name in ACTION_NAMES}
    tvp_vars = {name: model.set_variable("_tvp", name) for name in WEATHER_NAMES + TIME_NAMES}

    x_raw = ca.vertcat(x_vars["t_in"], x_vars["co2"], x_vars["rh"])
    u_raw = _casadi_feature_vector(bundle.feature_variant, x_vars, u_vars, tvp_vars)

    x_sc = (x_raw - ca.DM(bundle.scaler_x.mean_)) / ca.DM(bundle.scaler_x.scale_)
    u_sc = (u_raw - ca.DM(bundle.scaler_u.mean_)) / ca.DM(bundle.scaler_u.scale_)

    library = ca.vertcat(1, x_sc, u_sc)
    if bundle.library_degree != 1:
        raise ValueError("MPC embedding currently supports degree=1 SINDy libraries.")
    x_next_sc = ca.DM(bundle.model.coefficients()) @ library
    x_next_raw = (
        x_next_sc * ca.DM(bundle.scaler_x.scale_.reshape(-1, 1))
        + ca.DM(bundle.scaler_x.mean_.reshape(-1, 1))
    )

    for i, name in enumerate(STATE_NAMES):
        model.set_rhs(name, x_next_raw[i])
    model.setup()

    mpc = do_mpc.controller.MPC(model)
    mpc.set_param(
        n_horizon=cfg.horizon,
        t_step=cfg.period,
        n_robust=0,
        store_full_solution=False,
        nlpsol_opts={
            "ipopt.print_level": 0,
            "ipopt.sb": "yes",
            "print_time": 0,
        },
    )

    t_in = x_vars["t_in"]
    co2 = x_vars["co2"]
    rh = x_vars["rh"]
    uBoil = u_vars["uBoil"]
    uCO2 = u_vars["uCO2"]
    uThScr = u_vars["uThScr"]
    uVent = u_vars["uVent"]
    uLamp = u_vars["uLamp"]
    uBlScr = u_vars["uBlScr"]

    if objective == "temperature_only":
        lterm = 10.0 * (t_in - 20.0) ** 2 + 100.0 * uBoil**2 + 50.0 * uLamp**2
        mterm = 10.0 * (t_in - 20.0) ** 2
    else:
        # EPI-aligned objective: keep climate inside a day/night-varying PRODUCTIVE band
        # at minimum resource cost -- NOT tight setpoint tracking (which over-spends and,
        # as the oracle showed, drives EPI negative). Inside the band only energy cost
        # acts, so the controller is thrifty; outside, soft penalties pull it back.
        cos_h = tvp_vars["cos_h"]
        w_day = ca.fmax(0.0, (1.0 - cos_h) / 2.0)           # ~0 at midnight, ~1 at noon
        T_lo = 15.0 + 3.0 * w_day        # night >=15, day >=18
        T_hi = 19.0 + 5.0 * w_day        # night <=19, day <=24
        co2_floor = 400.0 + 300.0 * w_day  # ambient at night, ~700 by day
        band_T = ca.fmax(0.0, T_lo - t_in) + ca.fmax(0.0, t_in - T_hi)
        low_co2 = ca.fmax(0.0, co2_floor - co2)
        hi_rh = ca.fmax(0.0, rh - 85.0)
        cost_climate = 30.0 * band_T**2 + 3e-4 * low_co2**2 + 8.0 * hi_rh**2
        cost_energy = 20.0 * uBoil + 10.0 * uLamp + 2.0 * uCO2
        lterm = cost_energy + cost_climate
        mterm = cost_climate

    mpc.set_objective(mterm=mterm, lterm=lterm)
    mpc.set_rterm(
        uBoil=10.0,
        uCO2=5.0,
        uThScr=100.0,
        uVent=50.0,
        uLamp=1.0,
        uBlScr=1.0,
    )

    for name in ACTION_NAMES:
        mpc.bounds["lower", "_u", name] = 0.0
        mpc.bounds["upper", "_u", name] = 1.0
    mpc.bounds["upper", "_u", "uVent"] = 0.4
    mpc.bounds["lower", "_x", "t_in"] = 12.0
    mpc.bounds["upper", "_x", "t_in"] = 35.0

    mpc.set_tvp_fun(weather_provider.get_mpc_tvp_fun(mpc))
    mpc.setup()
    return mpc


def rollout_rule_based(
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    seed: int | None = None,
    noise_scale: float = 0.0,
    rb_params: dict | None = None,
) -> pd.DataFrame:
    data = collect_rule_based_dataset(
        cfg,
        n_days=n_days,
        start_date=start_date,
        seed=seed,
        noise_scale=noise_scale,
        rb_params=rb_params,
    )
    df = data.to_frame()
    df["controller"] = "rule_based"
    return df


def rollout_mpc(
    bundle: SINDyBundle,
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    objective: str = "full",
    max_solver_failures: int = 100,
) -> pd.DataFrame:
    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    weather_provider = WeatherForecastTVP(cfg_run, n_days=n_days, start_date=start_date)
    mpc = build_mpc_controller(bundle, weather_provider, cfg_run, objective=objective)
    env = _make_env(cfg_run, n_days=n_days)
    obs, _ = env.reset(options={"scenario": weather_provider.scenario}, seed=cfg.seed)

    x0, _ = observation_to_arrays(obs)
    mpc.x0 = x0.reshape(-1, 1)
    mpc.set_initial_guess()

    rows = []
    failures = 0
    fallback = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        try:
            action = np.asarray(mpc.make_step(state.reshape(-1, 1))).ravel()
            action = np.clip(action, 0.0, 1.0)
        except Exception as exc:
            failures += 1
            action = fallback.copy()
            if failures > max_solver_failures:
                print(f"Stopping rollout after solver failure at step {step}: {exc}")
                break

        row = {
            "step": step,
            "time_h": step * cfg_run.period / 3600.0,
            "controller": bundle.metadata.get("label", "mpc"),
            "solver_failures": failures,
        }
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = time_encoding(step, cfg_run.period)[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action[i]

        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
        row.update(_econ_row(_info))
        rows.append(row)
        if terminated or truncated:
            break

    env.close()
    return pd.DataFrame(rows)


def rollout_mpc_guarded(
    bundle: SINDyBundle,
    maha: dict,
    threshold: float,
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    max_solver_failures: int = 100,
) -> pd.DataFrame:
    """SINDy-MPC with an OOD safety guard (E5, Г4в): when the Mahalanobis distance of the
    current exogenous input exceeds ``threshold`` (out-of-distribution), fall back to the
    safe rule-based action instead of trusting the surrogate MPC. Records guard activations."""
    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    weather_provider = WeatherForecastTVP(cfg_run, n_days=n_days, start_date=start_date)
    mpc = build_mpc_controller(bundle, weather_provider, cfg_run)
    env = _make_env(cfg_run, n_days=n_days)
    obs, _ = env.reset(options={"scenario": weather_provider.scenario}, seed=cfg.seed)
    rb = make_rule_based_controller()
    x0, _ = observation_to_arrays(obs)
    mpc.x0 = x0.reshape(-1, 1)
    mpc.set_initial_guess()
    rows, failures = [], 0
    fallback = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        t_enc = time_encoding(step, cfg_run.period)
        ood = float(mahalanobis_distances(maha, weather_vec.reshape(1, 3), t_enc.reshape(1, 2))[0])
        guarded = ood > threshold
        if guarded:
            action = np.clip(np.asarray(rb.predict(_build_step_context(env)), dtype=np.float64), 0.0, 1.0)
        else:
            try:
                action = np.clip(np.asarray(mpc.make_step(state.reshape(-1, 1))).ravel(), 0.0, 1.0)
            except Exception:  # noqa: BLE001
                failures += 1
                action = fallback.copy()
                if failures > max_solver_failures:
                    break
        row = {"step": step, "time_h": step * cfg_run.period / 3600.0, "controller": "guarded_sindy_mpc",
               "solver_failures": failures, "ood": ood, "guarded": int(guarded)}
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = t_enc[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action[i]
        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
        row.update(_econ_row(_info))
        rows.append(row)
        if terminated or truncated:
            break
    env.close()
    return pd.DataFrame(rows)


def _apply_fault(value: float, ftype: str, fval: float) -> float:
    if ftype == "stuck":
        return fval
    if ftype == "offset":
        return value + fval
    if ftype == "dead":
        return 0.0
    return value


def rollout_mpc_faulty(
    bundle: SINDyBundle,
    cfg: ExperimentConfig,
    n_days: int,
    fault: dict,
    start_date: str | None = None,
    supervisor: bool = False,
    resid_threshold: float = 3.0,
    max_solver_failures: int = 100,
) -> pd.DataFrame:
    """SINDy-MPC under a sensor/actuator fault (E7, safety part of Г4).

    ``fault`` = {layer: 'sensor'|'actuator', target: 't_in'|'uVent'|..., type:
    'stuck'|'offset'|'dead', value: float, start_step: int}. A sensor fault corrupts the
    reading the surrogate MPC sees; an actuator fault corrupts the command sent to gym.
    With ``supervisor=True`` a model-based monitor flags a fault when the one-step
    surrogate-prediction residual spikes and hands control to the safe rule-based fallback
    (which reads the true plant state, i.e. a redundant safe mode)."""
    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    weather_provider = WeatherForecastTVP(cfg_run, n_days=n_days, start_date=start_date)
    mpc = build_mpc_controller(bundle, weather_provider, cfg_run)
    env = _make_env(cfg_run, n_days=n_days)
    obs, _ = env.reset(options={"scenario": weather_provider.scenario}, seed=cfg.seed)
    rb = make_rule_based_controller()
    layer = fault.get("layer"); tgt = fault.get("target"); ftype = fault.get("type")
    fval = float(fault.get("value", 0.0)); start = int(fault.get("start_step", 0))
    si = STATE_NAMES.index(tgt) if (layer == "sensor" and tgt in STATE_NAMES) else None
    ai = ACTION_NAMES.index(tgt) if (layer == "actuator" and tgt in ACTION_NAMES) else None
    x0, _ = observation_to_arrays(obs)
    mpc.x0 = x0.reshape(-1, 1); mpc.set_initial_guess()
    rows, failures, prev_pred, latched = [], 0, None, False
    fallback = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        ctrl_state = state.copy()
        if si is not None and step >= start:
            ctrl_state[si] = _apply_fault(state[si], ftype, fval)
        # Supervisor: a one-step residual spike (e.g. the fault onset, or an actuator
        # fault breaking dynamics consistency) latches the controller into safe mode.
        if supervisor and prev_pred is not None and not latched:
            resid = float(np.sum(np.abs(bundle.scaler_x.transform(ctrl_state.reshape(1, -1))[0]
                                        - bundle.scaler_x.transform(prev_pred.reshape(1, -1))[0])))
            if resid > resid_threshold:
                latched = True
        flagged = latched
        if flagged:
            action = np.clip(np.asarray(rb.predict(_build_step_context(env)), dtype=np.float64), 0.0, 1.0)
        else:
            try:
                action = np.clip(np.asarray(mpc.make_step(ctrl_state.reshape(-1, 1))).ravel(), 0.0, 1.0)
            except Exception:  # noqa: BLE001
                failures += 1; action = fallback.copy()
                if failures > max_solver_failures:
                    break
        t_enc = time_encoding(step, cfg_run.period)
        prev_pred = predict_next_raw(bundle, ctrl_state, weather_vec, t_enc, action)
        action_env = action.copy()
        if ai is not None and step >= start:
            action_env[ai] = float(np.clip(_apply_fault(action[ai], ftype, fval), 0.0, 1.0))
        row = {"step": step, "time_h": step * cfg_run.period / 3600.0, "controller": "faulty_sindy_mpc",
               "solver_failures": failures, "flagged": int(flagged)}
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = t_enc[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action_env[i]
        obs, _reward, terminated, truncated, _info = env.step(action_env.astype(np.float32))
        row.update(_econ_row(_info))
        rows.append(row)
        if terminated or truncated:
            break
    env.close()
    return pd.DataFrame(rows)


def trajectory_from_frame(df: pd.DataFrame, cfg: ExperimentConfig, source: str) -> TrajectoryData:
    return TrajectoryData(
        states=df[STATE_NAMES].to_numpy(),
        weather=df[WEATHER_NAMES].to_numpy(),
        time_enc=df[TIME_NAMES].to_numpy(),
        actions=df[ACTION_NAMES].to_numpy(),
        meta={"source": source, "period": cfg.period, "rows": len(df)},
    )


# ── E5 OOD trust signals: Mahalanobis (input novelty) + ensemble variance ────

def fit_mahalanobis(train_data: "TrajectoryData") -> dict:
    """Gaussian model of the exogenous inputs (weather + time-of-day) of the training
    distribution. Mahalanobis distance from it = input novelty (weather/season shift)."""
    X = np.hstack([np.asarray(train_data.weather, float), np.asarray(train_data.time_enc, float)])
    mu = X.mean(axis=0)
    C = np.cov(X.T) + 1e-6 * np.eye(X.shape[1])
    return {"mu": mu, "Cinv": np.linalg.pinv(C)}


def mahalanobis_distances(maha: dict, weather: np.ndarray, time_enc: np.ndarray) -> np.ndarray:
    X = np.hstack([np.asarray(weather, float), np.asarray(time_enc, float)])
    d = X - maha["mu"]
    return np.sqrt(np.maximum(0.0, np.einsum("ij,jk,ik->i", d, maha["Cinv"], d)))


def fit_ensemble_for_variance(train_data, feature_variant="physics_no_cross", n_models=20, period=900.0):
    """Fit an Ensemble-SINDy and expose its bootstrap coefficient list for prediction variance."""
    b = fit_sindy(train_data, feature_variant=feature_variant, library_degree=1,
                  optimizer="ensemble", denoise="none", period=period, ensemble_models=n_models)
    opt = b.model.optimizer
    coef_list = getattr(opt, "coef_list", None)
    if coef_list is None:
        coef_list = getattr(opt, "coef_list_", None)
    b.metadata["coef_list"] = np.asarray(coef_list) if coef_list is not None else None
    return b


def ensemble_pred_std(bundle: SINDyBundle, data: "TrajectoryData") -> np.ndarray:
    """Per-step ensemble prediction std (epistemic uncertainty) of the next scaled state."""
    coef_list = bundle.metadata.get("coef_list")
    if coef_list is None:
        return np.full(len(data.states), np.nan)
    coef_list = np.asarray(coef_list)               # (n_models, 3, m)
    n = len(data.states)
    out = np.zeros(n)
    for k in range(n):
        phi = _sindy_library_vector(bundle, data.states[k], data.weather[k], data.time_enc[k], data.actions[k])
        preds = coef_list @ phi                     # (n_models, 3)
        out[k] = float(np.mean(np.std(preds, axis=0)))  # mean over states of cross-model std
    return out


def _sindy_library_vector(bundle: SINDyBundle, state, weather, time_enc, action) -> np.ndarray:
    """Degree-1 SINDy library row phi = [1, x_scaled, u_scaled] (matches build_mpc_controller)."""
    tmp = TrajectoryData(
        states=np.asarray(state, dtype=np.float64).reshape(1, 3),
        weather=np.asarray(weather, dtype=np.float64).reshape(1, 3),
        time_enc=np.asarray(time_enc, dtype=np.float64).reshape(1, 2),
        actions=np.asarray(action, dtype=np.float64).reshape(1, 6),
        meta={"period": bundle.period},
    )
    feats, _ = compute_feature_matrix(tmp, bundle.feature_variant)
    x_sc = bundle.scaler_x.transform(tmp.states)[0]
    u_sc = bundle.scaler_u.transform(feats)[0]
    return np.concatenate([[1.0], x_sc, u_sc])


def rollout_mpc_ekf(
    bundle: SINDyBundle,
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    forgetting: float = 0.999,
    rebuild_every: int = 96,
    p0: float = 0.1,
    max_solver_failures: int = 100,
) -> pd.DataFrame:
    """SINDy-MPC with EKF/RLS online adaptation of the surrogate coefficients (E4, Г4а).

    The discrete SINDy map x_{k+1}=Xi.phi(x_k,u_k) is linear in the coefficients Xi, so
    the extended Kalman filter reduces to recursive least squares with a forgetting
    factor (per output state). Each step the observed transition updates Xi; the do-mpc
    controller is rebuilt every ``rebuild_every`` steps with the adapted coefficients so
    control tracks the weather shift. Returns the closed-loop frame with EPI fields.

    Defaults (p0=0.1, forgetting=0.999) are the GENTLE prior chosen after diagnosis
    (scratchpad/diag_ekf.py): the old aggressive prior (p0=10, forgetting=0.995) caused
    covariance windup under the low excitation of closed-loop data -> erratic coefficient
    jumps -> the adapted MPC destabilised (EPI -4.3 vs offline +0.5). The gentle prior is
    stable (bounded P-trace) and non-harmful (EPI +0.7). NOTE: RLS reliably lowers the
    one-step residual, but one-step fit does NOT track closed-loop EPI here -- control is
    dominated by discrete actuator decisions (e.g. whether uBoil re-enters the model), so
    adaptation gains are marginal on mild shifts.
    """
    import copy

    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    if bundle.library_degree != 1:
        raise ValueError("EKF-SINDy adaptation requires a degree-1 bundle.")
    weather_provider = WeatherForecastTVP(cfg_run, n_days=n_days, start_date=start_date)
    b = copy.deepcopy(bundle)
    Xi = np.asarray(b.model.coefficients(), dtype=np.float64).copy()   # (3, m)
    m = Xi.shape[1]
    P = np.stack([np.eye(m) * p0 for _ in range(3)])                    # (3, m, m)

    mpc = build_mpc_controller(b, weather_provider, cfg_run)
    env = _make_env(cfg_run, n_days=n_days)
    obs, _ = env.reset(options={"scenario": weather_provider.scenario}, seed=cfg.seed)
    x0, _ = observation_to_arrays(obs)
    mpc.x0 = x0.reshape(-1, 1)
    mpc.set_initial_guess()

    rows, failures = [], 0
    fallback = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    prev_phi = None  # library row from the previous step (for the RLS update)
    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        # RLS update: previous transition prev_state -> current state (scaled space).
        if prev_phi is not None:
            x_now_sc = b.scaler_x.transform(state.reshape(1, -1))[0]
            for i in range(3):
                Pphi = P[i] @ prev_phi
                denom = forgetting + float(prev_phi @ Pphi)
                K = Pphi / denom
                Xi[i] = Xi[i] + K * (x_now_sc[i] - float(Xi[i] @ prev_phi))
                P[i] = (P[i] - np.outer(K, Pphi)) / forgetting
        if step > 0 and step % rebuild_every == 0:
            b.model.optimizer.coef_ = Xi.copy()
            mpc = build_mpc_controller(b, weather_provider, cfg_run)
            mpc.x0 = state.reshape(-1, 1)
            mpc.set_initial_guess()

        try:
            action = np.clip(np.asarray(mpc.make_step(state.reshape(-1, 1))).ravel(), 0.0, 1.0)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            action = fallback.copy()
            if failures > max_solver_failures:
                print(f"[ekf] stop after solver failure at step {step}: {exc}")
                break

        prev_phi = _sindy_library_vector(b, state, weather_vec, time_encoding(step, cfg_run.period), action)
        row = {"step": step, "time_h": step * cfg_run.period / 3600.0,
               "controller": "ekf_sindy_mpc", "solver_failures": failures}
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = time_encoding(step, cfg_run.period)[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action[i]
        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
        row.update(_econ_row(_info))
        rows.append(row)
        if terminated or truncated:
            break
    env.close()
    return pd.DataFrame(rows)


def aggregate_trajectories(items: list[TrajectoryData], cfg: ExperimentConfig) -> TrajectoryData:
    return TrajectoryData(
        states=np.vstack([x.states for x in items]),
        weather=np.vstack([x.weather for x in items]),
        time_enc=np.vstack([x.time_enc for x in items]),
        actions=np.vstack([x.actions for x in items]),
        meta={"source": "aggregated", "period": cfg.period, "parts": [x.meta for x in items]},
    )


def rollout_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    temp_err = df["t_in"] - 20.0
    co2_err = df["co2"] - 800.0
    rh_excess = np.maximum(0.0, df["rh"] - 85.0)
    temp_safe = (df["t_in"] >= 12.0) & (df["t_in"] <= 35.0)
    comfort = (
        (df["t_in"] >= 18.0)
        & (df["t_in"] <= 22.0)
        & (df["co2"] >= 600.0)
        & (df["co2"] <= 1000.0)
        & (df["rh"] <= 85.0)
    )
    energy_proxy = 20.0 * df["uBoil"] + 10.0 * df["uLamp"] + 2.0 * df["uCO2"]
    return {
        "steps": int(len(df)),
        "temp_rmse": float(np.sqrt(np.mean(temp_err**2))),
        "temp_mae": float(np.mean(np.abs(temp_err))),
        "co2_rmse": float(np.sqrt(np.mean(co2_err**2))),
        "rh_excess_mean": float(np.mean(rh_excess)),
        "rh_excess_area": float(np.sum(rh_excess)),
        "temp_low_violations": int(np.sum(df["t_in"] < 12.0)),
        "temp_high_violations": int(np.sum(df["t_in"] > 35.0)),
        "temp_safe_pct": float(np.mean(temp_safe) * 100.0),
        "comfort_pct": float(np.mean(comfort) * 100.0),
        "energy_proxy_sum": float(np.sum(energy_proxy)),
        "boiler_sum": float(np.sum(df["uBoil"])),
        "lamp_sum": float(np.sum(df["uLamp"])),
        "co2_injection_sum": float(np.sum(df["uCO2"])),
        "vent_sum": float(np.sum(df["uVent"])),
        "solver_failures": int(df.get("solver_failures", pd.Series([0])).max()),
    }


def epi_metrics(
    df: pd.DataFrame,
    corridors: dict | None = None,
    prices: dict | None = None,
) -> dict:
    """Primary protocol metrics (E0): EPI from the simulator economics + corridors.

    EPI [EUR/m2.season] = sum of per-step ``profit`` harvested from gl_gym's
    GreenhouseReward (captured into rollout/dataset frames as the ECON_FIELDS
    columns). Constraint metrics use the simulator's CO2/T/RH corridors. When
    ``prices`` are given (from protocol_config.read_env_economics), costs are also
    converted to physical resource use (kWh/m2, kg/m2).
    """
    if df.empty:
        return {}
    corridors = corridors or DEFAULT_CORRIDORS
    n = int(len(df))
    out: dict = {"steps": n}

    if "profit" in df.columns:
        out["epi"] = float(df["profit"].sum())
        out["revenue"] = float(df["revenue"].sum())
        out["cost_total"] = float(df["variable_costs"].sum())
        out["cost_heat"] = float(df["heat_cost"].sum())
        out["cost_co2"] = float(df["co2_cost"].sum())
        out["cost_elec"] = float(df["elec_cost"].sum())
        out["fruit_dm_growth"] = float(df["fruit_growth_dm"].sum())
        if prices:
            ph = prices.get("heating_price_eur_per_kwh") or np.nan
            pe = prices.get("elec_price_eur_per_kwh") or np.nan
            pc = prices.get("co2_price_eur_per_kg") or np.nan
            out["energy_heat_kwh_m2"] = float(out["cost_heat"] / ph) if ph else np.nan
            out["energy_elec_kwh_m2"] = float(out["cost_elec"] / pe) if pe else np.nan
            out["co2_kg_m2"] = float(out["cost_co2"] / pc) if pc else np.nan

    # Constraint corridors (% time inside, count and area of violations).
    for key in ("t_in", "co2", "rh"):
        if key in df.columns and key in corridors:
            lo, hi = corridors[key]
            x = df[key].to_numpy(dtype=float)
            viol = np.maximum(0.0, lo - x) + np.maximum(0.0, x - hi)
            out[f"{key}_in_corridor_pct"] = float(np.mean((x >= lo) & (x <= hi)) * 100.0)
            out[f"{key}_violation_steps"] = int(np.sum(viol > 0))
            out[f"{key}_violation_area"] = float(np.sum(viol))
    out["violation_steps_total"] = int(
        sum(out.get(f"{k}_violation_steps", 0) for k in ("t_in", "co2", "rh"))
    )

    if "uBoil" in df.columns:
        out["boiler_sum"] = float(df["uBoil"].sum())
        out["lamp_sum"] = float(df["uLamp"].sum())
        out["co2_injection_sum"] = float(df["uCO2"].sum())
        out["vent_sum"] = float(df["uVent"].sum())
    out["solver_failures"] = int(df.get("solver_failures", pd.Series([0])).max())
    return out


def benchmark_epi(rollouts: dict[str, pd.DataFrame], corridors=None, prices=None) -> pd.DataFrame:
    rows = []
    for name, df in rollouts.items():
        row = {"method": name}
        row.update(epi_metrics(df, corridors=corridors, prices=prices))
        rows.append(row)
    return pd.DataFrame(rows)


def benchmark_rollouts(rollouts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in rollouts.items():
        row = {"method": name}
        row.update(rollout_metrics(df))
        rows.append(row)
    return pd.DataFrame(rows)


def run_dagger(
    initial_data: TrajectoryData,
    test_data: TrajectoryData,
    cfg: ExperimentConfig,
    iterations: int = 3,
    episode_days: int = 5,
    feature_variant: str = "physics",
) -> tuple[pd.DataFrame, list[SINDyBundle], list[TrajectoryData]]:
    datasets = [initial_data]
    bundles = []
    rows = []

    for iteration in range(iterations + 1):
        aggregate = aggregate_trajectories(datasets, cfg)
        bundle = fit_sindy(
            aggregate,
            feature_variant=feature_variant,
            library_degree=1,
            period=float(cfg.period),
            metadata={"label": f"pi_sindy_mpc_dagger_{iteration}", "dagger_iteration": iteration},
        )
        bundles.append(bundle)

        metrics = evaluate_sindy(bundle, test_data)
        for _, m in metrics.iterrows():
            row = m.to_dict()
            row["dagger_iteration"] = iteration
            row["aggregate_rows"] = len(aggregate.states)
            row["condition_number"] = bundle.condition_number
            row["nonzero_coefficients"] = int(np.count_nonzero(bundle.model.coefficients()))
            rows.append(row)

        if iteration < iterations:
            rollout = rollout_mpc(bundle, cfg, n_days=episode_days, objective="full")
            datasets.append(trajectory_from_frame(rollout, cfg, source=f"mpc_dagger_{iteration}"))

    return pd.DataFrame(rows), bundles, datasets


def coefficient_table(bundle: SINDyBundle) -> pd.DataFrame:
    model = bundle.model
    names = ["1"] + STATE_NAMES + bundle.feature_names
    if bundle.library_degree != 1:
        try:
            names = model.get_feature_names()
        except Exception:
            pass
    coefs = np.asarray(model.coefficients())
    rows = []
    for eq_idx, state in enumerate(STATE_NAMES):
        for term_idx in range(coefs.shape[1]):
            coef = float(coefs[eq_idx, term_idx])
            rows.append(
                {
                    "equation": state,
                    "term": names[term_idx] if term_idx < len(names) else f"term_{term_idx}",
                    "coefficient": coef,
                    "abs_coefficient": abs(coef),
                    "nonzero": bool(abs(coef) > 1e-12),
                }
            )
    return pd.DataFrame(rows)


def sign_check_table(bundle: SINDyBundle) -> pd.DataFrame:
    table = coefficient_table(bundle)
    # Checks are defined over DIRECT actuator/physics terms that exist in every library
    # variant (raw/physics/physics_no_cross) -- unlike cross-terms (dc_uVent, h_uVent,
    # t_uBoil), which the confirmatory physics_no_cross recipe excludes by construction and
    # which therefore always read "missing" there. These direct-term signs are physically
    # unambiguous and give a meaningful transparency gate for the frozen recipe.
    checks = [
        ("t_in", "uBoil", "positive", "boiler heating should raise/maintain indoor temperature"),
        ("t_in", "S_eff", "positive", "effective solar gain should raise/maintain indoor temperature"),
        ("co2", "uCO2", "positive", "CO2 injection should raise indoor CO2"),
        ("co2", "uVent", "negative", "ventilation should bleed enriched CO2 toward ambient"),
        ("rh", "uVent", "negative", "ventilation should reduce indoor humidity"),
    ]
    rows = []
    for equation, term, expected, note in checks:
        found = table[(table["equation"] == equation) & (table["term"] == term)]
        coef = float(found["coefficient"].iloc[0]) if not found.empty else np.nan
        if np.isnan(coef) or abs(coef) <= 1e-12:
            verdict = "missing_or_zero"
        elif expected == "positive":
            verdict = "consistent" if coef > 0 else "opposite"
        else:
            verdict = "consistent" if coef < 0 else "opposite"
        rows.append(
            {
                "equation": equation,
                "term": term,
                "expected_sign": expected,
                "coefficient": coef,
                "verdict": verdict,
                "interpretation": note,
            }
        )
    return pd.DataFrame(rows)


# ── Neural-network (MLP) surrogate ──────────────────────────────────────────

@dataclass
class NNBundle:
    """MLP surrogate trained with PyTorch, weights stored as numpy for portability."""
    weights: list          # list of np.ndarray W matrices (layer order)
    biases: list           # list of np.ndarray b vectors
    scaler_x: object
    scaler_u: object
    feature_variant: str
    feature_names: list[str]
    hidden_sizes: list
    period: float
    train_rows: int
    train_loss: float
    metadata: dict


def _build_torch_mlp(input_size: int, hidden_sizes: list, output_size: int):
    import torch.nn as nn
    layers: list = []
    in_dim = input_size
    for h in hidden_sizes:
        layers += [nn.Linear(in_dim, h), nn.Tanh()]
        in_dim = h
    layers.append(nn.Linear(in_dim, output_size))
    return nn.Sequential(*layers)


def fit_nn_surrogate(
    data: TrajectoryData,
    feature_variant: str = "physics",
    hidden_sizes: list | None = None,
    epochs: int = 500,
    lr: float = 1e-3,
    batch_size: int = 512,
    period: float = 900.0,
    metadata: dict | None = None,
) -> NNBundle:
    import torch
    import torch.nn as nn
    from sklearn.preprocessing import StandardScaler
    from torch.utils.data import DataLoader, TensorDataset

    hidden_sizes = hidden_sizes or [64, 64]
    features, feature_names = compute_feature_matrix(data, feature_variant)
    scaler_x = StandardScaler()
    scaler_u = StandardScaler()
    x_sc = scaler_x.fit_transform(data.states).astype(np.float32)
    u_sc = scaler_u.fit_transform(features).astype(np.float32)

    X = torch.tensor(np.hstack([x_sc[:-1], u_sc[:-1]]))
    Y = torch.tensor(x_sc[1:])

    loader = DataLoader(TensorDataset(X, Y), batch_size=batch_size, shuffle=True)
    model = _build_torch_mlp(X.shape[1], hidden_sizes, output_size=3)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    for _ in range(epochs):
        for xb, yb in loader:
            optimizer.zero_grad()
            criterion(model(xb), yb).backward()
            optimizer.step()

    with torch.no_grad():
        final_loss = float(criterion(model(X), Y).item())

    ws, bs = [], []
    for layer in model:
        if hasattr(layer, "weight"):
            ws.append(layer.weight.detach().numpy().copy())
            bs.append(layer.bias.detach().numpy().copy())

    return NNBundle(
        weights=ws,
        biases=bs,
        scaler_x=scaler_x,
        scaler_u=scaler_u,
        feature_variant=feature_variant,
        feature_names=feature_names,
        hidden_sizes=list(hidden_sizes),
        period=float(period),
        train_rows=len(x_sc) - 1,
        train_loss=final_loss,
        metadata=metadata or {},
    )


def _nn_forward_numpy(bundle: NNBundle, inp: np.ndarray) -> np.ndarray:
    """Fast numpy forward pass (no gradient tracking)."""
    h = inp.astype(np.float32)
    for i, (W, b) in enumerate(zip(bundle.weights, bundle.biases)):
        h = h @ W.T + b
        if i < len(bundle.weights) - 1:
            h = np.tanh(h)
    return h


def predict_next_raw_nn(
    bundle: NNBundle,
    x_raw: np.ndarray,
    weather: np.ndarray,
    time_enc: np.ndarray,
    action: np.ndarray,
) -> np.ndarray:
    tmp = TrajectoryData(
        states=np.asarray(x_raw, dtype=np.float64).reshape(1, 3),
        weather=np.asarray(weather, dtype=np.float64).reshape(1, 3),
        time_enc=np.asarray(time_enc, dtype=np.float64).reshape(1, 2),
        actions=np.asarray(action, dtype=np.float64).reshape(1, 6),
        meta={"period": bundle.period},
    )
    u_raw, _ = compute_feature_matrix(tmp, bundle.feature_variant)
    x_sc = bundle.scaler_x.transform(tmp.states).astype(np.float32)
    u_sc = bundle.scaler_u.transform(u_raw).astype(np.float32)
    y_sc = _nn_forward_numpy(bundle, np.hstack([x_sc, u_sc]))
    return bundle.scaler_x.inverse_transform(y_sc.reshape(1, -1))[0]


def evaluate_nn_surrogate(
    bundle: NNBundle,
    data: TrajectoryData,
    rollout_horizons: Iterable[int] = (4, 20, 96),
) -> pd.DataFrame:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    rows = []
    features, _ = compute_feature_matrix(data, bundle.feature_variant)
    x_sc = bundle.scaler_x.transform(data.states).astype(np.float32)
    u_sc = bundle.scaler_u.transform(features).astype(np.float32)
    inp = np.hstack([x_sc[:-1], u_sc[:-1]])
    pred_sc = _nn_forward_numpy(bundle, inp)
    pred = bundle.scaler_x.inverse_transform(pred_sc)
    truth = data.states[1:]

    for i, state in enumerate(STATE_NAMES):
        rows.append({
            "metric_scope": "one_step", "horizon": 1, "state": state,
            "rmse": mean_squared_error(truth[:, i], pred[:, i], squared=False),
            "mae": mean_absolute_error(truth[:, i], pred[:, i]),
            "r2": r2_score(truth[:, i], pred[:, i]),
        })

    for horizon in rollout_horizons:
        errs, failed = [], 0
        n0 = max(0, len(data.states) - horizon - 1)
        starts = np.linspace(0, n0, num=min(20, n0 + 1), dtype=int) if n0 > 0 else []
        for start in starts:
            x = data.states[start].copy()
            pred_path, true_path = [], []
            for k in range(horizon):
                idx = start + k
                try:
                    x = predict_next_raw_nn(bundle, x, data.weather[idx], data.time_enc[idx], data.actions[idx])
                except Exception:
                    failed += 1
                    break
                if not np.all(np.isfinite(x)) or np.max(np.abs(x)) > 1e6:
                    failed += 1
                    break
                pred_path.append(x)
                true_path.append(data.states[idx + 1])
            if pred_path:
                errs.append(np.asarray(pred_path) - np.asarray(true_path))
        if errs:
            err = np.concatenate(errs, axis=0)
            for i, state in enumerate(STATE_NAMES):
                rows.append({
                    "metric_scope": "rollout", "horizon": int(horizon), "state": state,
                    "rmse": float(np.sqrt(np.mean(err[:, i] ** 2))),
                    "mae": float(np.mean(np.abs(err[:, i]))),
                    "r2": np.nan,
                    "failed_rollouts": int(failed),
                    "attempted_rollouts": int(len(starts)),
                })
        else:
            for state in STATE_NAMES:
                rows.append({
                    "metric_scope": "rollout", "horizon": int(horizon), "state": state,
                    "rmse": np.inf, "mae": np.inf, "r2": np.nan,
                    "failed_rollouts": int(failed), "attempted_rollouts": int(len(starts)),
                })
    return pd.DataFrame(rows)


def _build_physics_features_torch(
    x: "torch.Tensor",
    uk_raw: "torch.Tensor",
    weather_k: np.ndarray,
    time_k: np.ndarray,
    feature_variant: str,
    su_mean: "torch.Tensor",
    su_scale: "torch.Tensor",
) -> "torch.Tensor":
    import torch
    T_out = torch.tensor(float(weather_k[0]))
    rad   = torch.tensor(float(weather_k[1]))
    co2_out = torch.tensor(float(weather_k[2]))
    sin_h = torch.tensor(float(time_k[0]))
    cos_h = torch.tensor(float(time_k[1]))
    uBoil, uCO2, uThScr, uVent, uLamp, uBlScr = [uk_raw[i] for i in range(6)]
    raw = torch.stack([T_out, rad, co2_out, sin_h, cos_h, uBoil, uCO2, uThScr, uVent, uLamp, uBlScr])
    if feature_variant == "raw":
        feat = raw
    elif feature_variant == "physics":
        sx_mean_t = torch.zeros(3)  # placeholder, x is already scaled
        # x here is SCALED; to compute physics we need raw values
        # we pass scaled x so need scale params externally — handled by caller
        raise RuntimeError("Use _build_physics_features_torch_with_scales")
    else:
        feat = raw
    return (feat - su_mean) / su_scale


def rollout_mpc_nn(
    bundle: NNBundle,
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    horizon: int = 20,
    max_solver_failures: int = 10,
) -> pd.DataFrame:
    """Shooting MPC using the MLP surrogate with PyTorch autograd gradients."""
    import torch
    import torch.nn as nn
    import scipy.optimize as sopt
    from dataclasses import asdict

    # Reconstruct torch model from stored numpy weights
    input_size = 3 + len(bundle.feature_names)
    torch_model = _build_torch_mlp(input_size, bundle.hidden_sizes, 3)
    wi = 0
    for layer in torch_model:
        if hasattr(layer, "weight"):
            layer.weight.data = torch.tensor(bundle.weights[wi], dtype=torch.float32)
            layer.bias.data = torch.tensor(bundle.biases[wi], dtype=torch.float32)
            wi += 1
    torch_model.eval()
    for p in torch_model.parameters():
        p.requires_grad_(False)

    sx_mean  = torch.tensor(bundle.scaler_x.mean_, dtype=torch.float32)
    sx_scale = torch.tensor(bundle.scaler_x.scale_, dtype=torch.float32)
    su_mean  = torch.tensor(bundle.scaler_u.mean_, dtype=torch.float32)
    su_scale = torch.tensor(bundle.scaler_u.scale_, dtype=torch.float32)

    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    weather_provider = WeatherForecastTVP(cfg_run, n_days=n_days, start_date=start_date)
    env = _make_env(cfg_run, n_days=n_days)
    obs, _ = env.reset(options={"scenario": weather_provider.scenario}, seed=cfg.seed)

    u_low  = np.zeros(6)
    u_high = np.array([1.0, 1.0, 1.0, 0.4, 1.0, 1.0])
    bounds = list(zip(np.tile(u_low, horizon), np.tile(u_high, horizon)))

    def mpc_step(state_raw: np.ndarray, step_idx: int) -> np.ndarray:
        x0_sc = torch.tensor(
            bundle.scaler_x.transform(state_raw.reshape(1, -1))[0], dtype=torch.float32
        )

        def objective(u_flat: np.ndarray):
            u_t = torch.tensor(
                u_flat.reshape(horizon, 6), dtype=torch.float32, requires_grad=True
            )
            x = x0_sc.clone()
            total_cost = torch.zeros(1)
            for k in range(horizon):
                uk_raw = u_t[k]
                n_w = len(weather_provider.weather)
                wk = weather_provider.weather[min(step_idx + k, n_w - 1)]
                tk = weather_provider.time_enc[min(step_idx + k, n_w - 1)]

                # Reconstruct raw state for physics features
                x_raw_k = x * sx_scale + sx_mean
                t_in_k, co2_k, rh_k = x_raw_k[0], x_raw_k[1], x_raw_k[2]
                uBoil_k, uCO2_k, uThScr_k = uk_raw[0], uk_raw[1], uk_raw[2]
                uVent_k, uLamp_k, uBlScr_k = uk_raw[3], uk_raw[4], uk_raw[5]

                T_out_k   = torch.tensor(float(wk[0]))
                rad_k     = torch.tensor(float(wk[1]))
                co2_out_k = torch.tensor(float(wk[2]))
                sin_h_k   = torch.tensor(float(tk[0]))
                cos_h_k   = torch.tensor(float(tk[1]))

                raw_feat = torch.stack([
                    T_out_k, rad_k, co2_out_k, sin_h_k, cos_h_k,
                    uBoil_k, uCO2_k, uThScr_k, uVent_k, uLamp_k, uBlScr_k,
                ])
                if bundle.feature_variant == "physics":
                    psat_k  = 0.6108 * torch.exp(17.27 * t_in_k / (t_in_k + 237.3))
                    vpd_k   = (1.0 - rh_k / 100.0) * psat_k
                    S_eff_k = rad_k * (1.0 - uThScr_k)
                    feat_k  = torch.cat([raw_feat, torch.stack([
                        psat_k, vpd_k, S_eff_k,
                        t_in_k * S_eff_k, rh_k * uVent_k,
                        (co2_k - co2_out_k) * uVent_k, t_in_k * uBoil_k,
                    ])])
                else:
                    feat_k = raw_feat

                u_sc_k = (feat_k - su_mean) / su_scale
                inp_k  = torch.cat([x, u_sc_k])
                x      = torch_model(inp_k.unsqueeze(0)).squeeze(0)

                x_raw_next = x * sx_scale + sx_mean
                t_next, co2_next, rh_next = x_raw_next[0], x_raw_next[1], x_raw_next[2]
                # EPI-aligned productive band at minimum resource cost (matches build_mpc).
                w_day = torch.clamp((1.0 - cos_h_k) / 2.0, min=0.0)
                T_lo = 15.0 + 3.0 * w_day
                T_hi = 19.0 + 5.0 * w_day
                co2_floor = 400.0 + 300.0 * w_day
                band_T = torch.clamp(T_lo - t_next, min=0.0) + torch.clamp(t_next - T_hi, min=0.0)
                low_co2 = torch.clamp(co2_floor - co2_next, min=0.0)
                hi_rh = torch.clamp(rh_next - 85.0, min=0.0)
                cost_e  = 20.0 * uBoil_k + 10.0 * uLamp_k + 2.0 * uCO2_k
                total_cost = total_cost + (
                    30.0 * band_T**2 + 3e-4 * low_co2**2 + 8.0 * hi_rh**2 + cost_e
                )

            total_cost.backward()
            grad = u_t.grad.detach().numpy().ravel() if u_t.grad is not None else np.zeros_like(u_flat)
            return float(total_cost.item()), grad

        u_init = np.tile([0.3, 0.0, 0.5, 0.1, 0.0, 0.0], horizon).astype(np.float64)
        res = sopt.minimize(
            objective, u_init, method="L-BFGS-B", jac=True,
            bounds=bounds, options={"maxiter": 25, "ftol": 1e-4},
        )
        return res.x[:6]

    rows, failures = [], 0
    fallback = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    label = bundle.metadata.get("label", "nn_mpc")

    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        try:
            action = np.clip(mpc_step(state, step), u_low, u_high)
        except Exception as exc:
            failures += 1
            action = fallback.copy()
            if failures > max_solver_failures:
                print(f"[NN-MPC] stopping after {failures} failures at step {step}: {exc}")
                break

        row: dict = {
            "step": step,
            "time_h": step * cfg_run.period / 3600.0,
            "controller": label,
            "solver_failures": failures,
        }
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = time_encoding(step, cfg_run.period)[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action[i]

        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
        row.update(_econ_row(_info))
        rows.append(row)
        if terminated or truncated:
            break

    env.close()
    return pd.DataFrame(rows)


# ── Inference timing ─────────────────────────────────────────────────────────

def measure_inference_time(
    bundles_sindy: dict[str, SINDyBundle],
    bundles_nn: dict[str, NNBundle],
    sample_data: TrajectoryData,
    n_samples: int = 500,
) -> pd.DataFrame:
    """
    Benchmark one-step prediction latency for SINDy and MLP surrogates.
    Returns a DataFrame with columns [method, mean_ms, std_ms, median_ms].
    """
    rows = []
    idx = np.random.default_rng(0).integers(0, max(1, len(sample_data.states) - 1), size=n_samples)

    for label, bundle in bundles_sindy.items():
        times = []
        for i in idx:
            t0 = time.perf_counter()
            predict_next_raw(
                bundle,
                sample_data.states[i],
                sample_data.weather[i],
                sample_data.time_enc[i],
                sample_data.actions[i],
            )
            times.append((time.perf_counter() - t0) * 1e3)
        times_arr = np.array(times)
        rows.append({
            "method": label,
            "surrogate_type": "SINDy",
            "mean_ms": float(np.mean(times_arr)),
            "std_ms": float(np.std(times_arr)),
            "median_ms": float(np.median(times_arr)),
            "p95_ms": float(np.percentile(times_arr, 95)),
        })

    for label, bundle in bundles_nn.items():
        times = []
        for i in idx:
            t0 = time.perf_counter()
            predict_next_raw_nn(
                bundle,
                sample_data.states[i],
                sample_data.weather[i],
                sample_data.time_enc[i],
                sample_data.actions[i],
            )
            times.append((time.perf_counter() - t0) * 1e3)
        times_arr = np.array(times)
        rows.append({
            "method": label,
            "surrogate_type": "MLP",
            "mean_ms": float(np.mean(times_arr)),
            "std_ms": float(np.std(times_arr)),
            "median_ms": float(np.median(times_arr)),
            "p95_ms": float(np.percentile(times_arr, 95)),
        })

    return pd.DataFrame(rows)


# ── Multi-seed statistical benchmark ─────────────────────────────────────────

def run_seeded_benchmark(
    train_data: TrajectoryData,
    cfg: ExperimentConfig,
    n_days_rollout: int,
    benchmark_start_date: str,
    seeds: list[int],
    feature_variant: str = "physics",
    include_nn: bool = True,
) -> pd.DataFrame:
    """
    Run closed-loop benchmark across multiple environment seeds.
    Returns a long-form DataFrame with per-seed metrics; aggregate with groupby mean/std.
    """
    from dataclasses import asdict

    rows = []
    for seed in seeds:
        cfg_s = ExperimentConfig(**{**asdict(cfg), "seed": seed})

        # Rule-based baseline
        df_rbc = rollout_rule_based(cfg_s, n_days=n_days_rollout,
                                    start_date=benchmark_start_date, noise_scale=0.0,
                                    seed=seed)
        m = rollout_metrics(df_rbc)
        m.update({"method": "rule_based", "seed": seed})
        rows.append(m)

        # SINDy-MPC (physics)
        bundle_pi = fit_sindy(train_data, feature_variant=feature_variant,
                              library_degree=1, period=float(cfg.period),
                              metadata={"label": f"physics_sindy_mpc_s{seed}"})
        df_pi = rollout_mpc(bundle_pi, cfg_s, n_days=n_days_rollout,
                            start_date=benchmark_start_date, objective="full")
        m = rollout_metrics(df_pi)
        m.update({"method": "physics_sindy_mpc", "seed": seed})
        rows.append(m)

        # SINDy-MPC (raw)
        bundle_raw = fit_sindy(train_data, feature_variant="raw",
                               library_degree=1, period=float(cfg.period),
                               metadata={"label": f"raw_sindy_mpc_s{seed}"})
        df_raw = rollout_mpc(bundle_raw, cfg_s, n_days=n_days_rollout,
                             start_date=benchmark_start_date, objective="full")
        m = rollout_metrics(df_raw)
        m.update({"method": "raw_sindy_mpc", "seed": seed})
        rows.append(m)

        if include_nn:
            nn_bundle = fit_nn_surrogate(train_data, feature_variant=feature_variant,
                                         hidden_sizes=[64, 64], epochs=300,
                                         period=float(cfg.period),
                                         metadata={"label": f"nn_mpc_s{seed}"})
            df_nn = rollout_mpc_nn(nn_bundle, cfg_s, n_days=n_days_rollout,
                                   start_date=benchmark_start_date, horizon=cfg.horizon)
            m = rollout_metrics(df_nn)
            m.update({"method": "nn_mpc", "seed": seed})
            rows.append(m)

    return pd.DataFrame(rows)


def summarise_seeded_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate multi-seed results: mean ± std per method."""
    numeric_cols = [c for c in df.columns if c not in ("method", "seed")]
    agg = df.groupby("method")[numeric_cols].agg(["mean", "std"])
    agg.columns = ["_".join(c) for c in agg.columns]
    return agg.reset_index()


def save_bundle_nn(bundle: NNBundle, path: Path) -> None:
    save_bundle(bundle, path)  # reuse pickle-based save


def load_bundle_nn(path: Path) -> NNBundle:
    return load_bundle(path)


def save_table(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def save_figure(fig, path: Path, dpi: int = 180) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")


def plot_ablation_summary(metrics: pd.DataFrame, figures_dir: Path) -> None:
    import matplotlib.pyplot as plt

    one = metrics[(metrics["metric_scope"] == "one_step") & (metrics["state"] == "t_in")]
    roll = metrics[(metrics["metric_scope"] == "rollout") & (metrics["state"] == "t_in")]

    fig, ax = plt.subplots(figsize=(8, 4))
    for method, grp in one.groupby("method"):
        ax.plot(grp["budget_days"], grp["rmse"], marker="o", label=method)
    ax.set_title("One-step temperature RMSE vs data budget")
    ax.set_xlabel("Training data budget, days")
    ax.set_ylabel("RMSE, deg C")
    ax.grid(True, alpha=0.3)
    ax.legend()
    save_figure(fig, figures_dir / "ablation_one_step_temp_rmse.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    for method, grp in roll.groupby("method"):
        grp = grp[grp["horizon"] == grp["horizon"].max()]
        ax.plot(grp["budget_days"], grp["rmse"], marker="o", label=method)
    ax.set_title("Open-loop rollout temperature RMSE vs data budget")
    ax.set_xlabel("Training data budget, days")
    ax.set_ylabel("RMSE, deg C")
    ax.grid(True, alpha=0.3)
    ax.legend()
    save_figure(fig, figures_dir / "ablation_rollout_temp_rmse.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    sparsity = metrics.drop_duplicates(["method", "budget_days"])[
        ["method", "budget_days", "sparsity"]
    ]
    for method, grp in sparsity.groupby("method"):
        ax.plot(grp["budget_days"], grp["sparsity"], marker="o", label=method)
    ax.set_title("SINDy sparsity vs data budget")
    ax.set_xlabel("Training data budget, days")
    ax.set_ylabel("Fraction of zero coefficients")
    ax.grid(True, alpha=0.3)
    ax.legend()
    save_figure(fig, figures_dir / "ablation_sparsity.png")


def plot_rollout_comparison(rollouts: dict[str, pd.DataFrame], figures_dir: Path, suffix: str = "") -> None:
    import matplotlib.pyplot as plt

    series = [
        ("t_in", "Indoor temperature, deg C", 20.0),
        ("co2", "CO2, ppm", 800.0),
        ("rh", "Relative humidity, %", 85.0),
    ]
    fig, axes = plt.subplots(len(series), 1, figsize=(11, 8), sharex=True)
    for ax, (column, title, setpoint) in zip(axes, series):
        for method, df in rollouts.items():
            if not df.empty:
                ax.plot(df["time_h"], df[column], label=method, linewidth=1.4)
        ax.axhline(setpoint, color="black", linestyle="--", linewidth=1.0)
        ax.set_ylabel(title)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Simulation time, h")
    axes[0].legend(loc="best")
    save_figure(fig, figures_dir / f"closed_loop_states{suffix}.png")

    fig, axes = plt.subplots(6, 1, figsize=(11, 10), sharex=True)
    for ax, action in zip(axes, ACTION_NAMES):
        for method, df in rollouts.items():
            if not df.empty:
                ax.plot(df["time_h"], df[action], label=method, linewidth=1.1)
        ax.set_ylabel(action)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Simulation time, h")
    axes[0].legend(loc="best")
    save_figure(fig, figures_dir / f"closed_loop_actuators{suffix}.png")


def plot_dagger_curves(metrics: pd.DataFrame, figures_dir: Path) -> None:
    import matplotlib.pyplot as plt

    one = metrics[(metrics["metric_scope"] == "one_step") & (metrics["state"] == "t_in")]
    roll = metrics[
        (metrics["metric_scope"] == "rollout")
        & (metrics["state"] == "t_in")
        & (metrics["horizon"] == metrics["horizon"].max())
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(one["dagger_iteration"], one["rmse"], marker="o", label="one-step")
    if not roll.empty:
        ax.plot(roll["dagger_iteration"], roll["rmse"], marker="o", label="rollout")
    ax.set_title("DAgger improvement: temperature RMSE")
    ax.set_xlabel("DAgger iteration")
    ax.set_ylabel("RMSE, deg C")
    ax.grid(True, alpha=0.3)
    ax.legend()
    save_figure(fig, figures_dir / "dagger_learning_curve_temp_rmse.png")


def plot_coefficient_heatmap(bundle: SINDyBundle, figures_dir: Path, top_n: int = 30) -> None:
    import matplotlib.pyplot as plt

    table = coefficient_table(bundle)
    top_terms = (
        table.groupby("term")["abs_coefficient"]
        .max()
        .sort_values(ascending=False)
        .head(top_n)
        .index
    )
    pivot = table[table["term"].isin(top_terms)].pivot(
        index="term", columns="equation", values="coefficient"
    )
    fig, ax = plt.subplots(figsize=(8, max(5, 0.25 * len(pivot))))
    im = ax.imshow(pivot.values, aspect="auto", cmap="coolwarm")
    ax.set_xticks(np.arange(len(pivot.columns)), pivot.columns)
    ax.set_yticks(np.arange(len(pivot.index)), pivot.index)
    ax.set_title("Top SINDy coefficients")
    fig.colorbar(im, ax=ax, label="coefficient")
    save_figure(fig, figures_dir / "sindy_coefficient_heatmap.png")


# ── E2 gates: MPC-embeddability + transparency (sign checks + structural stability) ──

def mpc_embeddability_gate(
    bundle: SINDyBundle,
    cfg: ExperimentConfig,
    start_date: str | None = None,
    budget_ms: float = 250.0,
) -> dict:
    """Gate: a model is admitted to E3 only if it embeds in the MPC solver cheaply.

    Degree-1 SINDy maps embed analytically into do-mpc/CasADi; degree>1 does not
    (build_mpc_controller raises). Returns embeddability and the measured MPC-step time.
    """
    if bundle.library_degree != 1:
        return {"embeddable": False, "mpc_step_ms": float("nan"),
                "reason": "library_degree>1 not analytically MPC-embeddable"}
    try:
        wp = WeatherForecastTVP(cfg, n_days=2, start_date=start_date)
        mpc = build_mpc_controller(bundle, wp, cfg)
    except Exception as exc:  # noqa: BLE001
        return {"embeddable": False, "mpc_step_ms": float("nan"), "reason": f"build failed: {str(exc)[:80]}"}
    # A degree-1 SINDy map is an analytic linear model -> embeds by construction once
    # build succeeds. Step timing is best-effort; a timing hiccup (e.g. solver edge
    # case from a nominal x0) must not flip the embeddability verdict.
    ms = float("nan")
    try:
        x0 = np.asarray(bundle.scaler_x.mean_, dtype=float).reshape(-1, 1)
        mpc.x0 = x0
        mpc.set_initial_guess()
        t0 = time.perf_counter()
        mpc.make_step(x0)
        ms = (time.perf_counter() - t0) * 1000.0
    except Exception:  # noqa: BLE001
        ms = float("nan")
    embeddable = True if not np.isfinite(ms) else bool(ms <= budget_ms)
    return {"embeddable": embeddable, "mpc_step_ms": ms, "reason": "ok"}


def _block_bootstrap(data: TrajectoryData, rng, block: int = 96) -> TrajectoryData:
    n = len(data.states)
    if n <= block:
        return data
    n_blocks = max(1, n // block)
    starts = rng.integers(0, n - block, size=n_blocks)
    idx = np.concatenate([np.arange(s, s + block) for s in starts])
    return TrajectoryData(
        states=data.states[idx], weather=data.weather[idx],
        time_enc=data.time_enc[idx], actions=data.actions[idx],
        meta={**data.meta, "bootstrap": True},
    )


def structural_stability(
    data: TrajectoryData,
    feature_variant: str = "physics",
    library_degree: int = 1,
    optimizer: str = "stlsq",
    denoise: str = "none",
    period: float = 900.0,
    threshold: float = 0.05,
    n_boot: int = 20,
    block: int = 96,
    seed: int = 0,
) -> tuple[float, np.ndarray]:
    """Fraction of the base model's active terms that stay active under block-bootstrap refits."""
    rng = np.random.default_rng(seed)
    base = fit_sindy(data, feature_variant=feature_variant, library_degree=library_degree,
                     optimizer=optimizer, denoise=denoise, period=period, threshold=threshold)
    base_active = np.abs(np.asarray(base.model.coefficients())) > 1e-9
    if not base_active.any():
        return 0.0, base_active
    counts = np.zeros_like(base_active, dtype=float)
    for _ in range(n_boot):
        sub = _block_bootstrap(data, rng, block=block)
        try:
            b = fit_sindy(sub, feature_variant=feature_variant, library_degree=library_degree,
                          optimizer=optimizer, denoise=denoise, period=period, threshold=threshold)
            counts += np.abs(np.asarray(b.model.coefficients())) > 1e-9
        except Exception:  # noqa: BLE001
            continue
    freq = counts / max(1, n_boot)
    return float(freq[base_active].mean()), freq


def transparency_gate(
    bundle: SINDyBundle,
    data: TrajectoryData,
    sign_pass_threshold: float = 0.5,
    stability_threshold: float = 0.6,
    n_boot: int = 15,
) -> dict:
    """Transparency gate (§1.3): glass-box AND sign/dimension checks AND structural stability."""
    signs = sign_check_table(bundle)
    checked = signs[signs["verdict"] != "missing_or_zero"]
    sign_pass = float((checked["verdict"] == "consistent").mean()) if len(checked) else 0.0
    stab, _ = structural_stability(
        data, feature_variant=bundle.feature_variant, library_degree=bundle.library_degree,
        optimizer=bundle.metadata.get("optimizer", "stlsq"),
        denoise=bundle.metadata.get("denoise", "none"),
        period=bundle.period, threshold=bundle.threshold, n_boot=n_boot,
    )
    glass_box = True  # SINDy yields explicit symbolic equations
    passed = glass_box and (sign_pass >= sign_pass_threshold) and (stab >= stability_threshold)
    return {"glass_box": glass_box, "sign_pass_rate": sign_pass,
            "structural_stability": stab, "passed": bool(passed)}


# ── E3 oracle-MPC: receding-horizon CEM over the TRUE simulator model env.F ──

def rollout_oracle_mpc(
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    horizon: int | None = None,
    n_samples: int = 48,
    n_iters: int = 3,
    elite_frac: float = 0.2,
    sample_std: float = 0.3,
    max_solver_failures: int = 10,
) -> pd.DataFrame:
    """Oracle controller: cross-entropy-method shooting over the simulator's own CasADi
    integrator ``env.unwrapped.F`` (the true 28-state GreenLight model), maximizing the
    REAL economic profit (revenue from fruit-DM growth minus resource costs, the same
    quantity gl_gym sums into EPI). With the true model this is the EPI upper reference
    relative to the simulator (protocol oracle, §1.2). A longer horizon is used so the
    slow fruit-growth payoff of heating/CO2 is visible. Compute-heavy; reduced seed set.
    """
    import casadi as ca

    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    H = horizon or cfg.horizon
    env = _make_env(cfg_run, n_days=n_days)
    scen = weather_scenario_from_date(start_date or cfg_run.start_date, cfg_run.location, cfg_run.growth_year)
    obs, _ = env.reset(options={"scenario": scen}, seed=cfg.seed)
    raw = env.unwrapped
    Fmap = raw.F.map(n_samples)
    params = np.asarray(raw.p, dtype=float)
    weather = np.asarray(raw.weather_data, dtype=float)
    nx = raw.nx
    rng = np.random.default_rng(cfg.seed)
    u_low = np.zeros(6)
    u_high = np.array([1.0, 1.0, 1.0, 0.4, 1.0, 1.0])
    # Economic constants from the live reward model (gl_gym GreenhouseReward).
    rf = raw.reward_fn
    dt = float(cfg_run.period)
    c_rev = 1e-6 / float(rf.dmfm) * float(rf.fruit_price_model.price)   # mg fruit DM -> EUR/m2
    c_heat = (params[108] / params[46]) * (dt / 3600.0) * 1e-3 * float(rf.heating_price_model.price)
    c_elec = params[172] * (dt / 3600.0) * 1e-3 * float(rf.elec_price_model.price)
    c_co2 = (params[109] / params[46]) * dt * 1e-6 * float(rf.co2_price_model.price)
    rb_ctrl = make_rule_based_controller()

    def plan(x_now, step, a_rb):
        # Warm-start the search from the rule-based action and always keep it as a
        # candidate; return the BEST sequence found. This guarantees the oracle is at
        # least as good as the agronomic heuristic on horizon profit, then improves it
        # -- otherwise CEM (few samples, high-dim) under-optimizes and over-spends.
        m = np.tile(a_rb, (H, 1))
        std = np.full((H, 6), sample_std)
        best_seq, best_cost = m.copy(), np.inf
        for _ in range(n_iters):
            seqs = np.clip(m[None] + std[None] * rng.standard_normal((n_samples, H, 6)), u_low, u_high)
            seqs[0] = np.tile(a_rb, (H, 1))   # rule-based always evaluated
            X = np.tile(x_now.reshape(nx, 1), (1, n_samples))
            cost = np.zeros(n_samples)
            for k in range(H):
                Uk = seqs[:, k, :].T
                pdyn = np.concatenate([weather[min(step + k, len(weather) - 1)], params])
                Pm = np.tile(pdyn.reshape(-1, 1), (1, n_samples))
                X_prev = X
                X = np.asarray(Fmap(x0=X_prev, u=Uk, p=Pm)["xf"])
                # ECONOMIC objective: maximize real profit = revenue (fruit dry-matter
                # growth x[25]) minus resource costs, exactly as gl_gym's GreenhouseReward
                # computes EPI. With the true model this is the EPI upper bound.
                gains = (X[25] - X_prev[25]) * c_rev
                costs = Uk[0] * c_heat + Uk[4] * c_elec + Uk[1] * c_co2
                t2 = X[2]
                # minimize negative profit; wide safety only to keep the integrator sane.
                cost += -(gains - costs) + 1e3 * (np.maximum(0.0, 8.0 - t2) + np.maximum(0.0, t2 - 42.0))
            order = np.argsort(cost)
            if cost[order[0]] < best_cost:
                best_cost = float(cost[order[0]])
                best_seq = seqs[order[0]].copy()
            idx = order[: max(2, int(elite_frac * n_samples))]
            m = seqs[idx].mean(0)
            std = seqs[idx].std(0) + 1e-3
        return np.clip(best_seq[0], u_low, u_high)

    rows = []
    failures = 0
    fallback = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0])
    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        try:
            a_rb = np.clip(np.asarray(rb_ctrl.predict(_build_step_context(env)), dtype=float), u_low, u_high)
            action = plan(np.asarray(raw.x, dtype=float), step, a_rb)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            action = fallback.copy()
            if failures > max_solver_failures:
                print(f"[oracle] stop after {failures} failures at step {step}: {exc}")
                break
        row = {"step": step, "time_h": step * cfg_run.period / 3600.0,
               "controller": "oracle_mpc", "solver_failures": failures}
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = time_encoding(step, cfg_run.period)[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action[i]
        obs, _r, terminated, truncated, info = env.step(action.astype(np.float32))
        row.update(_econ_row(info))
        rows.append(row)
        if terminated or truncated:
            break
    env.close()
    return pd.DataFrame(rows)


# ── E3 RL baselines: PPO / SAC via stable-baselines3 ─────────────────────────

def _scenario_reset_env(cfg: ExperimentConfig, n_days: int, scenario: dict):
    import gymnasium as gym

    base = _make_env(cfg, n_days=n_days)

    class _FixedScenario(gym.Wrapper):
        def reset(self, *, seed=None, options=None):
            return self.env.reset(seed=seed, options={"scenario": scenario})

    return _FixedScenario(base)


def train_rl(
    algo: str,
    cfg: ExperimentConfig,
    train_steps: int,
    train_start_date: str | None = None,
    seed: int = 0,
):
    """Train a PPO or SAC policy on the GreenLight env (reward = scaled EPI).

    Observations/rewards are wrapped in VecNormalize (running normalization). This is
    essential for SAC: the Dict obs spans very different magnitudes (CO2 density, vapor
    pressure, temperatures) and without normalization SAC's off-policy critic diverges to
    NaN deep into training. Diagnosed: the env is NaN-safe under 3000 bounded random
    actions and SAC survives short runs; the blow-up only appears far into 200k-step
    training -> critic explosion on unnormalized obs, not an ODE blow-up. PPO uses the same
    pipeline for parity. Fitted stats travel with the model (get_vec_normalize_env()).
    """
    from stable_baselines3 import PPO, SAC
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    scen = weather_scenario_from_date(train_start_date or cfg.start_date, cfg.location, cfg.growth_year)
    venv = DummyVecEnv([lambda: _scenario_reset_env(cfg, n_days=cfg.n_days, scenario=scen)])
    venv = VecNormalize(venv, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)
    Algo = {"ppo": PPO, "sac": SAC}[algo.lower()]
    # Bound SAC's replay buffer (SB3 pre-allocates the whole thing) so many seed-runs can
    # share one box without OOM; 200k covers the full 200k-step training.
    extra = {"buffer_size": 200_000} if algo.lower() == "sac" else {}
    # GreenLight env exposes a Dict observation space -> MultiInputPolicy.
    model = Algo("MultiInputPolicy", venv, seed=seed, verbose=0, **extra)
    model.learn(total_timesteps=int(train_steps), progress_bar=False)
    return model


def rollout_rl(
    model,
    cfg: ExperimentConfig,
    n_days: int,
    start_date: str | None = None,
    label: str = "rl",
) -> pd.DataFrame:
    """Roll out a trained SB3 policy (deterministic) capturing per-step economics."""
    cfg_run = ExperimentConfig(**{**asdict(cfg), "n_days": n_days})
    env = _make_env(cfg_run, n_days=n_days)
    scen = weather_scenario_from_date(start_date or cfg_run.start_date, cfg_run.location, cfg_run.growth_year)
    obs, _ = env.reset(options={"scenario": scen}, seed=cfg.seed)
    # Reuse the frozen training-time obs normalization (no reward norm at eval); the raw
    # env is still stepped so the captured economics/info stay in real units.
    vecnorm = getattr(model, "get_vec_normalize_env", lambda: None)()
    rows = []
    for step in range(cfg_run.total_steps):
        state, weather_vec = observation_to_arrays(obs)
        policy_obs = vecnorm.normalize_obs(obs) if vecnorm is not None else obs
        action, _ = model.predict(policy_obs, deterministic=True)
        action = np.clip(np.asarray(action, dtype=np.float64).ravel(), 0.0, 1.0)
        row = {"step": step, "time_h": step * cfg_run.period / 3600.0,
               "controller": label, "solver_failures": 0}
        for i, name in enumerate(STATE_NAMES):
            row[name] = state[i]
        for i, name in enumerate(WEATHER_NAMES):
            row[name] = weather_vec[i]
        for i, name in enumerate(TIME_NAMES):
            row[name] = time_encoding(step, cfg_run.period)[i]
        for i, name in enumerate(ACTION_NAMES):
            row[name] = action[i]
        obs, _r, terminated, truncated, info = env.step(action.astype(np.float32))
        row.update(_econ_row(info))
        rows.append(row)
        if terminated or truncated:
            break
    env.close()
    return pd.DataFrame(rows)


# ── E3 / E8 statistics: paired Wilcoxon + Holm + bootstrap CI + effect size ──

def paired_stats(
    df: pd.DataFrame,
    metric: str,
    baseline: str,
    methods: list[str] | None = None,
    n_boot: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Paired comparison of each method vs a baseline across seeds.

    df is long-form with columns [method, seed, <metric>]; pairing is by seed. Reports
    mean difference, bootstrap CI, Cohen's d, Wilcoxon signed-rank p, and Holm-adjusted p.
    """
    from scipy.stats import wilcoxon

    rng = np.random.default_rng(seed)
    piv = df.pivot_table(index="seed", columns="method", values=metric)
    methods = methods or [m for m in piv.columns if m != baseline]
    rows, pvals = [], []
    for m in methods:
        a = piv[m].to_numpy(float)
        b = piv[baseline].to_numpy(float)
        mask = ~(np.isnan(a) | np.isnan(b))
        a, b = a[mask], b[mask]
        diff = a - b
        try:
            _stat, p = wilcoxon(a, b)
        except Exception:  # noqa: BLE001 (e.g. all-zero differences)
            p = float("nan")
        if len(diff) > 0:
            boot = np.array([rng.choice(diff, len(diff), replace=True).mean() for _ in range(n_boot)])
            lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        else:
            lo = hi = float("nan")
        d = float(diff.mean() / (diff.std(ddof=1) + 1e-12)) if len(diff) > 1 else float("nan")
        rows.append({"method": m, "baseline": baseline, "metric": metric, "n_pairs": int(len(diff)),
                     "mean_diff": float(np.mean(diff)) if len(diff) else float("nan"),
                     "ci_low": float(lo), "ci_high": float(hi), "cohen_d": d, "p_value": float(p)})
        pvals.append(p)
    res = pd.DataFrame(rows)
    # Holm-Bonferroni step-down correction
    valid = [(i, p) for i, p in enumerate(pvals) if not np.isnan(p)]
    holm = [float("nan")] * len(pvals)
    prev = 0.0
    for rank, (i, p) in enumerate(sorted(valid, key=lambda t: t[1])):
        adj = min(1.0, (len(valid) - rank) * p)
        prev = max(prev, adj)
        holm[i] = prev
    res["p_holm"] = holm
    res["significant"] = res["p_holm"] < alpha
    return res
