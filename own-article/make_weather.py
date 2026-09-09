"""Weather CSVs for gl_gym from Open-Meteo (ERA5/ERA5-Land).

WHY. The data the whole study rests on were produced by `make_rostov_weather.py`, which --
by the account in weather_data_methodology.md -- lived in a session scratchpad and was lost.
The INPUT to the experiments was therefore irreproducible even though the method was
written down. This file reconstructs the generator from that document, and is checked by
regenerating a year that already ships with gl_gym and comparing.

    python make_weather.py --check 2020            # regenerate and compare with shipped
    python make_weather.py --years 2014,2015,2016,2017 --out <dir>

Format (9 columns, as in the shipped gl_gym data):
    time, global radiation, wind speed, air temperature, sky temperature, ??,
    CO2 concentration, day number, RH
Step 300 s, one full calendar year. The loader reads only six columns, by name.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

API = "https://archive-api.open-meteo.com/v1/archive"
LAT, LON = 47.24, 39.71
HOURLY = ("temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m,"
          "shortwave_radiation,cloud_cover")
SITE = "Rostov-on-Don"


def _shipped_weather() -> Path:
    """Where the simulator keeps its weather files for this site.

    GREENLIGHT_WEATHER_DIR overrides everything. Otherwise the installed gl_gym package is
    asked for its own data directory, which is where the simulator reads from; failing
    that, a directory beside this file, so the step still runs from an unpacked archive.
    """
    import os

    env = os.environ.get("GREENLIGHT_WEATHER_DIR")
    if env:
        return Path(env)
    try:
        import gl_gym
        cand = Path(gl_gym.__file__).parent / "data" / "weather" / SITE
        if cand.parent.parent.is_dir():
            return cand
    except Exception:
        pass
    return Path(__file__).resolve().parent / "weather" / SITE


SHIPPED = _shipped_weather()


def fetch(year: int, lat: float = LAT, lon: float = LON) -> pd.DataFrame:
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
        "hourly": HOURLY, "wind_speed_unit": "ms", "timezone": "UTC"})
    with urllib.request.urlopen(f"{API}?{q}", timeout=180) as r:
        js = json.loads(r.read().decode())
    h = js["hourly"]
    d = pd.DataFrame(h)
    d["time"] = pd.to_datetime(d["time"])
    return d


def sky_temperature(t_air_c, dew_c, cloud_frac):
    """Sky temperature is derived, not measured (methodology, section 3).

    e_a       = 6.112 exp(17.62 Td / (243.12 + Td))        vapour pressure, hPa (Magnus)
    eps_clear = clip(0.605 + 0.048 sqrt(e_a), 0, 1)        clear sky (Brunt)
    eps_sky   = (1 - CC) eps_clear + CC                    cloud -> black body
    T_sky     = eps_sky^0.25 * T_air                       in kelvin
    """
    e_a = 6.112 * np.exp(17.62 * dew_c / (243.12 + dew_c))
    eps_clear = np.clip(0.605 + 0.048 * np.sqrt(np.maximum(e_a, 0.0)), 0.0, 1.0)
    eps_sky = (1.0 - cloud_frac) * eps_clear + cloud_frac * 1.0
    return eps_sky ** 0.25 * (t_air_c + 273.15) - 273.15


def build_year(year: int) -> pd.DataFrame:
    raw = fetch(year)
    n_days = 366 if pd.Timestamp(year=year, month=1, day=1).is_leap_year else 365
    steps = n_days * 288                       # 288 five-minute steps per day
    t_sec = np.arange(steps, dtype=float) * 300.0
    src_sec = (raw["time"] - raw["time"].iloc[0]).dt.total_seconds().to_numpy()

    def interp(col):
        return np.interp(t_sec, src_sec, raw[col].to_numpy(dtype=float))

    t_air = interp("temperature_2m")
    dew = interp("dew_point_2m")
    rh = np.clip(interp("relative_humidity_2m"), 0.0, 100.0)
    wind = np.maximum(interp("wind_speed_10m"), 0.0)
    rad = interp("shortwave_radiation")
    rad[rad < 1e-10] = 0.0                     # methodology: zero the radiation noise floor
    cloud = np.clip(interp("cloud_cover") / 100.0, 0.0, 1.0)

    return pd.DataFrame({
        "time": t_sec,
        "global radiation": rad,
        "wind speed": wind,
        "air temperature": t_air,
        "sky temperature": sky_temperature(t_air, dew, cloud),
        "??": 0.0,
        "CO2 concentration": 400.0,            # hard-coded in gl_gym; the column is ignored
        "day number": np.floor(t_sec / 86400.0),
        "RH": rh,
    })


def check(year: int) -> int:
    """Regenerate a year that already exists and compare with the shipped file."""
    ship = pd.read_csv(SHIPPED / f"{year}.csv")
    got = build_year(year)
    print(f"rows: shipped {len(ship)}, reconstructed {len(got)}")
    ok = len(ship) == len(got)
    for c in ("global radiation", "wind speed", "air temperature", "sky temperature", "RH"):
        a, b = ship[c].to_numpy(), got[c].to_numpy()
        m = min(len(a), len(b))
        r = float(np.corrcoef(a[:m], b[:m])[0, 1])
        mae = float(np.mean(np.abs(a[:m] - b[:m])))
        good = r > 0.99 and mae < max(0.5, 0.02 * (np.ptp(a[:m]) or 1))
        ok &= good
        print(f"  [{'OK ' if good else 'MISMATCH'}] {c:18s} r={r:.5f} MAE={mae:.3f}")
    print("\nreconstruction is correct" if ok else "\nRECONSTRUCTION DOES NOT MATCH")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="")
    ap.add_argument("--out", default=str(SHIPPED))
    ap.add_argument("--check", type=int, default=None)
    a = ap.parse_args()
    if a.check:
        return check(a.check)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for y in [int(x) for x in a.years.split(",") if x.strip()]:
        d = build_year(y)
        p = out / f"{y}.csv"
        d.to_csv(p, index=False)
        print(f"[ok] {p}  rows {len(d)}  "
              f"t_air {d['air temperature'].min():.1f}..{d['air temperature'].max():.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
