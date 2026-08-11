"""Генератор погодных CSV для gl_gym из Open-Meteo (ERA5/ERA5-Land).

ЗАЧЕМ. Данные, на которых построена вся работа, сделаны скриптом
`make_rostov_weather.py`, который, по свидетельству
[weather_data_methodology.md](weather_data_methodology.md), лежал «в scratchpad сессии» и
утерян. То есть ВХОД экспериментов невоспроизводим, хотя методика описана. Этот файл
восстанавливает генератор по документу и проверяется регенерацией уже имеющегося года.

    python make_weather.py --check 2020            # регенерировать и сравнить с shipped
    python make_weather.py --years 2014,2015,2016,2017 --out <dir>

Формат (9 колонок, как в shipped-данных gl_gym):
    time, global radiation, wind speed, air temperature, sky temperature, ??,
    CO2 concentration, day number, RH
Шаг 300 с, полный календарный год. Загрузчик читает только 6 колонок по имени.
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
SHIPPED = Path(r"C:\Users\zergu\repos\greenlight\GreenLight-Gym2\gl_gym\data\weather"
               r"\Rostov-on-Don")


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
    """Температура неба выводится, а не измеряется (методика, разд. 3).

    e_a       = 6.112 exp(17.62 Td / (243.12 + Td))        давление пара, гПа (Магнус)
    eps_clear = clip(0.605 + 0.048 sqrt(e_a), 0, 1)        ясное небо (Брант)
    eps_sky   = (1 - CC) eps_clear + CC                    облака -> абсолютно чёрное тело
    T_sky     = eps_sky^0.25 * T_air                       в кельвинах
    """
    e_a = 6.112 * np.exp(17.62 * dew_c / (243.12 + dew_c))
    eps_clear = np.clip(0.605 + 0.048 * np.sqrt(np.maximum(e_a, 0.0)), 0.0, 1.0)
    eps_sky = (1.0 - cloud_frac) * eps_clear + cloud_frac * 1.0
    return eps_sky ** 0.25 * (t_air_c + 273.15) - 273.15


def build_year(year: int) -> pd.DataFrame:
    raw = fetch(year)
    n_days = 366 if pd.Timestamp(year=year, month=1, day=1).is_leap_year else 365
    steps = n_days * 288                       # 288 пятиминуток в сутках
    t_sec = np.arange(steps, dtype=float) * 300.0
    src_sec = (raw["time"] - raw["time"].iloc[0]).dt.total_seconds().to_numpy()

    def interp(col):
        return np.interp(t_sec, src_sec, raw[col].to_numpy(dtype=float))

    t_air = interp("temperature_2m")
    dew = interp("dew_point_2m")
    rh = np.clip(interp("relative_humidity_2m"), 0.0, 100.0)
    wind = np.maximum(interp("wind_speed_10m"), 0.0)
    rad = interp("shortwave_radiation")
    rad[rad < 1e-10] = 0.0                     # методика: обнулять шум радиации
    cloud = np.clip(interp("cloud_cover") / 100.0, 0.0, 1.0)

    return pd.DataFrame({
        "time": t_sec,
        "global radiation": rad,
        "wind speed": wind,
        "air temperature": t_air,
        "sky temperature": sky_temperature(t_air, dew, cloud),
        "??": 0.0,
        "CO2 concentration": 400.0,            # в gl_gym зашито, столбец игнорируется
        "day number": np.floor(t_sec / 86400.0),
        "RH": rh,
    })


def check(year: int) -> int:
    """Регенерировать имеющийся год и сравнить с поставляемым файлом."""
    ship = pd.read_csv(SHIPPED / f"{year}.csv")
    got = build_year(year)
    print(f"строк: shipped {len(ship)}, восстановлено {len(got)}")
    ok = len(ship) == len(got)
    for c in ("global radiation", "wind speed", "air temperature", "sky temperature", "RH"):
        a, b = ship[c].to_numpy(), got[c].to_numpy()
        m = min(len(a), len(b))
        r = float(np.corrcoef(a[:m], b[:m])[0, 1])
        mae = float(np.mean(np.abs(a[:m] - b[:m])))
        good = r > 0.99 and mae < max(0.5, 0.02 * (np.ptp(a[:m]) or 1))
        ok &= good
        print(f"  [{'OK ' if good else 'РАСХОЖДЕНИЕ'}] {c:18s} r={r:.5f} MAE={mae:.3f}")
    print("\nвосстановление верно" if ok else "\nВОССТАНОВЛЕНИЕ НЕ СОВПАДАЕТ")
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
        print(f"[ok] {p}  строк {len(d)}  "
              f"t_air {d['air temperature'].min():.1f}..{d['air temperature'].max():.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
