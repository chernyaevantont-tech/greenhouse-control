"""
mpc_controller.py — do_mpc MPC controller backed by a SINDy surrogate model.

Architecture
------------
* The SINDy discrete-time equations are embedded symbolically in a
  ``do_mpc.model.Model('discrete')`` via CasADi matrix multiplication.
* The MPC controller solves at each step and publishes the proposed action
  to ``greenhouse/action/proposed`` via MQTT.
* OOD detection uses Mahalanobis distance on the scaled feature space.
* ``update_model()`` supports hot-swapping the SINDy model for DAgger-style
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
from greenhouse_mvp.orchestration.mqtt_bus import MQTTBus
from greenhouse_mvp.orchestration.schemas import ActionPayload, OODMetrics, TelemetryPayload
from greenhouse_mvp.sindy_pipeline.physics_features import compute_physics_features

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

OOD_THRESHOLD: float = 6.0  # Mahalanobis distance threshold for 21-d feature space.
# For chi(21), the 99th percentile ≈ 6.1 — values above this indicate genuine anomalies.


class MPCController:
    """
    Greenhouse MPC controller built on a Physics-Informed SINDy surrogate.

    Parameters
    ----------
    sindy_model:
        Fitted ``ps.SINDy`` model.
    scaler_x:
        StandardScaler fitted on state data [t_in, co2, rh].
    scaler_u:
        StandardScaler fitted on 18-d physics feature vector.
    weather_provider:
        Pre-built weather forecast TVP for the episode.
    bus:
        MQTT bus for publishing proposed actions and OOD metrics.
    horizon:
        MPC prediction horizon (number of steps).
    period:
        Sampling period in seconds.
    mu_train:
        Mean of the training feature matrix used for OOD (optional).
    cov_inv:
        Inverse covariance of training features used for OOD (optional).
    """

    def __init__(
        self,
        sindy_model: ps.SINDy,
        scaler_x: StandardScaler,
        scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
        bus: MQTTBus,
        horizon: int = 20,
        period: float = 900.0,
        mu_train: np.ndarray | None = None,
        cov_inv: np.ndarray | None = None,
        auto_subscribe: bool = True,
    ) -> None:
        self._bus = bus
        self._horizon = horizon
        self._period = period
        self._mu_train = mu_train
        self._cov_inv = cov_inv

        self._sindy_model = sindy_model
        self._mpc, self._sim_model, self._scaler_x, self._scaler_u = (
            self._build(sindy_model, scaler_x, scaler_u, weather_provider, horizon, period)
        )
        self._t0: float = 0.0  # current simulation time, advances each step

        # Subscribe to telemetry (disabled when managed externally, e.g. from orchestration)
        if auto_subscribe:
            bus.subscribe(
                topic="greenhouse/telemetry",
                schema=TelemetryPayload,
                handler=self._on_telemetry,
                qos=1,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialise(self, x0: np.ndarray) -> None:
        """
        Set the initial state and call ``mpc.set_initial_guess()``.

        Parameters
        ----------
        x0:
            Initial state vector [t_in, co2, rh], shape (3,).
        """
        x0 = np.asarray(x0, dtype=np.float64).reshape(-1, 1)
        self._mpc.x0 = x0
        self._mpc.set_initial_guess()
        logger.info("MPCController initialised with x0=%s", x0.ravel().tolist())

    def step(self, telemetry: TelemetryPayload) -> tuple[ActionPayload, OODMetrics]:
        """
        Run one MPC solve step and return the proposed action + OOD metrics.

        Parameters
        ----------
        telemetry:
            Current telemetry from the simulation.

        Returns
        -------
        (ActionPayload, OODMetrics)
        """
        x0 = np.array(
            [telemetry.t_in, telemetry.co2, telemetry.rh], dtype=np.float64
        ).reshape(-1, 1)

        u_opt = self._mpc.make_step(x0)   # shape (6, 1)
        self._t0 += self._period           # advance internal time tracker
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

        self._bus.publish("greenhouse/action/proposed", action)
        self._bus.publish("greenhouse/ood/metrics", ood)

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
        """
        Hot-swap the SINDy model (DAgger online retraining).

        Rebuilds the do_mpc controller with new equations. The current x0
        is preserved and re-applied after the rebuild.
        """
        # Preserve current state and time
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

        # Restore simulation time so TVP forecast stays aligned
        self._mpc.t0 = t0_prev

        if x0_prev is not None:
            self.initialise(x0_prev)

        logger.info("MPCController model updated (DAgger).")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_telemetry(self, payload: TelemetryPayload) -> None:
        """MQTT callback: run one MPC step when telemetry arrives."""
        try:
            self.step(payload)
        except Exception:
            logger.exception("MPCController.step() raised an exception")

    def _compute_ood(
        self,
        telemetry: TelemetryPayload,
        u_vec: np.ndarray,
    ) -> OODMetrics:
        """Compute Mahalanobis distance OOD metrics."""
        if self._mu_train is None or self._cov_inv is None:
            return OODMetrics(
                step=telemetry.step,
                mahalanobis_distance=0.0,
                max_residual=0.0,
                in_distribution=True,
                threshold_used=OOD_THRESHOLD,
            )

        # Build the physics feature vector for current state+action
        states_1 = np.array([[telemetry.t_in, telemetry.co2, telemetry.rh]])
        weather_1 = np.array([[telemetry.T_out, telemetry.rad, telemetry.co2_out]])
        time_1 = np.array([[telemetry.sin_h, telemetry.cos_h]])
        actions_1 = u_vec.reshape(1, -1)  # (1, 6)

        phys = compute_physics_features(states_1, weather_1, time_1, actions_1)

        x_cur = self._scaler_x.transform(states_1)[0]   # (3,)
        u_cur = self._scaler_u.transform(phys)[0]        # (18,)
        feat = np.concatenate([x_cur, u_cur])             # (21,)

        delta = feat - self._mu_train
        dist = float(np.sqrt(delta @ self._cov_inv @ delta))
        in_dist = dist < OOD_THRESHOLD

        # One-step SINDy residual on scaled inputs (simple proxy)
        max_residual = float(np.max(np.abs(delta)))

        return OODMetrics(
            step=telemetry.step,
            mahalanobis_distance=dist,
            max_residual=max_residual,
            in_distribution=in_dist,
            threshold_used=OOD_THRESHOLD,
        )

    # ------------------------------------------------------------------
    # Static builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build(
        sindy_model: ps.SINDy,
        scaler_x: StandardScaler,
        scaler_u: StandardScaler,
        weather_provider: WeatherForecastTVP,
        horizon: int,
        period: float,
    ) -> tuple[do_mpc.controller.MPC, do_mpc.model.Model, StandardScaler, StandardScaler]:
        """Build a fresh do_mpc model + controller from a SINDy model."""

        # ------ Extract scaler constants ------
        mu_x = ca.DM(scaler_x.mean_.tolist())         # (3,)
        sigma_x = ca.DM(scaler_x.scale_.tolist())     # (3,)
        mu_u = ca.DM(scaler_u.mean_.tolist())         # (18,)
        sigma_u = ca.DM(scaler_u.scale_.tolist())     # (18,)

        # SINDy coefficient matrix Ξ, shape (3, 22)
        coefs = ca.DM(sindy_model.coefficients())

        # ------ Build do_mpc discrete model ------
        model = do_mpc.model.Model("discrete")

        # State variables
        t_in = model.set_variable("_x", "t_in")
        co2 = model.set_variable("_x", "co2")
        rh = model.set_variable("_x", "rh")

        # Control variables
        uBoil = model.set_variable("_u", "uBoil")
        uCO2 = model.set_variable("_u", "uCO2")
        uThScr = model.set_variable("_u", "uThScr")
        uVent = model.set_variable("_u", "uVent")
        uLamp = model.set_variable("_u", "uLamp")
        uBlScr = model.set_variable("_u", "uBlScr")

        # Time-varying parameters (weather forecast)
        T_out = model.set_variable("_tvp", "T_out")
        rad = model.set_variable("_tvp", "rad")
        co2_out = model.set_variable("_tvp", "co2_out")
        sin_h = model.set_variable("_tvp", "sin_h")
        cos_h = model.set_variable("_tvp", "cos_h")

        # ------ Symbolic physics features (CasADi) ------
        psat = 0.6108 * ca.exp(17.27 * t_in / (t_in + 237.3))
        vpd = (1.0 - rh / 100.0) * psat
        S_eff = rad * (1.0 - uThScr)

        u_raw = ca.vertcat(
            T_out, rad, co2_out, sin_h, cos_h,
            uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
            psat, vpd, S_eff,
            t_in * S_eff,
            rh * uVent,
            (co2 - co2_out) * uVent,
            t_in * uBoil,
        )  # (18,)

        # ------ Normalisation (embedded in model) ------
        x_sym = ca.vertcat(t_in, co2, rh)
        x_scaled = (x_sym - mu_x) / sigma_x          # (3,)
        u_scaled = (u_raw - mu_u) / sigma_u           # (18,)

        # ------ SINDy prediction ------
        # bias term first: theta = [1; x_scaled; u_scaled]  (22,)
        theta = ca.vertcat(1.0, x_scaled, u_scaled)   # (22,)
        x_next_scaled = coefs @ theta                  # (3,)
        x_next_raw = x_next_scaled * sigma_x + mu_x   # (3,)

        model.set_rhs("t_in", x_next_raw[0])
        model.set_rhs("co2", x_next_raw[1])
        model.set_rhs("rh", x_next_raw[2])
        model.setup()

        # ------ MPC controller ------
        mpc = do_mpc.controller.MPC(model)
        setup_params = {
            "n_horizon": horizon,
            "t_step": period,
            "state_discretization": "discrete",
            "store_full_solution": False,
            "nlpsol_opts": {
                "ipopt.print_level": 0,
                "ipopt.sb": "yes",
                "print_time": 0,
            },
        }
        mpc.set_param(**setup_params)

        # ------ TVP function ------
        tvp_fun = weather_provider.get_mpc_tvp_fun(mpc)
        mpc.set_tvp_fun(tvp_fun)

        # ------ Cost function ------
        # Re-reference model variables for cost (needed after model.setup())
        t_in_c = model.x["t_in"]
        co2_c = model.x["co2"]
        rh_c = model.x["rh"]
        uBoil_c = model.u["uBoil"]
        uCO2_c = model.u["uCO2"]
        uLamp_c = model.u["uLamp"]

        err_T = (t_in_c - 20.0) / 5.0
        err_co2 = (co2_c - 800.0) / 200.0
        err_rh = ca.fmax(0, rh_c - 85.0) / 5.0

        lterm = (
            100.0 * err_T ** 2
            + 30.0 * err_co2 ** 2
            + 50.0 * err_rh ** 2
            + 20.0 * uBoil_c
            + 10.0 * uLamp_c
            + 2.0 * uCO2_c
        )
        mterm = 100.0 * err_T ** 2 + 30.0 * err_co2 ** 2 + 50.0 * err_rh ** 2

        mpc.set_objective(mterm=mterm, lterm=lterm)

        # Anti-chattering R terms
        mpc.set_rterm(
            uBoil=10.0,
            uCO2=5.0,
            uThScr=100.0,
            uVent=50.0,
            uLamp=1.0,
            uBlScr=1.0,
        )

        # ------ Constraints ------
        # Actuator bounds
        for u_name in ["uBoil", "uCO2", "uThScr", "uLamp", "uBlScr"]:
            mpc.bounds["lower", "_u", u_name] = 0.0
            mpc.bounds["upper", "_u", u_name] = 1.0

        # Ventilation: winter frost protection
        mpc.bounds["lower", "_u", "uVent"] = 0.0
        mpc.bounds["upper", "_u", "uVent"] = 0.4

        # State bounds (hard frost / heat damage)
        mpc.bounds["lower", "_x", "t_in"] = 12.0
        mpc.bounds["upper", "_x", "t_in"] = 35.0

        mpc.setup()

        return mpc, model, scaler_x, scaler_u


if __name__ == "__main__":
    import os
    import pickle
    import signal
    import threading

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from greenhouse_mvp.environment.tvp_forecast import WeatherForecastTVP
    from greenhouse_mvp.orchestration.mqtt_bus import MQTTBus

    _host = os.environ.get("MQTT_HOST", "localhost")
    _port = int(os.environ.get("MQTT_PORT", "1883"))
    _model_path = os.environ.get("SINDY_MODEL_PATH", "/app/models/sindy_model.pkl")
    _horizon = int(os.environ.get("MPC_HORIZON", "20"))
    _start_date = os.environ.get("START_DATE", "2010-02-28")
    _n_days = int(os.environ.get("N_DAYS", "60"))
    _period = int(os.environ.get("PERIOD", "900"))

    with open(_model_path, "rb") as _fh:
        _bundle = pickle.load(_fh)

    _weather = WeatherForecastTVP(
        start_date=_start_date,
        n_days=_n_days,
        horizon=_horizon,
        period=_period,
    )

    _bus = MQTTBus(host=_host, port=_port)
    _bus.loop_start()

    _ctrl = MPCController(
        sindy_model=_bundle["model"],
        scaler_x=_bundle["scaler_x"],
        scaler_u=_bundle["scaler_u"],
        weather_provider=_weather,
        bus=_bus,
        horizon=_horizon,
        mu_train=_bundle.get("mu_train"),
        cov_inv=_bundle.get("cov_inv"),
        auto_subscribe=True,
    )

    logger.info("control_core: MPCController running, waiting for telemetry...")

    _stop = threading.Event()

    def _shutdown(*_: object) -> None:
        logger.info("control_core: shutdown signal received.")
        _stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    _stop.wait()
    _bus.loop_stop()
