"""Region-correct deep-soil boundary temperature for Rostov-on-Don.

GreenLight-Gym hard-codes ``gl_gym.environments.utils.soilTempNl`` — an annual
sinusoid (Kusuda-Achenbach form) fitted to a Dutch grassland (Jacobs et al.,
2011) at ~1 m depth: ``T = 10 + 5*sin(2*pi*(t + 0.625*yr)/yr)``. It is used as
the external soil temperature ``d.tSoOut`` (deep-soil boundary condition).

For Rostov-on-Don (47.24 N, 39.71 E) this is materially wrong: the continental
climate has ~2x the annual amplitude of maritime NL. We refit the same
analytical (single-harmonic) form to ERA5-Land soil temperature, layer
0.28-1.00 m (node ~0.72 m, the closest available to the model's nominal 1 m),
hourly 2018-2023, pulled via the Open-Meteo archive API.

Fit (least squares, 6 years):
    T_mean   = 11.26 C   (NL: 10.0)
    amplitude = 10.36 C   (NL:  5.0)   <- ~2x larger, continental climate
    phase shift = 234.6 d
    sinusoid RMSE vs ERA5-Land hourly = 1.37 C
    annual min ~0.9 C (~day 39), max ~21.6 C (~day 222)

Sensitivity (closed env, Rostov 2020, fixed action): replacing the NL model
with this fit shifts indoor air temperature by ~0.30 C RMSE (max 0.59 C) —
a second-order but non-negligible systematic correction.

References:
  Kusuda, T. & Achenbach, P. R. (1965). Earth Temperature and Thermal
    Diffusivity at Selected Stations in the United States. ASHRAE Trans. 71(1).
  Jacobs, Heusinkveld & Holtslag (2011). Agric. For. Meteorol. 151, 774-780.
  Munoz-Sabater et al. (2021). ERA5-Land. Earth Syst. Sci. Data 13, 4349-4383.
"""
from __future__ import annotations
import numpy as np

# Fitted constants (ERA5-Land 0.28-1.0 m, Rostov-on-Don, 2018-2023)
_SECS_IN_YEAR = 365.25 * 86400.0
_T_MEAN = 11.26
_AMPLITUDE = 10.356
_PHASE_SHIFT_S = 20_266_007.0  # seconds; T = mean + A*sin(2*pi*(t + shift)/P)


def soilTempRostov(time):
    """External soil temperature [degC] for Rostov-on-Don at a given time.

    Drop-in replacement for ``gl_gym.environments.utils.soilTempNl``.

    Args:
        time: seconds since the beginning of the year (scalar or ndarray).
    Returns:
        Soil temperature [degC] at ~1 m depth.
    """
    t = np.asarray(time, dtype=float)
    return _T_MEAN + _AMPLITUDE * np.sin(2 * np.pi * (t + _PHASE_SHIFT_S) / _SECS_IN_YEAR)


def apply_rostov_soil() -> None:
    """Monkeypatch gl_gym to use the Rostov soil model.

    Call BEFORE creating/resetting any GreenLight env (the WeatherRepository
    caches weather per (location, year, start_day), so the patch must be active
    on the first load).
    """
    import gl_gym.environments.utils as _u
    _u.soilTempNl = soilTempRostov
