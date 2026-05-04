"""
sindy_fitter.py — Discrete-time Physics-Informed SINDy model fitting.

Formulation
-----------
    x_{k+1} = Ξᵀ · Θ(x_k, u_k)

where Θ = PolynomialLibrary(degree=1, include_bias=True) → 22 terms:
    [1, t_in, co2, rh, T_out, rad, co2_out, sin_h, cos_h,
     uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
     psat, vpd, S_eff, t_S_eff, h_uVent, dc_uVent, t_uBoil]

Ξ has shape (3 equations, 22 terms).
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pysindy as ps
from sklearn.preprocessing import StandardScaler

from greenhouse_mvp.sindy_pipeline.physics_features import (
    FEATURE_NAMES,
    check_condition_number,
)

logger = logging.getLogger(__name__)


class SINDyFitter:
    """
    Fit a discrete-time next-step SINDy model on greenhouse data.

    Attributes
    ----------
    DEFAULT_THR:
        STLSQ sparsity threshold.
    DEFAULT_ALPHA:
        STLSQ ridge regularisation.
    """

    DEFAULT_THR: float = 0.05
    DEFAULT_ALPHA: float = 0.01

    def __init__(
        self,
        threshold: float | None = None,
        alpha: float | None = None,
    ) -> None:
        self._threshold = threshold if threshold is not None else self.DEFAULT_THR
        self._alpha = alpha if alpha is not None else self.DEFAULT_ALPHA

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(
        self,
        states: np.ndarray,        # (N, 3) raw  [t_in, co2, rh]
        actions_phys: np.ndarray,  # (N, 18) raw physics features
        period: float = 900.0,
    ) -> tuple[ps.SINDy, StandardScaler, StandardScaler]:
        """
        Fit a discrete-time SINDy model and return model + scalers.

        Parameters
        ----------
        states:
            Raw state observations, shape (N, 3).
        actions_phys:
            Pre-computed physics feature vector (from
            ``compute_physics_features``), shape (N, 18).
        period:
            Sampling period in seconds (dt for the discrete model).

        Returns
        -------
        (sindy_model, scaler_states, scaler_actions)
        """
        states = np.asarray(states, dtype=np.float64)
        actions_phys = np.asarray(actions_phys, dtype=np.float64)

        if states.shape[1] != 3:
            raise ValueError(f"states must have 3 columns, got {states.shape[1]}")
        if actions_phys.shape[1] != 18:
            raise ValueError(
                f"actions_phys must have 18 columns, got {actions_phys.shape[1]}"
            )
        if states.shape[0] != actions_phys.shape[0]:
            raise ValueError("states and actions_phys must have the same number of rows")
        if states.shape[0] < 3:
            raise ValueError("Need at least 3 data points to form (x_in, x_out) pairs")

        # 1. Scale states and action features separately
        scaler_x = StandardScaler()
        scaler_u = StandardScaler()
        scaled_states = scaler_x.fit_transform(states)
        scaled_actions = scaler_u.fit_transform(actions_phys)

        # 2. Build (x_in, u_in, x_out) pairs — use ALL data, matching notebook Iteration 0.
        x_in = scaled_states[:-1]   # (N-1, 3)
        u_in = scaled_actions[:-1]  # (N-1, 18)
        x_out = scaled_states[1:]   # (N-1, 3)

        logger.info("SINDyFitter: fitting on %d samples (no train/val split).", len(x_in))

        # 3. Condition check
        combined = np.hstack([x_in, u_in])  # (N-1, 21) — also used for OOD stats
        kappa = check_condition_number(combined, context="SINDyFitter")
        logger.info("Feature matrix condition number κ=%.2f", kappa)

        # 4. Fit on the full dataset (identical to notebook Iteration 0)
        model = ps.SINDy(
            optimizer=ps.STLSQ(
                threshold=self._threshold,
                alpha=self._alpha,
                max_iter=200,
                normalize_columns=False,
            ),
            feature_library=ps.PolynomialLibrary(degree=1, include_bias=True),
            feature_names=FEATURE_NAMES,
        )
        model.fit(
            x_in,
            u=u_in,
            x_dot=x_out,
            t=period,
        )

        logger.info(
            "SINDy fit complete. Non-zero coefficients per equation: %s",
            [int(np.count_nonzero(row)) for row in model.coefficients()],
        )

        # 5. Compute full-dataset statistics for OOD detection
        self._mu_train = combined.mean(axis=0)       # (21,)
        self._cov_inv = np.linalg.pinv(np.cov(combined.T))  # (21, 21)

        return model, scaler_x, scaler_u

    @property
    def mu_train(self) -> np.ndarray:
        """Mean of the training feature matrix (post-scaling). Available after fit()."""
        return self._mu_train  # type: ignore[return-value]

    @property
    def cov_inv(self) -> np.ndarray:
        """Inverse covariance of training features. Available after fit()."""
        return self._cov_inv  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def save(
    path: str,
    model: ps.SINDy,
    scaler_x: StandardScaler,
    scaler_u: StandardScaler,
    mu_train: np.ndarray | None = None,
    cov_inv: np.ndarray | None = None,
    x_in_raw: np.ndarray | None = None,
    u_in_raw: np.ndarray | None = None,
    x_out_raw: np.ndarray | None = None,
) -> None:
    """
    Pickle the SINDy model and scalers (plus optional OOD statistics) to *path*.

    The file contains a dict with keys:
    ``model``, ``scaler_x``, ``scaler_u``, ``mu_train``, ``cov_inv``,
    ``x_in_raw``, ``u_in_raw``, ``x_out_raw`` (raw training arrays for DAgger seeding).
    """
    payload = {
        "model": model,
        "scaler_x": scaler_x,
        "scaler_u": scaler_u,
        "mu_train": mu_train,
        "cov_inv": cov_inv,
        "x_in_raw": x_in_raw,
        "u_in_raw": u_in_raw,
        "x_out_raw": x_out_raw,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("SINDy model saved to %s", path)


def load(
    path: str,
) -> tuple[ps.SINDy, StandardScaler, StandardScaler, np.ndarray | None, np.ndarray | None]:
    """
    Load a SINDy model and scalers from a pickle file.

    Returns
    -------
    (model, scaler_x, scaler_u, mu_train, cov_inv)
    ``mu_train`` and ``cov_inv`` may be ``None`` if the file was saved without them.
    """
    with open(path, "rb") as f:
        payload = pickle.load(f)  # noqa: S301 — trusted internal files only
    logger.info("SINDy model loaded from %s", path)
    return (
        payload["model"],
        payload["scaler_x"],
        payload["scaler_u"],
        payload.get("mu_train"),
        payload.get("cov_inv"),
    )
