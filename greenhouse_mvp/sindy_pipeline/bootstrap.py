"""
bootstrap.py — Auto-build a SINDy model from a fast headless simulation.

Run this ONCE before control_core / orchestration start.  If the model
file already exists the script exits immediately (idempotent).

Steps
-----
1. Run a *headless* (no MQTT) gl_gym episode for ``season_length`` days using
   a simple randomised exploration policy to cover the action space.
2. Extract (states, weather, time, actions) at every step.
3. Compute physics features and fit SINDy via ``SINDyFitter``.
4. Persist the model bundle to ``model_path``.

Usage
-----
    python -m greenhouse_mvp.sindy_pipeline.bootstrap

Environment variables (all optional):
    MODEL_PATH        path to write the pkl   (default /app/models/sindy_model.pkl)
    SEASON_LENGTH     simulation days          (default 30)
    PERIOD            timestep seconds         (default 900)
    SINDY_THRESHOLD   STLSQ sparsity thr       (default 0.05)
    SINDY_ALPHA       STLSQ ridge alpha        (default 0.01)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Exploration noise parameters (match the notebook: NOISE_SCALE=0.1, NOISE_PERIOD=5)
_NOISE_SCALE: float = 0.1
_NOISE_PERIOD: int = 5


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _build_step_context(env):
    """Build a StepContext from a live gl_gym environment (for RuleBasedController)."""
    from gl_gym.core.types import StepContext
    raw = env.unwrapped
    return StepContext(
        t=raw.timestep, dt=raw.dt, Np=raw.Np,
        x_prev=raw.x_prev, x=raw.x, u=raw.u, p=raw.p,
        d=raw.weather_data,
        hour_of_day=raw.hour_of_day, day_of_year=raw.day_of_year,
    )


def collect_data(
    season_length: int = 30,
    period: int = 900,
    seed: int = 42,
    start_date: str = "2010-02-28",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Run a headless gl_gym episode and return raw arrays.

    Uses RuleBasedController (same as the notebook) with small Gaussian noise
    (NOISE_SCALE=0.1, NOISE_PERIOD=5) for action-space coverage.

    Returns
    -------
    states       (N, 3)   [t_in, co2, rh]
    weather      (N, 3)   [T_out, rad, co2_out]
    time_enc     (N, 2)   [sin_h, cos_h]
    actions      (N, 6)   [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
    """
    import math

    import gl_gym  # noqa: F401 — registers namespace
    import gymnasium as gym
    from gl_gym.components.rule_based import RuleBasedController

    logger.info(
        "bootstrap: collecting data — season_length=%d days, period=%ds, start_date=%s …",
        season_length, period, start_date,
    )

    env = gym.make(
        "gl_gym/GreenLightTomato-v0",
        normalize_actions=False,
        observation_modules=[
            "IndoorClimateObservations",
            "WeatherObservations",
            "BasicCropObservations",
        ],
        season_length=season_length,
    )
    obs_dict, _ = env.reset(options={"start_date": start_date}, seed=seed)

    controller = RuleBasedController(
        lamps_on=0, lamps_off=18, lamps_day_start=-1, lamps_day_stop=366,
        lamps_off_sun=400, lamp_rad_sum_limit=10,
        temp_setpoint_day=19.5, temp_setpoint_night=16.5,
        heat_correction=0, heat_deadzone=5,
        co2_day=800, vent_heat_Pband=4, rh_max=85,
        mech_dehumid_Pband=2, vent_rh_Pband=5,
        t_vent_off=1, vent_cold_Pband=-1,
        thScrSpDay=5, thScrSpNight=10, thScrPband=-1, thScrDeadZone=4,
        thScrRh=-2, thScrRhPband=2,
        lampExtraHeat=2, blScrExtraRh=100, rhMax=85,
        tHeatBand=-1, co2Band=-100, useBlScr=1,
    )

    rng = np.random.default_rng(seed)
    steps_per_day = int(86400 / period)
    total_steps = season_length * steps_per_day

    states_list:  list[np.ndarray] = []
    weather_list: list[np.ndarray] = []
    time_list:    list[np.ndarray] = []
    action_list:  list[np.ndarray] = []

    noise = np.zeros(6, dtype=np.float64)
    noise_countdown = 0

    for step in range(total_steps):
        indoor  = obs_dict["IndoorClimateObservations"]
        weather = obs_dict["WeatherObservations"]

        t_in    = float(indoor[1])
        co2     = float(indoor[0])
        rh      = float(indoor[2])
        T_out   = float(weather[1])
        rad     = float(weather[0])
        co2_out = float(weather[3]) if len(weather) > 3 else 410.0

        hour  = (step % steps_per_day) * period / 3600.0
        sin_h = math.sin(2 * math.pi * hour / 24.0)
        cos_h = math.cos(2 * math.pi * hour / 24.0)

        # Rule-based base action + periodic Gaussian noise for coverage
        ctx = _build_step_context(env)
        base_action = controller.predict(ctx).astype(np.float64)
        if noise_countdown <= 0:
            noise = rng.normal(0.0, _NOISE_SCALE, size=6)
            noise_countdown = _NOISE_PERIOD
        noise_countdown -= 1
        action = np.clip(base_action + noise, 0.0, 1.0).astype(np.float32)

        states_list.append([t_in, co2, rh])
        weather_list.append([T_out, rad, co2_out])
        time_list.append([sin_h, cos_h])
        action_list.append(action.tolist())

        obs_dict, _reward, terminated, truncated, _info = env.step(action)

        if terminated or truncated:
            logger.info("bootstrap: episode ended at step %d / %d", step + 1, total_steps)
            break

        if (step + 1) % steps_per_day == 0:
            logger.info(
                "bootstrap: collected %d / %d steps (day %d / %d)",
                step + 1, total_steps,
                (step + 1) // steps_per_day, season_length,
            )

    env.close()

    states   = np.array(states_list,  dtype=np.float64)
    weather  = np.array(weather_list, dtype=np.float64)
    time_enc = np.array(time_list,    dtype=np.float64)
    actions  = np.array(action_list,  dtype=np.float64)

    logger.info(
        "bootstrap: collected %d steps. states shape=%s",
        len(states_list), states.shape,
    )
    return states, weather, time_enc, actions


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_bootstrap(
    model_path: str,
    season_length: int = 30,
    period: int = 900,
    start_date: str = "2010-02-28",
) -> None:
    if Path(model_path).exists():
        logger.info("bootstrap: model already exists at %s — skipping.", model_path)
        return

    from greenhouse_mvp.sindy_pipeline.physics_features import compute_physics_features
    from greenhouse_mvp.sindy_pipeline.sindy_fitter import SINDyFitter, save

    states, weather, time_enc, actions = collect_data(
        season_length=season_length,
        period=period,
        start_date=start_date,
    )

    logger.info("bootstrap: computing physics features …")
    phys_features = compute_physics_features(states, weather, time_enc, actions)

    logger.info("bootstrap: fitting SINDy …")
    threshold = float(os.environ.get("SINDY_THRESHOLD", "0.05"))
    alpha     = float(os.environ.get("SINDY_ALPHA",     "0.01"))
    fitter    = SINDyFitter(threshold=threshold, alpha=alpha)
    model, scaler_x, scaler_u = fitter.fit(states, phys_features, period=float(period))

    save(
        model_path,
        model=model,
        scaler_x=scaler_x,
        scaler_u=scaler_u,
        mu_train=fitter.mu_train,
        cov_inv=fitter.cov_inv,
        x_in_raw=states[:-1],
        u_in_raw=phys_features[:-1],
        x_out_raw=states[1:],
    )
    logger.info("bootstrap: model saved to %s ✓", model_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    _model_path    = os.environ.get("MODEL_PATH",     "/app/models/sindy_model.pkl")
    _season_length = int(os.environ.get("SEASON_LENGTH", "60"))
    _period        = int(os.environ.get("PERIOD",        "900"))
    _start_date    = os.environ.get("START_DATE",       "2010-02-28")

    run_bootstrap(
        model_path=_model_path,
        season_length=_season_length,
        period=_period,
        start_date=_start_date,
    )
