"""Single source of truth for the E0-E3 experiment protocol (Rostov-on-Don, EPI).

Everything the notebooks need to agree on lives here: location, the leakage-free
year split, data budgets, horizons, seeds, the equal hyperparameter budget, and the
economic constants / constraint corridors that are READ FROM THE LIVE SIMULATOR
(`gl_gym` GreenhouseReward) rather than hard-coded.

Design choices (see own-article/EXPERIMENT_PROTOCOL.md):
- Location: Rostov-on-Don (47.24 N, 39.71 E); real ERA5 weather already shipped in
  gl_gym/data/weather/Rostov-on-Don/{2018..2023}.csv. rostov_soil.apply_rostov_soil()
  is wired into article_experiment_utils._make_env (gated on location).
- Split (leakage-free): TRAIN = {2018, 2019}; in-distribution TEST = 2020;
  OOD = {2021, 2022, 2023} (OOD is exercised by E5 in the next pass).
- Primary metric: EPI = sum of per-step simulator profit [EUR/m2.season]; harvested
  from env.step(...) info, decomposed into revenue / heat / co2 / electricity.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Any

import article_experiment_utils as U


# ── Calendar helpers ─────────────────────────────────────────────────────────

def _start_date(year: int, month_day: str) -> str:
    return f"{year}-{month_day}"


# ── Protocol configuration ───────────────────────────────────────────────────

@dataclass
class ProtocolConfig:
    location: str = "Rostov-on-Don"
    season_start_md: str = "03-01"        # planting calendar date (month-day)
    train_years: tuple[int, ...] = (2018, 2019)
    test_year: int = 2020                 # in-distribution held-out year
    ood_years: tuple[int, ...] = (2021, 2022, 2023)

    period: int = 900                     # control step [s] -> 96 steps/day
    horizon: int = 20                     # MPC prediction horizon [steps]

    # Article-grade settings (overridden when fast=True via for_speed()).
    n_days_train: int = 60
    n_days_test: int = 60
    budgets_days: tuple[int, ...] = (1, 3, 7, 14, 30, 60)
    seeds: tuple[int, ...] = tuple(range(10))   # >=10 independent train collections

    noise_scale: float = 0.1
    noise_period: int = 5

    # Equal hyperparameter budget shared by every tuned controller (E3) and the
    # identification ladder search (E2): number of trial configurations.
    hp_budget: int = 16

    # RL (PPO/SAC) training budget in env steps -- equal for both (E3).
    rl_train_steps: int = 200_000

    fast: bool = False

    # ── derived scenario builders ────────────────────────────────────────────
    @property
    def steps_per_day(self) -> int:
        return int(86400 / self.period)

    def base_cfg(self, n_days: int, seed: int = 42) -> U.ExperimentConfig:
        """An ExperimentConfig anchored to the train calendar (year-agnostic period)."""
        return U.ExperimentConfig(
            location=self.location,
            start_date=_start_date(self.train_years[0], self.season_start_md),
            growth_year=self.train_years[0],
            n_days=n_days,
            period=self.period,
            horizon=self.horizon,
            seed=seed,
            noise_scale=self.noise_scale,
            noise_period=self.noise_period,
        )

    def train_scenarios(self) -> list[dict[str, Any]]:
        """One collection job per training year (start date fixed across years)."""
        return [
            {"year": y, "start_date": _start_date(y, self.season_start_md),
             "n_days": self.n_days_train, "role": "train"}
            for y in self.train_years
        ]

    def test_scenario(self) -> dict[str, Any]:
        return {"year": self.test_year,
                "start_date": _start_date(self.test_year, self.season_start_md),
                "n_days": self.n_days_test, "role": "test_in_dist"}

    def ood_scenarios(self) -> list[dict[str, Any]]:
        return [
            {"year": y, "start_date": _start_date(y, self.season_start_md),
             "n_days": self.n_days_test, "role": "ood"}
            for y in self.ood_years
        ]

    def cfg_for(self, scenario: dict[str, Any], seed: int = 42) -> U.ExperimentConfig:
        return U.ExperimentConfig(
            location=self.location,
            start_date=scenario["start_date"],
            growth_year=int(scenario["year"]),
            n_days=int(scenario["n_days"]),
            period=self.period,
            horizon=self.horizon,
            seed=seed,
            noise_scale=self.noise_scale,
            noise_period=self.noise_period,
        )

    # ── fast / smoke variant ─────────────────────────────────────────────────
    def for_speed(self) -> "ProtocolConfig":
        """Downscaled config for FAST_MODE smoke runs (minutes, not hours)."""
        return ProtocolConfig(
            location=self.location,
            season_start_md=self.season_start_md,
            train_years=self.train_years,
            test_year=self.test_year,
            ood_years=self.ood_years,
            period=self.period,
            horizon=8,
            n_days_train=5,
            n_days_test=3,
            budgets_days=(1, 3, 5),
            seeds=(0, 1),
            noise_scale=self.noise_scale,
            noise_period=self.noise_period,
            hp_budget=4,
            rl_train_steps=1_500,
            fast=True,
        )

    def resolved(self, fast: bool) -> "ProtocolConfig":
        return self.for_speed() if fast else self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Live simulator economics / constraints (read, never invent) ──────────────

def read_env_economics(location: str = "Rostov-on-Don") -> dict[str, Any]:
    """Create a throwaway env and read the real prices + constraint corridors.

    Returns the economic constants and the CO2/T/RH corridors that gl_gym actually
    enforces, so the protocol config and EPI metrics stay in sync with the simulator.
    """
    probe_year = 2020 if location.lower().startswith("rostov") else 2010
    cfg = U.ExperimentConfig(location=location, start_date=f"{probe_year}-03-01",
                             growth_year=probe_year, n_days=1)
    env = U._make_env(cfg, n_days=1)
    try:
        scen = U.weather_scenario_from_date(cfg.start_date, location, cfg.growth_year)
        env.reset(options={"scenario": scen}, seed=0)
        raw = env.unwrapped
        rf = raw.reward_fn
        low = [float(v) for v in raw.constraints_low]
        high = [float(v) for v in raw.constraints_high]
        # constraint order in GreenhouseReward._output_violations is [CO2, T, RH]
        corridors = {
            "co2": (low[0], high[0]),
            "t_in": (low[1], high[1]),
            "rh": (low[2], high[2]),
        }
        prices = {
            "fruit_price_eur_per_kg": float(rf.fruit_price_model.price),
            "heating_price_eur_per_kwh": float(rf.heating_price_model.price),
            "elec_price_eur_per_kwh": float(rf.elec_price_model.price),
            "co2_price_eur_per_kg": float(rf.co2_price_model.price),
            "dmfm": float(rf.dmfm),
        }
    finally:
        env.close()
    return {"location": location, "corridors": corridors, "prices": prices}


DEFAULT = ProtocolConfig()
