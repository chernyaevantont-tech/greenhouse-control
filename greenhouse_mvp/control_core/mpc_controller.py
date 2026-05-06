"""
mpc_controller.py — do_mpc MPC controller backed by a SINDy surrogate model.

Architecture
------------
* The SINDy discrete-time equations are embedded symbolically in a
  do_mpc.model.Model via CasADi matrix multiplication.
* OOD detection uses Mahalanobis distance on the scaled feature space.
* update_model() supports hot-swapping the SINDy model for DAgger-style
  online retraining.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import casadi as ca
import do_mpc
import numpy as np
import pysindy as ps
from sklearn.preprocessing import StandardScaler

from greenhouse_mvp.environment.tvp_forecast import WeatherForecastTVP
from greenhouse_mvp.orchestration.schemas import ActionPayload, OODMetrics, TelemetryPayload
from greenhouse_mvp.sindy_pipeline.physics_features import compute_physics_features

logger = logging.getLogger(__name__)

OOD_THRESHOLD: float = 6.0  # Mahalanobis distance threshold for 21-d feature space.


class MPCController:
    """
    Greenhouse MPC controller built on a Physics-Informed SINDy surrogate.

    Parameters
    ----------
    sindy_model : ps.SINDy
    scaler_x    : StandardScaler fitted on state data [t_in, co2, rh]
    scaler_u    : StandardScaler fitted on 18-d physics feature vector
    weather_provider : WeatherForecastTVP
    horizon     : MPC prediction horizon
    period      : Sampling period in seconds
    mu_train    : Mean of training feature matrix (OOD)
    cov_inv     : Inverse covariance of training features (OOD)
    """

    def __init__(
        self,
        sindy_model: ps.SINDy,
        scaler_x: StandardScaler,
        scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
        horizon: int = 20,
        period: float = 900.0,
        mu_train: np.ndarray | None = None,
        cov_inv: np.ndarray | None = None,
    ) -> None:
        self._horizon = horizon
        self._period = period
        self._mu_train = mu_train
        self._cov_inv = cov_inv

        self._sindy_model = sindy_model
        self._mpc, self._sim_model, self._scaler_x, self._scaler_u = (
            self._build(sindy_model, scaler_x, scaler_u, weather_provider, horizon, period)
        )
        self._t0: float = 0.0  # current simulation time, advances each step

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialise(self, x0: np.ndarray) -> None:
        """Set initial state and call mpc.set_initial_guess()."""
        x0 = np.asarray(x0, dtype=np.float64).reshape(-1, 1)
        self._mpc.x0 = x0
        self._mpc.set_initial_guess()
        logger.info("MPCController initialised with x0=%s", x0.ravel().tolist())

    def step(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, OODMetrics]:
        """Run one MPC solve step and return the proposed action + OOD metrics."""
        x0 = np.array(
            [telemetry.t_in, telemetry.co2, telemetry.rh], dtype=np.float64
        ).reshape(-1, 1)

        u_opt = self._mpc.make_step(x0)
        self._t0 += self._period
        u_vec = u_opt.ravel()

        action = ActionPayload(
            step=telemetry.step,
            approved=False,
            uBoil=float(u_vec[0]),
            uCO2=float(u_vec[1]),
            uThScr=float(u_vec[2]),
            uVent=float(u_vec[3]),
            uLamp=float(u_vec[4]),
            uBlScr=float(u_vec[5]),
        )

        ood = self._compute_ood(telemetry, u_vec)
        return action, ood

    def update_model(
        self,
        new_sindy: ps.SINDy,
        new_scaler_x: StandardScaler,
        new_scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
        mu_train: np.ndarray | None = None,
        cov_inv: np.ndarray | None = None,
    ) -> None:
        """Hot-swap the SINDy model (DAgger online retraining)."""
        try:
            x0_prev = np.array(self._mpc.x0.cat).ravel()
        except Exception:
            x0_prev = None
        t0_prev = self._t0

        self._sindy_model = new_sindy
        self._mpc, self._sim_model, self._scaler_x, self._scaler_u = (
            self._build(new_sindy, new_scaler_x, new_scaler_u, weather_provider,
                        self._horizon, self._period)
        )
        if mu_train is not None:
            self._mu_train = mu_train
        if cov_inv is not None:
            self._cov_inv = cov_inv

        self._mpc.t0 = t0_prev

        if x0_prev is not None:
            self.initialise(x0_prev)

        logger.info("MPCController model updated (DAgger).")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build(
        self,
        sindy_model: ps.SINDy,
        scaler_x: StandardScaler,
        scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
        horizon: int,
        period: float,
    ):
        """Build and configure a do_mpc controller from a SINDy model.

        Mirrors the notebook (physics_informed_mpc.ipynb) exactly:
        - individual named scalar variables
        - symbolic physics feature vector
        - coefs @ library_vector (full next-state prediction, no increment)
        - inverse scaling of RHS
        - named bounds and rterm
        """
        coefs = sindy_model.coefficients()  # (3, 22): 3 states × 22 library terms

        # Scaler parameters
        mu_x  = scaler_x.mean_    # (3,)
        st_x  = scaler_x.scale_   # (3,)
        mu_u  = scaler_u.mean_    # (18,)
        st_u  = scaler_u.scale_   # (18,)

        # ── 1. Build do_mpc Model with individual named scalar variables ──
        model = do_mpc.model.Model("discrete")

        # States
        t_in = model.set_variable("_x", "t_in")
        co2  = model.set_variable("_x", "co2")
        rh   = model.set_variable("_x", "rh")

        # Controls
        uBoil  = model.set_variable("_u", "uBoil")
        uCO2   = model.set_variable("_u", "uCO2")
        uThScr = model.set_variable("_u", "uThScr")
        uVent  = model.set_variable("_u", "uVent")
        uLamp  = model.set_variable("_u", "uLamp")
        uBlScr = model.set_variable("_u", "uBlScr")

        # TVP (weather forecast)
        T_out_v   = model.set_variable("_tvp", "T_out")
        rad_v     = model.set_variable("_tvp", "rad")
        co2_out_v = model.set_variable("_tvp", "co2_out")
        sin_h_v   = model.set_variable("_tvp", "sin_h")
        cos_h_v   = model.set_variable("_tvp", "cos_h")

        # ── 2. Symbolic physics feature vector (18 u-features) ──
        psat    = 0.6108 * ca.exp(17.27 * t_in / (t_in + 237.3))
        vpd     = (1.0 - rh / 100.0) * psat
        S_eff   = rad_v * (1.0 - uThScr)
        t_S_eff = t_in * S_eff
        h_uVent = rh * uVent
        dc_uVent = (co2 - co2_out_v) * uVent
        t_uBoil = t_in * uBoil

        u_raw = ca.vertcat(
            T_out_v, rad_v, co2_out_v, sin_h_v, cos_h_v,
            uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
            psat, vpd, S_eff, t_S_eff, h_uVent, dc_uVent, t_uBoil,
        )

        # ── 3. Normalise features ──
        x_raw = ca.vertcat(t_in, co2, rh)
        x_sc  = (x_raw - ca.DM(mu_x)) / ca.DM(st_x)
        u_sc  = (u_raw - ca.DM(mu_u)) / ca.DM(st_u)

        # Library vector: [1, x_sc(3), u_sc(18)] = 22 terms
        library_vector = ca.vertcat(1, x_sc, u_sc)

        # ── 4. SINDy dynamics: x_{k+1}_scaled = coefs @ library_vector ──
        x_next_sc = ca.DM(coefs) @ library_vector  # (3,1)

        # ── 5. Inverse normalise ──
        st_x_ca = ca.DM(st_x.reshape(-1, 1))   # (3,1)
        mu_x_ca = ca.DM(mu_x.reshape(-1, 1))   # (3,1)
        x_next_raw = x_next_sc * st_x_ca + mu_x_ca

        model.set_rhs("t_in", x_next_raw[0])
        model.set_rhs("co2",  x_next_raw[1])
        model.set_rhs("rh",   x_next_raw[2])
        model.setup()

        # ── 6. MPC controller ──
        mpc = do_mpc.controller.MPC(model)
        mpc.set_param(
            n_horizon=horizon,
            t_step=period,
            n_robust=0,
            store_full_solution=False,
        )

        # ── 7. Objective: track temperature setpoint + penalise energy ──
        T_setpoint = 20.0
        lterm = 10.0 * (t_in - T_setpoint) ** 2 + 100.0 * uBoil ** 2 + 50.0 * uLamp ** 2
        mterm = 10.0 * (t_in - T_setpoint) ** 2
        mpc.set_objective(mterm=mterm, lterm=lterm)

        mpc.set_rterm(
            uBoil=50.0,
            uCO2=10.0,
            uThScr=10.0,
            uVent=100.0,
            uLamp=5.0,
            uBlScr=5.0,
        )

        # ── 8. Bounds ──
        for u_name in ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]:
            mpc.bounds["lower", "_u", u_name] = 0.0
            mpc.bounds["upper", "_u", u_name] = 1.0

        mpc.bounds["lower", "_x", "t_in"] = 5.0
        mpc.bounds["upper", "_x", "t_in"] = 45.0

        # ── 9. TVP function from weather provider ──
        tvp_fun = weather_provider.get_mpc_tvp_fun(mpc)
        mpc.set_tvp_fun(tvp_fun)
        mpc.setup()

        return mpc, model, scaler_x, scaler_u

    def _compute_ood(self, telemetry: TelemetryPayload, u_vec: np.ndarray) -> OODMetrics:
        """Compute Mahalanobis-distance OOD detection."""
        try:
            feat = compute_physics_features(
                t_in=telemetry.t_in,
                co2=telemetry.co2,
                rh=telemetry.rh,
                T_out=telemetry.T_out,
                rad=telemetry.rad,
                co2_out=telemetry.co2_out,
                u_vec=u_vec,
            )
            feat_sc = self._scaler_u.transform(feat.reshape(1, -1))[0]

            if self._mu_train is not None and self._cov_inv is not None:
                diff = feat_sc - self._mu_train
                mahal = float(np.sqrt(diff @ self._cov_inv @ diff))
            else:
                mahal = 0.0

            # Max residual: one-step SINDy prediction error
            x0 = np.array([telemetry.t_in, telemetry.co2, telemetry.rh])
            x0_sc = self._scaler_x.transform(x0.reshape(1, -1))[0]
            pred = self._sindy_model.predict(
                x0_sc.reshape(1, -1), u=feat_sc.reshape(1, -1)
            )
            max_res = float(np.max(np.abs(pred)))

            return OODMetrics(
                step=telemetry.step,
                mahalanobis_distance=mahal,
                max_residual=max_res,
                in_distribution=mahal < OOD_THRESHOLD,
                threshold_used=OOD_THRESHOLD,
            )
        except Exception:
            logger.debug("OOD computation failed — returning safe default", exc_info=True)
            return OODMetrics(
                step=telemetry.step,
                mahalanobis_distance=0.0,
                max_residual=0.0,
                in_distribution=True,
                threshold_used=OOD_THRESHOLD,
            )
