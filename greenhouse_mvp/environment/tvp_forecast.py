"""
WeatherForecastTVP — pre-harvests weather data from a shadow episode of the
GreenLight gym environment and exposes it as a do-mpc TVP function.

This class is used by the MPC controller to provide a horizon-step lookahead
of external disturbances (T_out, rad, co2_out, sin_h, cos_h).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

import gl_gym  # noqa: F401 — registers gl_gym namespace with gymnasium
import gymnasium as gym
import numpy as np

if TYPE_CHECKING:
    import do_mpc

logger = logging.getLogger(__name__)


class WeatherForecastTVP:
    """
    Pre-computes a full weather trajectory by running a **shadow episode**
    (zero actions) of the same env used by ``SimAdapter``.

    The shadow env is separate from the main simulation env and is disposed
    after construction.

    Parameters
    ----------
    env_id:
        Gymnasium environment ID (must match ``SimAdapter``).
    start_date:
        Episode start date string, e.g. ``"2010-02-28"``.
    n_days:
        Episode length in days.
    horizon:
        MPC prediction horizon (number of steps).
    period:
        Step duration in seconds (default 900 s = 15 min).
    """

    def __init__(
        self,
        env_id: str = "gl_gym/GreenLightTomato-v0",
        start_date: str = "2010-02-28",
        n_days: int = 60,
        horizon: int = 6,
        period: int = 900,
    ) -> None:
        self._period = period
        self._horizon = horizon

        total_steps = int(n_days * 86400 / period) + horizon
        logger.info(
            "WeatherForecastTVP: running shadow episode (%d steps)…", total_steps
        )

        env = gym.make(
            env_id,
            normalize_actions=False,
            observation_modules=[
                "IndoorClimateObservations",
                "WeatherObservations",
                "BasicCropObservations",
            ],
            season_length=n_days,
        )
        obs, _ = env.reset(options={"start_date": start_date}, seed=42)
        zero_action = np.zeros(6, dtype=np.float32)

        T_out_list: list[float] = []
        rad_list: list[float] = []
        co2_out_list: list[float] = []
        sin_h_list: list[float] = []
        cos_h_list: list[float] = []

        for step in range(total_steps):
            weather = obs["WeatherObservations"]
            hour_of_day = (step * period / 3600.0) % 24.0

            T_out_list.append(float(weather[1]))
            rad_list.append(float(weather[0]))
            co2_out_list.append(float(weather[3]))
            sin_h_list.append(float(np.sin(2 * np.pi * hour_of_day / 24.0)))
            cos_h_list.append(float(np.cos(2 * np.pi * hour_of_day / 24.0)))

            obs, _reward, terminated, truncated, _info = env.step(zero_action)
            if terminated or truncated:
                logger.debug("Shadow episode ended at step %d.", step)
                break

        env.close()

        self._T_out = np.array(T_out_list, dtype=np.float64)
        self._rad = np.array(rad_list, dtype=np.float64)
        self._co2_out = np.array(co2_out_list, dtype=np.float64)
        self._sin_h = np.array(sin_h_list, dtype=np.float64)
        self._cos_h = np.array(cos_h_list, dtype=np.float64)

        logger.info(
            "WeatherForecastTVP: harvested %d steps of weather data.",
            len(self._T_out),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_mpc_tvp_fun(self, mpc: "do_mpc.controller.MPC") -> Callable:
        """
        Return a TVP function compatible with ``do_mpc.controller.MPC``.

        The returned callable accepts the current simulation time ``t_now``
        (in seconds from episode start) and fills the MPC TVP template with
        the appropriate forecast window.

        Parameters
        ----------
        mpc:
            A configured ``do_mpc.controller.MPC`` instance whose TVP
            template has been set up with fields:
            ``T_out``, ``rad``, ``co2_out``, ``sin_h``, ``cos_h``.

        Returns
        -------
        Callable[[float], do_mpc.TVPTemplate]
        """
        tvp_template = mpc.get_tvp_template()
        horizon = self._horizon
        n = len(self._T_out)

        T_out = self._T_out
        rad = self._rad
        co2_out = self._co2_out
        sin_h = self._sin_h
        cos_h = self._cos_h
        period = self._period

        def tvp_fun(t_now: float):  # type: ignore[return]
            k_start = int(t_now / period)
            for k in range(horizon):
                idx = min(k_start + k, n - 1)
                tvp_template["_tvp", k, "T_out"] = T_out[idx]
                tvp_template["_tvp", k, "rad"] = rad[idx]
                tvp_template["_tvp", k, "co2_out"] = co2_out[idx]
                tvp_template["_tvp", k, "sin_h"] = sin_h[idx]
                tvp_template["_tvp", k, "cos_h"] = cos_h[idx]
            return tvp_template

        return tvp_fun

    # ------------------------------------------------------------------
    # Raw array access (useful for plotting / debugging)
    # ------------------------------------------------------------------

    @property
    def T_out(self) -> np.ndarray:
        return self._T_out

    @property
    def rad(self) -> np.ndarray:
        return self._rad

    @property
    def co2_out(self) -> np.ndarray:
        return self._co2_out

    @property
    def sin_h(self) -> np.ndarray:
        return self._sin_h

    @property
    def cos_h(self) -> np.ndarray:
        return self._cos_h
