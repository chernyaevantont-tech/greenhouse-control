"""The bootstrap draw as a measured variance axis (regen-v2, experiment `draws`).

Why this experiment exists
--------------------------
`optimizer="ensemble"` fits by bagging: it resamples the identification data 20 times and
averages the resulting coefficient sets. WHICH resample you get is random, and in pysindy
2.1.0 `EnsembleOptimizer` exposes no `random_state` -- it draws from the global NumPy RNG.

Both the 2026-07 run and the first regen took ONE realisation per seed and reported it as
the method's performance. On identical data, five refits gave

    xi(uBoil->t_in) = 0.0605 / 0.0280 / 0.0264 / 0.0000 / 0.0274

i.e. the control-critical boiler term vanishes in roughly one refit in five. The DAgger
variants are hit hardest because `dagger_final` refits four times (initial + 3 aggregation
rounds), so each round is an independent lottery on whether the term survives. That is how
one pipeline on one dataset produced "+2.43 EUR/m2, first in all four seasons" and
"-0.12 EUR/m2, fourth of ten" -- the difference was the draw, not the method.

Reporting a point estimate over an unstated variance component is the defect. The remedy is
not "make it deterministic and hope" -- the regen is already deterministic, and -0.12 is an
UNBIASED estimate of the mean over draws (each seed's draw is uncorrelated with outcome).
Sweeping the draw does not move that mean; it measures the spread around it and turns
"we got +2.43 once" into a probability.

What it produces
----------------
For the two ensemble-based controllers (`sindy_mpc_conf`, `sindy_mpc_conf_dagger`), the
full seed x draw x season grid. `sindy_mpc_dense` and `sindy_mpc_lowthr` are STLSQ --
deterministic given the data, no draw axis -- so they are not swept; include one draw of
each only as a control that the axis really is flat for them.

The analysis this enables, which the single-draw protocol cannot support:
  * variance decomposition: how much of the spread is data (seed) vs bootstrap (draw);
  * P(this method leads the field on a single run) -- how lucky 2026-07 was, as a number;
  * intervals on the DAgger repair effect that account for both axes.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

import regen_config as C


# Controllers whose fit actually has a draw axis. The STLSQ ones are carried at a single
# draw as a negative control: their spread across draws must be exactly zero.
#
# `sindy_mpc_raw_ens` added 2026-08-10 (E-A). It is ensemble-based, so it carries the same
# lottery, and after N-7 it is the HEADLINE controller (+4.07 EUR/m2, first in all four
# seasons). Reporting it as a point estimate over an unmeasured draw axis would repeat
# exactly the defect this experiment exists to fix -- and it is the same defect that
# produced "+2.43, first in all four seasons" for a controller whose true mean is -0.12.
# `sindy_mpc_raw` (STLSQ, same library) is the matched control: if the raw library's
# advantage is real it must show up at zero draw spread too.
DRAW_CONTROLLERS = ("sindy_mpc_conf", "sindy_mpc_conf_dagger", "sindy_mpc_raw_ens")
CONTROL_CONTROLLERS = ("sindy_mpc_dense", "sindy_mpc_raw")


def exp_draws(args, seeds, pc, econ, out: Path) -> int:
    import run_regen as R

    n_draws = 2 if args.fast else int(getattr(args, "draws", 0) or C.ENSEMBLE_DRAWS)
    years = [int(y) for y in (args.test_years.split(",") if args.test_years else [])] \
        or list(C.TEST_YEARS)
    if args.fast:
        years = years[:2]
    rows, path = [], out / f"draws_{args.tag}.csv"

    for s in seeds:
        train = C.build_train_dataset(pc, seed=s, fast=args.fast)
        for ctrl in DRAW_CONTROLLERS + CONTROL_CONTROLLERS:
            # The control pair has no draw axis; one realisation is the whole story.
            draws = range(n_draws) if ctrl in DRAW_CONTROLLERS else range(1)
            for dr in draws:
                t0 = time.time()
                try:
                    model = R.build_model(ctrl, pc, train, s, args.fast, draw=dr)
                except Exception as exc:  # noqa: BLE001
                    R._log(f"seed {s} {ctrl} draw {dr} BUILD-FAILED "
                           f"{type(exc).__name__}: {str(exc)[:120]}")
                    continue
                xi = R._uboil(model)
                for y in years:
                    try:
                        df = R.rollout(ctrl, model, pc, y, s, args.fast)
                        m = R.score(df, econ, pc)
                        m.update({"block": "draws", "condition": f"{ctrl}/d{dr}",
                                  "method": ctrl, "draw": int(dr), "seed": s,
                                  "test_year": int(y), "xi_uboil": xi,
                                  "n_draws_declared": n_draws,
                                  "secs": round(time.time() - t0, 1), **C.stamp()})
                        rows.append(m)
                        R._write(rows, path)
                    except Exception as exc:  # noqa: BLE001
                        R._log(f"seed {s} {ctrl} draw {dr} y{y} FAILED "
                               f"{type(exc).__name__}: {str(exc)[:120]}")
                R._log(f"seed {s} {ctrl} draw {dr} xi={xi:.5f} ({round(time.time()-t0,1)}s)")
    R._write(rows, path)
    return 0


def summarise(d) -> "object":
    """Variance decomposition + how often each method would top the field on one run.

    Called by make_tables; kept here so the reasoning sits next to the experiment.
    """
    import pandas as pd

    if d is None or not len(d) or "draw" not in d.columns:
        return None
    out = {}
    per = d.groupby(["method", "seed", "draw"]).epi.mean().reset_index()

    # Spread attributable to each axis, per method. `draw` spread must be ~0 for the STLSQ
    # control; if it is not, the axis is leaking somewhere it should not.
    rows = []
    for m, g in per.groupby("method"):
        by_seed = g.groupby("seed").epi.mean()
        by_draw = g.groupby("draw").epi.mean()
        rows.append({"method": m,
                     "mean": g.epi.mean(),
                     "sd_total": g.epi.std(ddof=1),
                     "sd_between_seeds": by_seed.std(ddof=1),
                     "sd_between_draws": by_draw.std(ddof=1),
                     "n_seeds": g.seed.nunique(), "n_draws": g.draw.nunique()})
    out["variance"] = pd.DataFrame(rows)

    # P(leads) -- across draws, how often does a method's mean beat the others'? This is the
    # number that says how lucky a single-run "first place" was.
    piv = per.pivot_table(index=["seed", "draw"], columns="method", values="epi")
    if len(piv.columns) > 1:
        wins = piv.idxmax(axis=1).value_counts(normalize=True).rename("p_leads")
        out["p_leads"] = wins.reset_index().rename(columns={"index": "method"})
    return out
