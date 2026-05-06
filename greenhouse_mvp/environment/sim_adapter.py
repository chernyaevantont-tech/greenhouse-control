"""
sim_adapter.py — Utility functions for converting gym observations to/from
TelemetryPayload and ActionPayload.

The simulation loop is now managed by greenhouse_mvp.api.simulation_runner.
"""

from __future__ import annotations

import numpy as np

from greenhouse_mvp.orchestration.schemas import ActionPayload, TelemetryPayload


def obs_to_telemetry(obs: dict, step: int, period: int) -> TelemetryPayload:
    """
    Map a raw GreenLight gym observation dict to a TelemetryPayload.

    Index mapping (verified against GreenLight notebook):
      IndoorClimateObservations : [0]=co2_ppm, [1]=t_in_C, [2]=rh_%
      WeatherObservations       : [0]=rad_W/m2, [1]=T_out_C, [2]=?, [3]=co2_out_ppm
    """
    indoor = obs["IndoorClimateObservations"]
    weather = obs["WeatherObservations"]

    hour_of_day = (step * period / 3600.0) % 24.0

    return TelemetryPayload(
        step=step,
        timestamp_sim=float(step * period),
        t_in=float(indoor[1]),
        co2=float(indoor[0]),
        rh=float(indoor[2]),
        T_out=float(weather[1]),
        rad=float(weather[0]),
        co2_out=float(weather[3]),
        sin_h=float(np.sin(2 * np.pi * hour_of_day / 24.0)),
        cos_h=float(np.cos(2 * np.pi * hour_of_day / 24.0)),
    )


def action_to_array(action: ActionPayload) -> np.ndarray:
    """Convert ActionPayload to a float32 numpy array for env.step()."""
    return np.array(
        [action.uBoil, action.uCO2, action.uThScr, action.uVent, action.uLamp, action.uBlScr],
        dtype=np.float32,
    )


# Minimal safe action: heating 30%, thermal screen closed, everything else off.
SAFE_FALLBACK_ACTION = np.array([0.3, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)
