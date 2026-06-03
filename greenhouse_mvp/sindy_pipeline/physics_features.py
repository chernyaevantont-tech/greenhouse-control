"""
physics_features.py — Physics-informed feature engineering for SINDy.

Computes non-linear physics terms and cross-terms from raw state/action/weather
arrays before they are fed to the SINDy library.

Feature vector layout (18 columns):
    [T_out, rad, co2_out, sin_h, cos_h,
     uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
     psat, vpd, S_eff,
     t_S_eff, h_uVent, dc_uVent, t_uBoil]

Note: states (t_in, co2, rh) are NOT included here — they are the *x* side.
FEATURE_NAMES covers the full state+action feature space used internally by
SINDy (21 columns: 3 states + 18 u-features), but this function only returns
the 18 u-features.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature name constants
# ---------------------------------------------------------------------------

# State names (x side of SINDy)
STATE_NAMES: list[str] = ["t_in", "co2", "rh"]

# Control/disturbance feature names (u side of SINDy), 18 total
ACTION_FEATURE_NAMES: list[str] = [
    "T_out", "rad", "co2_out", "sin_h", "cos_h",      # 5 external
    "uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr",  # 6 actuators
    "psat", "vpd", "S_eff",                             # 3 physics nonlinear
    "t_S_eff", "h_uVent", "dc_uVent", "t_uBoil",        # 4 cross-terms
]

# Full feature list used by SINDyFitter (states first, then u-features)
FEATURE_NAMES: list[str] = STATE_NAMES + ACTION_FEATURE_NAMES

# Multicollinearity threshold constants
KAPPA_WARN = 1_000.0
KAPPA_MAX = 10_000.0


def compute_physics_features(
    states_arr: np.ndarray,       # (N, 3)  [t_in, co2, rh]
    weather_arr: np.ndarray,      # (N, 3)  [T_out, rad, co2_out]
    time_enc_arr: np.ndarray,     # (N, 2)  [sin_h, cos_h]
    actions_raw_arr: np.ndarray,  # (N, 6)  [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr]
) -> np.ndarray:                  # (N, 18)
    """
    Pure-NumPy computation of the full physics feature vector (u side).

    Parameters
    ----------
    states_arr:
        Raw state observations, shape (N, 3): [t_in, co2, rh].
    weather_arr:
        External weather observations, shape (N, 3): [T_out, rad, co2_out].
    time_enc_arr:
        Cyclic time encoding, shape (N, 2): [sin_h, cos_h].
    actions_raw_arr:
        Raw actuator signals in [0, 1], shape (N, 6):
        [uBoil, uCO2, uThScr, uVent, uLamp, uBlScr].

    Returns
    -------
    np.ndarray of shape (N, 18) — the physics feature vector.
    """
    states_arr = np.asarray(states_arr, dtype=np.float64)
    weather_arr = np.asarray(weather_arr, dtype=np.float64)
    time_enc_arr = np.asarray(time_enc_arr, dtype=np.float64)
    actions_raw_arr = np.asarray(actions_raw_arr, dtype=np.float64)

    t_in = states_arr[:, 0]
    co2 = states_arr[:, 1]
    rh = states_arr[:, 2]

    T_out = weather_arr[:, 0]
    rad = weather_arr[:, 1]
    co2_out = weather_arr[:, 2]

    sin_h = time_enc_arr[:, 0]
    cos_h = time_enc_arr[:, 1]

    uBoil = actions_raw_arr[:, 0]
    uCO2 = actions_raw_arr[:, 1]
    uThScr = actions_raw_arr[:, 2]
    uVent = actions_raw_arr[:, 3]
    uLamp = actions_raw_arr[:, 4]
    uBlScr = actions_raw_arr[:, 5]

    # --- Non-linear physics terms ---
    # Saturation vapour pressure [kPa]
    psat = 0.6108 * np.exp(17.27 * t_in / (t_in + 237.3))
    # Vapour Pressure Deficit [kPa]
    vpd = (1.0 - rh / 100.0) * psat
    # Effective solar gain through screen [W/m²]
    S_eff = rad * (1.0 - uThScr)

    # --- Cross-terms ---
    t_S_eff = t_in * S_eff
    h_uVent = rh * uVent
    # NOTE: dc_ext = co2 - co2_out is intentionally NOT a standalone feature
    # (would create perfect collinearity). It only appears inside dc_uVent.
    dc_uVent = (co2 - co2_out) * uVent
    t_uBoil = t_in * uBoil

    features = np.column_stack([
        T_out, rad, co2_out, sin_h, cos_h,
        uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
        psat, vpd, S_eff,
        t_S_eff, h_uVent, dc_uVent, t_uBoil,
    ])  # (N, 18)

    return features


def compute_physics_features_single(
    *,
    t_in: float,
    co2: float,
    rh: float,
    T_out: float,
    rad: float,
    co2_out: float,
    sin_h: float,
    cos_h: float,
    u_vec: np.ndarray,
) -> np.ndarray:
    """Compute one 18-d physics feature row for online control paths."""
    states = np.array([[t_in, co2, rh]], dtype=np.float64)
    weather = np.array([[T_out, rad, co2_out]], dtype=np.float64)
    time_enc = np.array([[sin_h, cos_h]], dtype=np.float64)
    actions = np.asarray(u_vec, dtype=np.float64).reshape(1, 6)
    return compute_physics_features(states, weather, time_enc, actions)[0]


def check_condition_number(matrix: np.ndarray, context: str = "") -> float:
    """
    Compute the condition number of *matrix* via SVD and log warnings.

    Raises
    ------
    ValueError
        If condition number exceeds KAPPA_MAX (10 000).
    """
    sv = np.linalg.svd(matrix, compute_uv=False)
    sv_nonzero = sv[sv > 0]
    if sv_nonzero.size == 0:
        return np.inf
    kappa = sv_nonzero[0] / sv_nonzero[-1]

    tag = f"[{context}] " if context else ""
    if kappa > KAPPA_MAX:
        raise ValueError(
            f"{tag}Feature matrix condition number κ={kappa:.1f} > {KAPPA_MAX:.0f}. "
            "SINDy fit aborted to avoid numerically unreliable coefficients."
        )
    if kappa > KAPPA_WARN:
        logger.warning(
            "%sFeature matrix condition number κ=%.1f > %.0f. "
            "Results may be sensitive to scaling.",
            tag, kappa, KAPPA_WARN,
        )
    return kappa
