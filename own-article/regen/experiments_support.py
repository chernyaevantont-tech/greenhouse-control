"""Supporting experiments E2/E4/E5/E6/E7, folded into the regen's single config.

These were five separate runners (`regen_e2_interpretability.py`, `run_e4_shift.py`,
`run_e5_grid.py`, `run_e6_sensitivity.py`, `run_e7_faults.py`), each with its own season
length -- E5 on 14 days, E6/E7 on 30, the main table on 60 -- and each reading
`protocol_config` defaults rather than a shared frozen config. The paper presents their
results side by side without saying they were measured on different windows.

Here they all run on the canonical season, through `run_regen`'s seeded fit path, and every
row records the window it was measured on so the question can never be silent again.

Compute is not reimplemented: `U.rollout_mpc_ekf`, `U.rollout_mpc_guarded`,
`U.rollout_mpc_faulty`, `U.fit_mahalanobis`, `U.fit_ensemble_for_variance` are the same
validated functions the legacy runners called.

`run_regen` imports this module; every function here imports `run_regen` lazily to keep the
dependency one-way at import time.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

import article_experiment_utils as U
import regen_config as C


# ── E2: identification ladder (the pre-registration artifact) ────────────────

def exp_ladder(args, seeds, pc, econ, out: Path) -> int:
    """Reproduce the configuration sweep the confirmatory recipe was frozen from.

    The paper says 42 configurations were compared and the winner frozen by open-loop
    criteria. We enumerate the full 3x2x4x3 = 72 grid and let the gates reject, so the
    surviving count is an outcome rather than an assumption -- and so a reader can check
    that the frozen recipe really is the one the stated criteria select.

    Everything here is open-loop by construction: that is the point. No closed-loop number
    is computed, exactly as the pre-registration required.
    """
    import run_regen as R

    rows, path = [], out / f"ladder_{args.tag}.csv"
    budgets = C.LADDER_ROLLOUT_BUDGETS_DAYS[:2] if args.fast else C.LADDER_ROLLOUT_BUDGETS_DAYS
    variants = C.LADDER_VARIANTS[:2] if args.fast else C.LADDER_VARIANTS
    degrees = (1,) if args.fast else C.LADDER_DEGREES
    opts = ("stlsq", "ensemble") if args.fast else C.LADDER_OPTIMIZERS
    dens = ("none",) if args.fast else C.LADDER_DENOISE

    for s in seeds:
        train = C.build_train_dataset(pc, seed=s, fast=args.fast)
        for variant in variants:
            for degree in degrees:
                for opt in opts:
                    for den in dens:
                        rec = {"feature_variant": variant, "library_degree": degree,
                               "optimizer": opt, "denoise": den,
                               "threshold": C.CONFIRMATORY["threshold"]}
                        rec_id = f"{variant}/d{degree}/{opt}/{den}"
                        t0 = time.time()
                        row = {"block": "ladder", "condition": rec_id, "seed": s,
                               "variant": variant, "degree": degree, "optimizer": opt,
                               "denoise": den, "n_days_train": pc.n_days_train,
                               **C.stamp()}
                        try:
                            b = R.fit_sindy_seeded(train, pc, seed=s, label=rec_id, recipe=rec)
                            row["nonzero"] = int(np.count_nonzero(b.model.coefficients()))
                            row["kappa"] = float(getattr(b, "condition_number", np.nan))
                            row.update(_openloop_stability(b, train, budgets))
                            row.update(_transparency(b))
                            row["embeddable"] = _embeddable(b, pc, s)
                            row["secs"] = round(time.time() - t0, 1)
                        except Exception as exc:  # noqa: BLE001
                            row["error"] = f"{type(exc).__name__}: {str(exc)[:80]}"
                        rows.append(row)
                        R._write(rows, path)
                        R._log(f"seed {s} ladder {rec_id} nz={row.get('nonzero','-')} "
                               f"rmse={row.get('rollout_rmse_t_in', float('nan')):.3f} "
                               f"emb={row.get('embeddable','-')}")
    R._write(rows, path)
    return 0


def _openloop_stability(bundle, data, budgets) -> dict:
    """Multi-step rollout error and divergence fraction -- the frozen selection criteria."""
    out = {}
    try:
        ev = U.evaluate_sindy(bundle, data, rollout_horizons=tuple(
            int(b * 86400 // 900) for b in budgets))
        roll = ev[ev.metric_scope == "rollout"]
        t = roll[roll.state == "t_in"]
        if len(t):
            out["rollout_rmse_t_in"] = float(t.sort_values("horizon").iloc[-1].rmse)
            fa = t.get("failed_rollouts")
            at = t.get("attempted_rollouts")
            if fa is not None and at is not None:
                tot = float(at.sum())
                out["diverged_frac"] = float(fa.sum()) / tot if tot else np.nan
        one = ev[(ev.metric_scope == "one_step") & (ev.state == "t_in")]
        if len(one):
            out["one_step_rmse_t_in"] = float(one.iloc[0].rmse)
    except Exception as exc:  # noqa: BLE001
        out["stability_error"] = f"{type(exc).__name__}: {str(exc)[:60]}"
    return out


def _transparency(bundle) -> dict:
    """Sign/dimension checks -- the interpretability gate the paper says it applied."""
    try:
        t = U.sign_check_table(bundle)
        if "passed" in t:
            return {"sign_pass": float(t["passed"].mean())}
        col = [c for c in t.columns if t[c].dtype == bool]
        return {"sign_pass": float(t[col[0]].mean()) if col else np.nan}
    except Exception:
        return {"sign_pass": np.nan}


def _embeddable(bundle, pc, seed) -> bool:
    """Can the identified map actually be compiled into the MPC? The second frozen gate."""
    try:
        sc = C.test_scenario(pc, C.IN_DIST_YEAR)
        cfg = pc.cfg_for(sc, seed=seed)
        wp = U.WeatherForecastTVP(cfg, n_days=1, start_date=sc["start_date"])
        U.build_mpc_controller(bundle, wp, cfg)
        return True
    except Exception:
        return False


# ── E4: online adaptation under season shift ─────────────────────────────────

def exp_adapt(args, seeds, pc, econ, out: Path) -> int:
    """Static surrogate vs data aggregation vs EKF/RLS on the out-of-distribution seasons.

    The paper's claim is that structure (keeping the boiler term), not coefficient
    adaptation, carries robustness: aggregation adds little and EKF actively hurts. Both
    directions are worth re-measuring, because the EKF result depends on the prior and the
    earlier aggressive prior (p0=10, forgetting=0.995) destabilised the loop.
    """
    import run_regen as R

    rows, path = [], out / f"adapt_{args.tag}.csv"
    years = [y for y in C.TEST_YEARS if y != C.IN_DIST_YEAR]
    if args.fast:
        years = years[:1]

    for s in seeds:
        train = C.build_train_dataset(pc, seed=s, fast=args.fast)
        static = R.fit_sindy_seeded(train, pc, seed=s, label="adapt_static",
                                    recipe=C.load_recipe("confirmatory"))
        dagger = R.build_model("sindy_mpc_conf_dagger", pc, train, s, args.fast)
        for y in years:
            pc_y = _year_cfg(pc, y)
            sc = C.test_scenario(pc_y, y)
            cfg = pc_y.cfg_for(sc, seed=s)
            for mode in C.ADAPT_MODES:
                t0 = time.time()
                try:
                    if mode == "static":
                        df = U.rollout_mpc(static, cfg, n_days=pc_y.n_days_test,
                                           start_date=sc["start_date"], objective="full",
                                           max_solver_failures=C.MAX_SOLVER_FAILURES)
                    elif mode == "dagger":
                        df = U.rollout_mpc(dagger, cfg, n_days=pc_y.n_days_test,
                                           start_date=sc["start_date"], objective="full",
                                           max_solver_failures=C.MAX_SOLVER_FAILURES)
                    else:
                        R.pin_rng(C.REGEN_ID, "ekf", s, y)
                        df = U.rollout_mpc_ekf(static, cfg, n_days=pc_y.n_days_test,
                                               start_date=sc["start_date"],
                                               forgetting=C.EKF_FORGETTING, p0=C.EKF_P0,
                                               max_solver_failures=C.MAX_SOLVER_FAILURES)
                    m = R.score(df, econ, pc_y)
                    m.update({"block": "adapt", "condition": mode, "mode": mode,
                              "seed": s, "test_year": y,
                              "secs": round(time.time() - t0, 1), **C.stamp()})
                    rows.append(m)
                    R._write(rows, path)
                    R._log(f"seed {s} adapt/{mode} y{y} EPI={m.get('epi', float('nan')):.3f}")
                except Exception as exc:  # noqa: BLE001
                    R._log(f"seed {s} adapt/{mode} y{y} FAILED "
                           f"{type(exc).__name__}: {str(exc)[:120]}")
    R._write(rows, path)
    return 0


# ── E5: distribution-shift detection and the OOD guard ───────────────────────

def exp_guard(args, seeds, pc, econ, out: Path) -> int:
    """Does the surrogate know when it is out of its depth, and does acting on it help?

    Two products per seed: (a) the association between two uncertainty signals and the
    actual prediction error, including the ROC AUC the paper reports as a *weak* signal;
    (b) the closed-loop effect of handing control to the rule base when the signal fires.
    """
    import run_regen as R
    from sklearn.metrics import roc_auc_score

    rows, path = [], out / f"guard_{args.tag}.csv"
    years = [y for y in C.TEST_YEARS if y != C.IN_DIST_YEAR]
    if args.fast:
        years = years[:1]

    for s in seeds:
        train = C.build_train_dataset(pc, seed=s, fast=args.fast)
        b = R.fit_sindy_seeded(train, pc, seed=s, label="guard",
                               recipe=C.load_recipe("confirmatory"))
        maha = U.fit_mahalanobis(train)
        R.pin_rng(C.REGEN_ID, "ens_var", s)
        ens = U.fit_ensemble_for_variance(train, feature_variant=C.CONFIRMATORY["feature_variant"],
                                          n_models=C.ENSEMBLE_VARIANCE_MODELS,
                                          period=float(pc.period))
        d_train = U.mahalanobis_distances(maha, train.weather, train.time_enc)
        thr = float(np.quantile(d_train, C.GUARD_QUANTILE))

        for y in years:
            pc_y = _year_cfg(pc, y)
            sc = C.test_scenario(pc_y, y)
            cfg = pc_y.cfg_for(sc, seed=s)
            try:
                test_d = U.collect_rule_based_dataset(
                    cfg, n_days=pc_y.n_days_test, start_date=sc["start_date"], seed=s,
                    noise_scale=0.0)
                dist = U.mahalanobis_distances(maha, test_d.weather, test_d.time_enc)
                err = _one_step_abs_error(b, test_d)
                n = min(len(dist), len(err))
                dist, err = dist[:n], err[:n]
                std = U.ensemble_pred_std(ens, test_d)[:n]
                big = err > np.quantile(err, 0.9)
                rows.append({"block": "signal", "condition": "mahalanobis", "seed": s,
                             "test_year": y, "threshold": thr,
                             "r_dist_err": float(np.corrcoef(dist, err)[0, 1]),
                             "r_std_err": float(np.corrcoef(std, err)[0, 1]),
                             "auc_dist": float(roc_auc_score(big, dist)),
                             "auc_std": float(roc_auc_score(big, std)),
                             "n_steps": int(n), **C.stamp()})

                for mode in ("plain", "guarded"):
                    t0 = time.time()
                    if mode == "plain":
                        df = U.rollout_mpc(b, cfg, n_days=pc_y.n_days_test,
                                           start_date=sc["start_date"], objective="full",
                                           max_solver_failures=C.MAX_SOLVER_FAILURES)
                    else:
                        df = U.rollout_mpc_guarded(b, maha, thr, cfg,
                                                   n_days=pc_y.n_days_test,
                                                   start_date=sc["start_date"],
                                                   max_solver_failures=C.MAX_SOLVER_FAILURES)
                    m = R.score(df, econ, pc_y)
                    m.update({"block": "guard", "condition": mode, "seed": s,
                              "test_year": y, "threshold": thr,
                              "guard_activations": int(df.get("guard_active", pd.Series(dtype=int)).sum())
                              if "guard_active" in df else -1,
                              "secs": round(time.time() - t0, 1), **C.stamp()})
                    rows.append(m)
                R._write(rows, path)
                R._log(f"seed {s} guard y{y} thr={thr:.2f} ok")
            except Exception as exc:  # noqa: BLE001
                R._log(f"seed {s} guard y{y} FAILED {type(exc).__name__}: {str(exc)[:120]}")
    R._write(rows, path)
    return 0


def _one_step_abs_error(bundle, data) -> np.ndarray:
    """Per-step |prediction error| on t_in, for the ROC target."""
    feats, _ = U.compute_feature_matrix(data, bundle.feature_variant)
    x_sc = bundle.scaler_x.transform(data.states)
    u_sc = bundle.scaler_u.transform(feats)
    pred = bundle.scaler_x.inverse_transform(
        np.asarray(bundle.model.predict(x_sc[:-1], u=u_sc[:-1])))
    return np.abs(pred[:, 0] - data.states[1:, 0])


# ── E7: fault injection and the residual supervisor ──────────────────────────

def exp_faults(args, seeds, pc, econ, out: Path) -> int:
    """Six sensor/actuator faults, each with and without the residual-based supervisor.

    The paper's honest finding here is that the supervisor reliably cuts violations but does
    not always improve economics; both columns are therefore recorded per fault.
    """
    import run_regen as R

    rows, path = [], out / f"faults_{args.tag}.csv"
    faults = C.FAULTS[:2] if args.fast else C.FAULTS
    year = C.IN_DIST_YEAR
    sc = C.test_scenario(pc, year)
    onset = int(pc.n_days_test * 86400 // pc.period * C.FAULT_ONSET_FRACTION)

    for s in seeds:
        train = C.build_train_dataset(pc, seed=s, fast=args.fast)
        b = R.fit_sindy_seeded(train, pc, seed=s, label="faults",
                               recipe=C.load_recipe("dense"))
        cfg = pc.cfg_for(sc, seed=s)
        try:
            df0 = U.rollout_mpc(b, cfg, n_days=pc.n_days_test, start_date=sc["start_date"],
                                objective="full", max_solver_failures=C.MAX_SOLVER_FAILURES)
            m0 = R.score(df0, econ, pc)
            m0.update({"block": "faults", "condition": "nofault", "fault": "none",
                       "supervisor": False, "seed": s, "test_year": year, **C.stamp()})
            rows.append(m0)
        except Exception as exc:  # noqa: BLE001
            R._log(f"seed {s} faults baseline FAILED {type(exc).__name__}")

        for name, spec in faults:
            f = {**spec, "start_step": onset}
            for sup in (False, True):
                t0 = time.time()
                try:
                    df = U.rollout_mpc_faulty(b, cfg, pc.n_days_test, f,
                                              start_date=sc["start_date"], supervisor=sup,
                                              resid_threshold=C.FAULT_RESID_THRESHOLD,
                                              max_solver_failures=C.MAX_SOLVER_FAILURES)
                    m = R.score(df, econ, pc)
                    m.update({"block": "faults", "condition": f"{name}/{'sup' if sup else 'raw'}",
                              "fault": name, "supervisor": sup, "seed": s,
                              "test_year": year, "onset_step": onset,
                              "secs": round(time.time() - t0, 1), **C.stamp()})
                    rows.append(m)
                    R._write(rows, path)
                except Exception as exc:  # noqa: BLE001
                    R._log(f"seed {s} fault {name} sup={sup} FAILED {type(exc).__name__}")
            R._log(f"seed {s} fault {name} done")
    R._write(rows, path)
    return 0


# ── E6: design-parameter sensitivity (the price half is post-processing) ─────

def exp_design(args, seeds, pc, econ, out: Path) -> int:
    """Horizon, sparsity threshold and coefficient perturbation.

    The price half of the paper's tornado is NOT here: `epi_metrics` reads the simulator's
    per-step profit, so prices cannot be varied by re-scoring a rollout inside the loop.
    They are re-derived exactly from the recorded physical quantities (kWh of heat and
    electricity, kg of CO2, fruit dry-matter growth) in `make_tables.py`, which is both
    cheaper and clearer about what is held fixed: the control trajectories are the ones
    optimised under nominal prices, so this measures the robustness of the RANKING, not
    re-optimised operation.
    """
    import run_regen as R

    rows, path = [], out / f"design_{args.tag}.csv"
    year = C.IN_DIST_YEAR
    sc = C.test_scenario(pc, year)
    horizons = C.SENS_HORIZONS[:2] if args.fast else C.SENS_HORIZONS
    thresholds = C.SENS_THRESHOLDS[:2] if args.fast else C.SENS_THRESHOLDS
    perturbs = C.SENS_COEF_PERTURB[:1] if args.fast else C.SENS_COEF_PERTURB
    reps = 1 if args.fast else C.SENS_PERTURB_REPS

    for s in seeds:
        train = C.build_train_dataset(pc, seed=s, fast=args.fast)
        base = R.fit_sindy_seeded(train, pc, seed=s, label="design",
                                  recipe=C.load_recipe("dense"))
        cfg0 = pc.cfg_for(sc, seed=s)

        def add(factor, value, df, **extra):
            m = R.score(df, econ, pc)
            m.update({"block": "design", "condition": f"{factor}={value}", "factor": factor,
                      "value": float(value), "seed": s, "test_year": year,
                      **extra, **C.stamp()})
            rows.append(m)
            R._write(rows, path)

        for h in horizons:
            try:
                cfg_h = U.ExperimentConfig(**{**vars(cfg0), "horizon": int(h)})
                add("mpc_horizon", h, U.rollout_mpc(
                    base, cfg_h, pc.n_days_test, start_date=sc["start_date"],
                    objective="full", max_solver_failures=C.MAX_SOLVER_FAILURES))
            except Exception as exc:  # noqa: BLE001
                R._log(f"seed {s} horizon {h} FAILED {type(exc).__name__}")

        for thr in thresholds:
            try:
                rec = {**C.load_recipe("dense"), "threshold": float(thr)}
                bt = R.fit_sindy_seeded(train, pc, seed=s, label=f"thr{thr}", recipe=rec)
                add("stlsq_threshold", thr, U.rollout_mpc(
                    bt, cfg0, pc.n_days_test, start_date=sc["start_date"], objective="full",
                    max_solver_failures=C.MAX_SOLVER_FAILURES),
                    nonzero=int(np.count_nonzero(bt.model.coefficients())),
                    xi_uboil=R._uboil(bt))
            except Exception as exc:  # noqa: BLE001
                R._log(f"seed {s} threshold {thr} FAILED {type(exc).__name__}")

        Xi0 = np.asarray(base.model.coefficients(), dtype=float)
        for pert in perturbs:
            for rep in range(reps):
                try:
                    rng = np.random.default_rng(R.pin_rng(C.REGEN_ID, "pert", s, pert, rep))
                    edits = {(r, c): Xi0[r, c] * (1.0 + pert * z)
                             for (r, c), z in zip(
                                 [(r, c) for r in range(Xi0.shape[0]) for c in range(Xi0.shape[1])],
                                 rng.standard_normal(Xi0.size))}
                    bp = K_variant(base, edits, f"pert{pert}_{rep}")
                    add("coef_perturb", pert, U.rollout_mpc(
                        bp, cfg0, pc.n_days_test, start_date=sc["start_date"],
                        objective="full", max_solver_failures=C.MAX_SOLVER_FAILURES),
                        rep=rep)
                except Exception as exc:  # noqa: BLE001
                    R._log(f"seed {s} perturb {pert}/{rep} FAILED {type(exc).__name__}")
        R._log(f"seed {s} design done")
    R._write(rows, path)
    return 0


def K_variant(bundle, edits, label):
    """Coefficient-edited copy, via the validated shim in run_knockout_ablation."""
    import run_knockout_ablation as K
    return K._variant_bundle(bundle, edits, label)


def _year_cfg(pc, year: int):
    import dataclasses
    return dataclasses.replace(pc, test_year=int(year))
