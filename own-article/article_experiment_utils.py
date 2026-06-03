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
    np.savez_compressed(
        path,
        states=data.states,
        weather=data.weather,
        time_enc=data.time_enc,
        actions=data.actions,
        meta=json.dumps(data.meta, ensure_ascii=False),
    )


def load_dataset(path: Path) -> TrajectoryData:
    z = np.load(path, allow_pickle=False)
    return TrajectoryData(
        states=z["states"],
        weather=z["weather"],
        time_enc=z["time_enc"],
        actions=z["actions"],
        meta=json.loads(str(z["meta"])),
    )


def save_bundle(bundle: SINDyBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_bundle(path: Path) -> SINDyBundle:
    with path.open("rb") as f:
        return pickle.load(f)


def _make_env(cfg: ExperimentConfig, n_days: int | None = None):
    import gl_gym  # noqa: F401
    import gymnasium as gym

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


def make_rule_based_controller():
    from gl_gym.components.rule_based import RuleBasedController

    return RuleBasedController(
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
) -> TrajectoryData:
    cfg = ExperimentConfig(**{**asdict(cfg), "n_days": n_days or cfg.n_days})
    start_date = start_date or cfg.start_date
    seed = cfg.seed if seed is None else seed
    noise_scale = cfg.noise_scale if noise_scale is None else noise_scale
    noise_period = cfg.noise_period if noise_period is None else noise_period
    scenario = weather_scenario_from_date(start_date, cfg.location, cfg.growth_year)

    env = _make_env(cfg, n_days=cfg.n_days)
    controller = make_rule_based_controller()
    rng = np.random.default_rng(seed)
    obs, reset_info = env.reset(options={"scenario": scenario}, seed=seed)
    scenario = reset_info.get("scenario", scenario)

    states, weather, times, actions = [], [], [], []
    current_noise = np.zeros(6, dtype=np.float64)
    noise_countdown = 0

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

        action = np.clip(base_action + current_noise, env.action_space.low, env.action_space.high)

        states.append(state)
        weather.append(weather_vec)
        times.append(time_encoding(step, cfg.period))
        actions.append(action.astype(np.float64))

        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
        if terminated or truncated:
            break

    env.close()
    return TrajectoryData(
        states=np.asarray(states),
        weather=np.asarray(weather),
        time_enc=np.asarray(times),
        actions=np.asarray(actions),
        meta={
            "source": "rule_based",
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


def fit_sindy(
    data: TrajectoryData,
    feature_variant: str = "physics",
    library_degree: int = 1,
    threshold: float = 0.05,
    alpha: float = 0.01,
    period: float = 900.0,
    metadata: dict | None = None,
) -> SINDyBundle:
    import pysindy as ps
    from sklearn.preprocessing import StandardScaler

    features, feature_names = compute_feature_matrix(data, feature_variant)
    scaler_x = StandardScaler()
    scaler_u = StandardScaler()
    x_sc = scaler_x.fit_transform(data.states)
    u_sc = scaler_u.fit_transform(features)

    x_in = x_sc[:-1]
    u_in = u_sc[:-1]
    x_out = x_sc[1:]
    kappa = condition_number(np.hstack([x_in, u_in]))

    model = ps.SINDy(
        optimizer=ps.STLSQ(
            threshold=threshold,
            alpha=alpha,
            max_iter=200,
            normalize_columns=False,
        ),
        feature_library=ps.PolynomialLibrary(degree=library_degree, include_bias=True),
        feature_names=STATE_NAMES + feature_names,
    )
    model.fit(x_in, u=u_in, x_dot=x_out, t=period)

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
        metadata=metadata or {},
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
                "rmse": mean_squared_error(truth[:, i], pred[:, i], squared=False),
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
            k_start = int(t_now / period)
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
        err_T = (t_in - 20.0) / 5.0
        err_co2 = (co2 - 800.0) / 200.0
        err_rh = ca.fmax(0, rh - 85.0) / 5.0
        cost_temp = 100.0 * err_T**2
        cost_co2 = 30.0 * err_co2**2
        cost_rh = 50.0 * err_rh**2
        cost_energy = 20.0 * uBoil + 10.0 * uLamp + 2.0 * uCO2
        lterm = cost_temp + cost_co2 + cost_rh + cost_energy
        mterm = cost_temp + cost_co2 + cost_rh

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
) -> pd.DataFrame:
    data = collect_rule_based_dataset(
        cfg,
        n_days=n_days,
        start_date=start_date,
        seed=seed,
        noise_scale=noise_scale,
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
    max_solver_failures: int = 3,
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
        rows.append(row)

        obs, _reward, terminated, truncated, _info = env.step(action.astype(np.float32))
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
    checks = [
        ("co2", "dc_uVent", "negative", "ventilation should reduce indoor CO2 gradient"),
        ("rh", "h_uVent", "negative", "ventilation should reduce humidity"),
        ("t_in", "t_uBoil", "positive", "heating should increase or maintain temperature"),
        ("t_in", "S_eff", "positive", "solar gain should increase or maintain temperature"),
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
