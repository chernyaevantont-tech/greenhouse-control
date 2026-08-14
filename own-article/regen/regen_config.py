"""Single source of truth for the article regeneration (regen-v2).

EVERY number that ends up in the paper must come from a run configured by THIS module.
Nothing here falls back silently: a missing or inconsistent input raises.

Why this file exists
--------------------
The 2026-06/07 results were produced by several runners that disagreed with each other
and with the protocol text (see ../regen/README.md, "Defect register"). The most
damaging disagreements were:

  D1  the sparsity threshold -- the paper's central hyper-parameter -- was NOT part of
      the frozen recipe. `protocol_config.CANONICAL_RECIPE` has no `threshold` key, so
      the confirmatory model silently used `article_experiment_utils.fit_sindy`'s
      function default (0.05). Here it is explicit and hashed.
  D2  `protocol_config.load_frozen_recipe()` fell back to a hard-coded dict when the
      json was missing. In a container that is a silent provenance break. Here: raise.
  D3  TRAIN was declared {2018, 2019} but every runner used `train_scenarios()[0]`,
      i.e. 2018 only. Here: both years, aggregated.
  D4  solver-failure budgets differed 10x by controller (SINDy/grey 100, NN-MPC and
      oracle 10), which truncated exactly the two controllers the paper calls worst.
      Here: one budget for everyone, and truncation is a recorded, gating outcome.
  D5  the oracle ran at horizon 12 while every surrogate MPC ran at 20, so "model
      fidelity" and "horizon" were confounded. Here: one horizon for everyone, plus an
      explicit oracle-horizon sweep so the effect is measured instead of assumed.

Import contract: this module only *declares*. Compute lives in the already-validated
`article_experiment_utils` API; `run_regen.py` is the thin driver.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWN_ARTICLE = HERE.parent
if str(OWN_ARTICLE) not in sys.path:
    sys.path.insert(0, str(OWN_ARTICLE))

import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

REGEN_ID = "regen-v2"

# ── Protocol constants (were scattered across runners; now declared once) ─────
LOCATION = "Rostov-on-Don"
SEASON_START_MD = "03-01"
TRAIN_YEARS = (2018, 2019)          # D3: BOTH, not just the first
TEST_YEARS = (2020, 2021, 2022, 2023)
IN_DIST_YEAR = 2020                 # the rest are out-of-distribution
SEEDS = tuple(range(20))            # 20, pinned here -- not a CLI accident

PERIOD = 900                        # control step [s] -> 96 steps/day
SEASON_DAYS = 60
STEPS_PER_SEASON = SEASON_DAYS * 86400 // PERIOD   # 5760; used as the truncation gate

HORIZON = 20                        # D5: ONE horizon for every predictive controller
MAX_SOLVER_FAILURES = 100           # D4: ONE budget for every solver-based controller

PRBS_SCALE = 0.3                    # identification excitation on top of the rule base
NOISE_SCALE = 0.1                   # collection-time excitation (eval rollouts use 0)
RL_TRAIN_STEPS = 200_000
NN_EPOCHS = 300
NN_HIDDEN = (64, 64)
DAGGER_ITERS = 3
DAGGER_EPISODE_DAYS = 5

ORACLE_CEM = dict(n_samples=48, n_iters=2, elite_frac=0.2, sample_std=0.3)

# Measures D5 instead of assuming it away. Cost is ~linear in the horizon; from the
# 2026-08-03 smoke (3-day season, 32 samples): h=12 -> 185 s, h=20 -> 271 s, i.e. about
# (56 + 10.75*h) seconds. Scaling to the real season (x20 steps, x1.5 samples) gives
# roughly 1.5 h at h=12, 2.3 h at h=20, 4.8 h at h=48 and 9.1 h at h=96 PER SEED -- so the
# full sweep on all 20 seeds would cost more than the entire main table. It is a
# sensitivity analysis, not a headline, so it runs on a fixed 5-seed subset; the h=20 point
# that establishes parity with the surrogate MPC is covered on ALL seeds by the main table.
ORACLE_HORIZON_SWEEP = (12, 20, 48, 96)
ORACLE_SWEEP_SEEDS = (0, 1, 2, 3, 4)

# λ sweep for the mechanism experiment. Denser than the 8-point 2026-07 grid around the
# collapse AND past it: the old grid's last point (λ=0.1, boiler coefficient exactly 0)
# had HIGHER EPI than λ=0.05, which contradicts the paper's monotonicity claim. The
# sweep must resolve that region rather than end there.
LAMBDA_GRID = (1e-6, 1e-3, 1e-2, 2e-2, 3e-2, 4e-2, 5e-2, 6e-2, 7e-2, 8e-2, 1e-1,
               1.5e-1, 2e-1)

# ── Identification recipes (explicit; every key that reaches fit_sindy) ───────
# NOTE the threshold keys: previously implicit (D1).
CONFIRMATORY = {
    "feature_variant": "physics_no_cross",
    "library_degree": 1,
    "optimizer": "ensemble",
    "denoise": "none",
    "threshold": 0.05,
}
DENSE = {
    "feature_variant": "physics_no_cross",
    "library_degree": 1,
    "optimizer": "stlsq",
    "denoise": "none",
    "threshold": 1e-3,
}
# Was called `grey_box_mpc` and described in the paper as a "reduced first-principles
# grey-box model". It is not: it is THIS SAME estimator at threshold 1e-6. Renamed so the
# regen cannot reproduce that claim by accident. See README "G-1" and build_true_greybox().
LOWTHR = {
    "feature_variant": "physics_no_cross",
    "library_degree": 1,
    "optimizer": "stlsq",
    "denoise": "none",
    "threshold": 1e-6,
}
# `physics` adds the four bilinear cross terms that the knockout run showed carry part of
# the heating pathway. The temperature x boiler term is named `t_uBoil` in the library (NOT
# `t_in*uBoil`) -- run_regen.CROSS_TERM. Used by the mechanism experiment only.
CROSS = {
    "feature_variant": "physics",
    "library_degree": 1,
    "optimizer": "stlsq",
    "denoise": "none",
    "threshold": 1e-6,
}

RECIPES = {"confirmatory": CONFIRMATORY, "dense": DENSE, "lowthr": LOWTHR, "cross": CROSS}

# ── N-7: the recipe the pre-registered criterion actually selects ─────────────
# The ladder, re-run with the corrected step horizons (2026-08-10), ranks the RAW library
# first on both pre-registered open-loop metrics and the frozen physics_no_cross recipe far
# behind, on identical fits (seeds 0/1 agree):
#
#     raw/d1/stlsq/none                  rollout RMSE  2.62   diverged 0.0000
#     physics_no_cross/d1/ensemble/none  rollout RMSE 11.04   diverged 0.0167   <- frozen
#
# The frozen recipe DOES pass the divergence gate (0.017 <= 0.05); the earlier claim that it
# failed its own gate came from the stale pre-fix ladder and is retracted. What survives is
# the 4.2x rollout gap -- and the manuscript asserts the opposite, that the raw library lost
# on open-loop metrics (statya_ru.tex:336). No controller in the main table uses `raw`, so
# the closed-loop consequence has never been measured. That is what these two recipes are for.
#
# Threshold is held at CONFIRMATORY's 0.05 so the ONLY thing that changes is the library.
# `_stlsq` is the ladder's top-ranked entry and is deterministic; `_ens` is the exact
# one-factor change from the confirmatory recipe and keeps the bootstrap-draw lottery, so the
# pair also separates "library" from "optimizer".
RAW_STLSQ = {
    "feature_variant": "raw",
    "library_degree": 1,
    "optimizer": "stlsq",
    "denoise": "none",
    "threshold": 0.05,
}
RAW_ENS = {
    "feature_variant": "raw",
    "library_degree": 1,
    "optimizer": "ensemble",
    "denoise": "none",
    "threshold": 0.05,
}

# Deliberately NOT in RECIPES/_declared()/config_hash, and the controllers below are NOT in
# ALL_CONTROLLERS: this ADDS an experiment rather than changing any existing one, and hashing
# it would invalidate every already-computed wave (the same convention as ENSEMBLE_DRAWS and
# LADDER_ROLLOUT_HORIZONS_STEPS). The recipe reaches each result row through the usual
# `fit_sindy_seeded` RNG key, so provenance stays self-contained.
# Замыкает ряд по обусловленности. Ладдер даёт kappa 8.2 (raw) -> 24.5 (physics_no_cross)
# -> 53.4 (physics), но замкнутый регулятор был только у первых двух, поэтому крайняя точка
# ряда -- худшая по обусловленности библиотека -- в замкнутом контуре не измерялась вовсе.
# Рецензент спросит об этом первым. Оба варианта -- одношаговое изменение относительно
# уже измеренных: порог и степень те же, меняется только библиотека.
PHYS_ENS = {
    "feature_variant": "physics",
    "library_degree": 1,
    "optimizer": "ensemble",
    "denoise": "none",
    "threshold": 0.05,
}
PHYS_STLSQ = {
    "feature_variant": "physics",
    "library_degree": 1,
    "optimizer": "stlsq",
    "denoise": "none",
    "threshold": 0.05,
}

EXT_RECIPES = {"raw_stlsq": RAW_STLSQ, "raw_ens": RAW_ENS,
               "phys_ens": PHYS_ENS, "phys_stlsq": PHYS_STLSQ}
CONTROLLERS_EXT = ["sindy_mpc_raw", "sindy_mpc_raw_ens",
                   "sindy_mpc_phys", "sindy_mpc_phys_ens"]

# ── Controllers ──────────────────────────────────────────────────────────────
# `sindy_mpc_lowthr` replaces the old `grey_box_mpc` label (same computation, honest name).
CONTROLLERS_CHEAP = ["rule_based", "sindy_mpc_conf", "sindy_mpc_dense",
                     "sindy_mpc_lowthr", "nn_mpc"]
CONTROLLERS_DAGGER = ["sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"]
CONTROLLERS_RL = ["ppo", "sac"]
CONTROLLERS_ORACLE = ["oracle_mpc"]
ALL_CONTROLLERS = (CONTROLLERS_CHEAP + CONTROLLERS_DAGGER
                   + CONTROLLERS_RL + CONTROLLERS_ORACLE)

NEEDS_TRAIN = {"sindy_mpc_conf", "sindy_mpc_dense", "sindy_mpc_lowthr", "nn_mpc",
               "sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger",
               "sindy_mpc_raw", "sindy_mpc_raw_ens",
               "sindy_mpc_phys", "sindy_mpc_phys_ens"}   # ext, see EXT_RECIPES
SOLVER_BASED = {"sindy_mpc_conf", "sindy_mpc_dense", "sindy_mpc_lowthr", "nn_mpc",
                "sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger", "oracle_mpc",
                "sindy_mpc_raw", "sindy_mpc_raw_ens",
                "sindy_mpc_phys", "sindy_mpc_phys_ens"}  # ext, see EXT_RECIPES

EXPECTED_MAIN_ROWS = len(ALL_CONTROLLERS) * len(TEST_YEARS) * len(SEEDS)   # 10*4*20 = 800

# ── Supporting experiments (were separate runners with their own constants) ───
# Every one of these previously ran on its own season length: E5 on 14 days, E6/E7 on 30,
# the main table on 60. The paper presents them side by side without saying so. Here they
# all use the canonical season, and the window is recorded per row regardless.

# E2 identification ladder: the 42 configurations the pre-registration chose from.
# 3 libraries x 2 degrees x 4 optimisers x 3 denoisers = 72 cells; the historical ladder
# has 42 because the infeasible combinations were skipped. We enumerate all 72 and let
# the gates reject; the count is then an outcome, not an assumption.
LADDER_VARIANTS = ("raw", "physics", "physics_no_cross")
LADDER_DEGREES = (1, 2)
LADDER_OPTIMIZERS = ("stlsq", "sr3", "constrained", "ensemble")
LADDER_DENOISE = ("none", "savgol", "kalman")
# Open-loop rollout horizons for the ladder, IN STEPS -- the same defaults the original E2
# used (`evaluate_sindy`'s `rollout_horizons=(4, 20, 96)`), i.e. 1 h / 5 h / 1 day.
#
# The first regen got this wrong and it produced a false alarm worth recording. The paper
# says the frozen recipe barely diverges "при длине прогноза не менее 3 суток" -- literally
# "at a forecast length of at least 3 days". That reads as a rollout horizon, so this
# constant was named ..._BUDGETS_DAYS = (1, 3, 7) and fed to evaluate_sindy as horizons of
# 96/288/672 steps -- up to SEVEN days of free running. Everything diverges over seven days:
# the frozen recipe scored diverged_frac 0.21 and rollout RMSE 12.4 against the historical
# E2's 0.0 and 2.76, on an identical fit (28 non-zero terms both times), and the harness
# duly reported that the pre-registered recipe fails its own gates. It does not.
#
# `e2_stability_vs_budget.csv` settles it: `budget_days` there is the TRAINING-DATA budget
# (1 day -> diverged 0.55, 3 days and up -> 0.0), not a forecast horizon. The manuscript's
# wording conflates the two and should say "объём обучающих данных", not "длина прогноза".
#
# Deliberately NOT part of `_declared()`/config_hash: it only affects the ladder, and adding
# it would invalidate the hash of every already-computed wave. The value is recorded per row
# instead, so ladder provenance stays self-contained.
LADDER_ROLLOUT_HORIZONS_STEPS = (4, 20, 96)

# The training-data budget curve (E2's other axis). Not currently swept by the ladder;
# kept here so the two ideas cannot silently merge again.
LADDER_TRAIN_BUDGETS_DAYS = (1, 3, 7, 14, 30, 60)

# E4 online adaptation: static surrogate vs data aggregation vs EKF/RLS, on the OOD years.
ADAPT_MODES = ("static", "dagger", "ekf")
EKF_FORGETTING = 0.999          # the gentle prior; the aggressive one (0.995/p0=10) wound up
EKF_P0 = 0.1

# E5 OOD guard: Mahalanobis threshold as a quantile of the training distances.
GUARD_QUANTILE = 0.95
ENSEMBLE_VARIANCE_MODELS = 20

# E7 fault injection: six modes, each with and without the residual supervisor.
FAULTS = (
    ("t_in_stuck", {"layer": "sensor", "target": "t_in", "type": "stuck", "value": 25.0}),
    ("t_in_offset", {"layer": "sensor", "target": "t_in", "type": "offset", "value": 4.0}),
    ("rh_offset", {"layer": "sensor", "target": "rh", "type": "offset", "value": -25.0}),
    ("uVent_dead", {"layer": "actuator", "target": "uVent", "type": "dead", "value": 0.0}),
    ("uBoil_stuck", {"layer": "actuator", "target": "uBoil", "type": "stuck", "value": 1.0}),
    ("uLamp_dead", {"layer": "actuator", "target": "uLamp", "type": "dead", "value": 0.0}),
)
FAULT_ONSET_FRACTION = 0.33     # fault starts a third of the way into the season
FAULT_RESID_THRESHOLD = 3.0

# E6 sensitivity: prices dominate design parameters -- the paper's tornado.
SENS_FRUIT_PRICE = (0.8, 1.6, 3.2)          # EUR/kg, around the nominal 1.6
SENS_ENERGY_SCALE = (0.5, 1.0, 2.0)         # multiplier on heat/elec/CO2 prices
SENS_HORIZONS = (8, 12, 20, 30)
SENS_THRESHOLDS = (0.01, 0.05, 0.1, 0.2)
# E-E: прежняя сетка (0.1, 0.2, 0.3) при 2 повторах дала немонотонный и огромный
# разброс -- 0.2 -> -13.41 при СКО 20.4, а 0.3 -> -4.77. Это признак слишком малого
# числа реализаций шума, а не свойства модели. Сетка мельче, повторов больше.
# Вне _declared()/config_hash: меняет только объём эксперимента E6.
SENS_COEF_PERTURB = (0.02, 0.05, 0.10, 0.15, 0.20)
SENS_PERTURB_REPS = 4

# Bootstrap draws per seed for the ensemble recipes (experiment `draws`).
# Deliberately NOT in _declared()/config_hash: it adds a new experiment rather than changing
# any existing one, and hashing it would invalidate every already-computed wave. Recorded
# per row as `n_draws_declared` instead.
ENSEMBLE_DRAWS = 10

# Oracle optimiser budget: does a bigger search help, or is the horizon binding?
ORACLE_BUDGETS = ((48, 2), (96, 3), (192, 4))

# RL normalisation: the paper reports PPO at -13 without VecNormalize and +3.4 with it.
# Reproduced as an experiment rather than quoted from a lost run.
RL_NORM_MODES = ("normalized", "raw")


# ── Provenance ───────────────────────────────────────────────────────────────

def _declared() -> dict:
    """Everything that can change a number, in one dict, for hashing and stamping."""
    return {
        "regen_id": REGEN_ID,
        "location": LOCATION, "season_start_md": SEASON_START_MD,
        "train_years": list(TRAIN_YEARS), "test_years": list(TEST_YEARS),
        "seeds": list(SEEDS), "period": PERIOD, "season_days": SEASON_DAYS,
        "horizon": HORIZON, "max_solver_failures": MAX_SOLVER_FAILURES,
        "prbs_scale": PRBS_SCALE, "noise_scale": NOISE_SCALE,
        "rl_train_steps": RL_TRAIN_STEPS, "nn_epochs": NN_EPOCHS,
        "nn_hidden": list(NN_HIDDEN),
        "dagger_iters": DAGGER_ITERS, "dagger_episode_days": DAGGER_EPISODE_DAYS,
        "oracle_cem": ORACLE_CEM, "oracle_horizon_sweep": list(ORACLE_HORIZON_SWEEP),
        "oracle_sweep_seeds": list(ORACLE_SWEEP_SEEDS),
        "lambda_grid": list(LAMBDA_GRID), "recipes": RECIPES,
        "controllers": ALL_CONTROLLERS,
    }


def config_hash() -> str:
    blob = json.dumps(_declared(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=str(OWN_ARTICLE), capture_output=True, text=True,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def stamp() -> dict:
    """Provenance columns attached to EVERY result row, so a merged CSV can never mix runs."""
    return {"regen_id": REGEN_ID, "config_hash": config_hash(), "git_sha": git_sha(),
            "image": os.environ.get("REGEN_IMAGE", "local")}


def write_manifest(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "regen_manifest.json"
    payload = dict(_declared())
    payload.update(stamp())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_recipe(name: str) -> dict:
    """Fail-loud recipe access (D2). No fallback, no implicit threshold, no surprises."""
    table = RECIPES if name in RECIPES else EXT_RECIPES
    if name not in table:
        raise KeyError(f"unknown recipe {name!r}; "
                       f"known: {sorted(RECIPES)} + ext {sorted(EXT_RECIPES)}")
    rec = dict(table[name])
    if "threshold" not in rec:
        raise ValueError(f"recipe {name!r} has no explicit threshold -- refusing to run (D1)")
    return rec


# ── Scenario / dataset builders ──────────────────────────────────────────────

def protocol(fast: bool = False) -> "P.ProtocolConfig":
    """A ProtocolConfig carrying THIS module's constants (not protocol_config's defaults)."""
    pc = P.ProtocolConfig(
        location=LOCATION, season_start_md=SEASON_START_MD,
        train_years=TRAIN_YEARS, test_year=IN_DIST_YEAR,
        ood_years=tuple(y for y in TEST_YEARS if y != IN_DIST_YEAR),
        period=PERIOD, horizon=HORIZON,
        n_days_train=SEASON_DAYS, n_days_test=SEASON_DAYS,
        seeds=SEEDS, noise_scale=NOISE_SCALE, rl_train_steps=RL_TRAIN_STEPS,
    )
    return pc.for_speed() if fast else pc


def train_scenarios(fast: bool = False) -> list[dict]:
    return protocol(fast).train_scenarios()          # BOTH train years (D3)


def test_scenario(pc, year: int) -> dict:
    return {"year": int(year),
            "start_date": f"{int(year)}-{SEASON_START_MD}",
            "n_days": pc.n_days_test,
            "role": "test_in_dist" if int(year) == IN_DIST_YEAR else "ood"}


def build_train_dataset(pc, seed: int, fast: bool = False):
    """Identification dataset = rule-based + PRBS over ALL declared train years (D3).

    The 2026-07 runners used only train_scenarios()[0] (2018), contradicting the Methods
    text. Aggregating both years changes every downstream number -- which is the point of
    a regen, and must be stated in the paper.
    """
    parts = []
    for sc in pc.train_scenarios():
        cfg = pc.cfg_for(sc, seed=seed)
        parts.append(U.collect_rule_based_dataset(
            cfg, n_days=pc.n_days_train, start_date=sc["start_date"], seed=seed,
            noise_scale=NOISE_SCALE, prbs_scale=PRBS_SCALE))
    if len(parts) == 1:
        return parts[0]
    return U.aggregate_trajectories(parts, pc.cfg_for(pc.train_scenarios()[0], seed=seed))


# Surrogate fitting deliberately does NOT live here. It needs the global-RNG pin (D7), and
# there must be exactly one code path that does it: `run_regen.fit_sindy_seeded`, which
# derives the RNG key from the run coordinates and records it in the bundle metadata.
# A second helper here would be a second way to get different numbers from the same seed.


def build_true_greybox(*_a, **_kw):
    """NOT IMPLEMENTED, deliberately.

    The paper claims an independent "reduced first-principles grey-box model" that the
    repaired surrogate converges onto. No such model exists in this repository: the old
    `grey_box_mpc` was `fit_sindy(physics_no_cross, degree 1, threshold=1e-6)` -- the same
    data-driven estimator as `sindy_mpc_dense` with a marginally lower threshold, so their
    agreement (3.79 vs 3.81) is an identity, not a convergence.

    Two honest options, both requiring a human decision:
      (a) drop the first-principles claim and report the controller as `sindy_mpc_lowthr`
          (what regen-v2 does by default); or
      (b) author a genuine grey-box: fix the energy/mass-balance coefficients of the
          t_in / co2 / rh equations from GreenLight's documented parameters, leave only the
          unknown transfer coefficients free, fit those, and embed via build_mpc_controller.
    """
    raise NotImplementedError(
        "no first-principles grey-box exists; see build_true_greybox.__doc__ (README G-1)")
