"""Reproducibility control for the regeneration.

The 2026-07 stack had two unseeded random sources, both on controllers the paper draws
conclusions from:

  R1  `pysindy.EnsembleOptimizer` (2.1.0) takes no random_state and resamples via
      `np.random.choice` -- the GLOBAL legacy NumPy RNG, which nothing ever seeded. The
      confirmatory recipe uses `optimizer="ensemble"`, so refitting identical data gave a
      different coefficient matrix every time. Measured on the smoke data, five refits of
      one dataset produced Xi(uBoil->t_in) = 0.0605 / 0.0280 / 0.0264 / 0.0000 / 0.0274:
      the "sparsity threshold zeroes the boiler term" event fired in roughly one refit in
      five, on the SAME data. The paper's central mechanism was therefore partly a coin
      flip, and the reproducibility statement was not true as written.

  R2  `fit_nn_surrogate` builds the MLP with torch's default init and iterates a
      `DataLoader(..., shuffle=True)`. Both consume the global torch RNG, also never
      seeded, so NN-MPC -- the controller the paper calls worst -- was not reproducible
      either.

`seed_everything` closes both, plus the interpreter-level sources, and pins the thread
counts (float reduction order in BLAS depends on the thread count, so a 4-thread run and
a 1-thread run can differ in the last bits and then diverge through a 5760-step closed
loop). `env_fingerprint` records what the numbers were produced with; `--selftest` proves
determinism rather than asserting it.

    python repro.py --selftest          # fits/rollouts twice, compares bit-for-bit
    python repro.py --fingerprint       # prints the environment record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

# Thread pinning must happen BEFORE numpy/torch import their backends.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402


def seed_everything(seed: int) -> None:
    """Seed every global RNG the compute stack can reach. Call before each work unit.

    Per-call generators (`np.random.default_rng(seed)`) in the codebase are already
    deterministic and unaffected; this covers the *global* state that pysindy's ensemble
    optimiser and torch reach into.
    """
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed % (2**31 - 1))          # R1: pysindy EnsembleOptimizer bagging
    try:
        import torch
        torch.manual_seed(seed)                  # R2: MLP init + DataLoader shuffle
        torch.cuda.manual_seed_all(seed)
        torch.set_num_threads(1)
        # Deterministic kernels where torch offers them. warn_only: the CPU MLP path has
        # no non-deterministic op, but a future GPU RL pod would otherwise hard-fail.
        torch.use_deterministic_algorithms(True, warn_only=True)
        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except Exception:
        pass


def env_fingerprint() -> dict:
    """What these numbers were produced with. Goes into the manifest and every gate."""
    pkgs = {}
    import importlib.metadata as md
    for p in ("numpy", "scipy", "pandas", "scikit-learn", "gl_gym", "gymnasium",
              "pysindy", "casadi", "do-mpc", "torch", "stable_baselines3", "matplotlib"):
        try:
            pkgs[p] = md.version(p)
        except Exception:
            pkgs[p] = "MISSING"
    threads = {v: os.environ.get(v) for v in
               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    fp = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": pkgs,
        "threads": threads,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
    }
    blob = json.dumps({"packages": pkgs, "python": fp["python"]}, sort_keys=True)
    fp["env_hash"] = hashlib.sha256(blob.encode()).hexdigest()[:12]
    return fp


def _digest(arr) -> str:
    a = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
    return hashlib.sha256(a.tobytes()).hexdigest()[:16]


RL_IN_SELFTEST = False       # V4, включается ключом --rl


def selftest(fast: bool = True) -> int:
    """Run the pipeline twice under identical seeds; every digest must match.

    Covers the two previously-broken paths (ensemble fit, NN surrogate) plus a closed-loop
    rollout, because determinism of the fit is worthless if the loop diverges afterwards.
    """
    import warnings
    warnings.filterwarnings("ignore")
    import article_experiment_utils as U
    import regen_config as C

    pc = C.protocol(fast=fast)
    results, ok = {}, True

    for attempt in (1, 2):
        seed_everything(0)
        train = C.build_train_dataset(pc, seed=0, fast=fast)
        d = {"train_states": _digest(train.states), "train_actions": _digest(train.actions)}

        # Imported here, not at module level: run_regen imports repro.
        import run_regen as R

        conf = R.fit_sindy_seeded(train, pc, seed=0, label="conf",
                                  recipe=C.load_recipe("confirmatory"))
        d["ensemble_coefs"] = _digest(conf.model.coefficients())

        dense = R.fit_sindy_seeded(train, pc, seed=0, label="dense",
                                   recipe=C.load_recipe("dense"))
        d["stlsq_coefs"] = _digest(dense.model.coefficients())

        seed_everything(0)
        nn = U.fit_nn_surrogate(train, feature_variant="physics",
                                hidden_sizes=list(C.NN_HIDDEN),
                                epochs=(5 if fast else 30), period=float(pc.period),
                                metadata={"label": "nn"})
        d["nn_weights"] = _digest(np.concatenate([np.ravel(w) for w in nn.weights]))

        seed_everything(0)
        sc = C.test_scenario(pc, C.IN_DIST_YEAR)
        cfg = pc.cfg_for(sc, seed=0)
        df = U.rollout_mpc(dense, cfg, n_days=pc.n_days_test, start_date=sc["start_date"],
                           objective="full", max_solver_failures=C.MAX_SOLVER_FAILURES)
        d["rollout_epi"] = f"{float(df['profit'].sum()):.12e}" if "profit" in df else "n/a"
        d["rollout_states"] = _digest(df[list(U.STATE_NAMES)].to_numpy())

        # V4: PPO/SAC were never covered here. The README states outright that "PPO/SAC
        # reproducibility has not been re-verified under the new pinning", so the paper's
        # blanket reproducibility claim was unsupported for two of its ten controllers.
        # SB3 takes an explicit `seed=`, but its env resets, action sampling and torch
        # init are separate streams -- whether they land identically has to be measured.
        # Off by default because training is the expensive part; enable with --rl.
        if RL_IN_SELFTEST:
            for algo in ("ppo", "sac"):
                seed_everything(0)
                sc_tr = pc.train_scenarios()[0]
                steps = 2000 if fast else pc.rl_train_steps
                model = U.train_rl(algo, pc.cfg_for(sc_tr, seed=0), steps,
                                   train_start_date=sc_tr["start_date"], seed=0)
                par = model.policy.parameters() if hasattr(model, "policy") else []
                flat = np.concatenate([p.detach().cpu().numpy().ravel() for p in par]) \
                    if par else np.zeros(1)
                d[f"{algo}_policy"] = _digest(flat)

        results[attempt] = d
        print(f"  attempt {attempt}: " + " ".join(f"{k}={v[:10]}" for k, v in d.items()))

    print()
    for k in results[1]:
        same = results[1][k] == results[2][k]
        ok &= same
        print(f"[{'PASS' if same else 'FAIL'}] {k}")

    fp = env_fingerprint()
    print(f"\nenv_hash={fp['env_hash']} python={fp['python']} "
          f"pysindy={fp['packages'].get('pysindy')} torch={fp['packages'].get('torch')}")
    print("\nfully reproducible" if ok else "\nNON-DETERMINISTIC -- do not run the regen")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fingerprint", action="store_true")
    ap.add_argument("--full", action="store_true", help="selftest on the real 60-day season")
    ap.add_argument("--rl", action="store_true",
                    help="V4: включить PPO/SAC в самотест (долго)")
    a = ap.parse_args()
    if a.fingerprint:
        print(json.dumps(env_fingerprint(), indent=2))
        return 0
    if a.selftest:
        global RL_IN_SELFTEST
        RL_IN_SELFTEST = bool(a.rl)
        return selftest(fast=not a.full)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
