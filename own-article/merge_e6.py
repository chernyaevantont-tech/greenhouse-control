"""Merge E6 (sensitivity) -> tornado of EPI robustness + line charts.

Combines the re-sim sweeps (e6_sensitivity_*.csv: mpc_horizon, stlsq_threshold,
coef_uncertainty) with post-hoc PRICE reprice of the E3 closed-loop results
(e3_seeded.csv; costs are linear in price, so no re-simulation needed).

Outputs: tables/e6_tornado.csv, tables/e6_price_sensitivity.csv,
         figures/e6_sensitivity.png
"""
from __future__ import annotations
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402


def main() -> int:
    RES = U.results_dir()
    parts = sorted(glob.glob(str(RES / "tables" / "e6_sensitivity_*.csv")))
    frames = [pd.read_csv(p) for p in parts if os.path.getsize(p) > 0]
    sens = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    e3 = pd.read_csv(RES / "tables" / "e3_seeded.csv")

    # ---- price reprice of E3 (EPI = revenue - heat - elec - co2; all linear in price) ----
    def reprice(d, fm=1.0, em=1.0, cm=1.0):
        return d["revenue"] * fm - d["cost_heat"] * em - d["cost_elec"] * em - d["cost_co2"] * cm
    methods = [m for m in ["rule_based", "grey_box_mpc", "sindy_mpc", "nn_mpc", "oracle_mpc"] if m in e3.method.values]
    mults = [0.5, 0.75, 1.0, 1.5, 2.0]
    prows = []
    for kind, kw in [("fruit", "fm"), ("energy", "em"), ("co2", "cm")]:
        for mult in mults:
            for meth in methods:
                sub = e3[e3.method == meth]
                prows.append({"price": kind, "mult": mult, "method": meth,
                              "epi": float(reprice(sub, **{kw: mult}).mean())})
    price = pd.DataFrame(prows)
    price.to_csv(RES / "tables" / "e6_price_sensitivity.csv", index=False)

    # ---- tornado for the proposed sindy_mpc ----
    base = float(e3[e3.method == "sindy_mpc"]["epi"].mean())
    tor = []
    if not sens.empty:
        for fac in ("mpc_horizon", "stlsq_threshold", "coef_uncertainty"):
            d = sens[sens.factor == fac].groupby("value")["epi"].mean()
            if len(d):
                tor.append({"factor": fac, "low": float(d.min()), "high": float(d.max())})
    sub = e3[e3.method == "sindy_mpc"]
    for kind, kw in [("fruit_price", "fm"), ("energy_price", "em"), ("co2_price", "cm")]:
        lo = float(reprice(sub, **{kw: 0.5}).mean()); hi = float(reprice(sub, **{kw: 2.0}).mean())
        tor.append({"factor": kind, "low": min(lo, hi), "high": max(lo, hi)})
    tornado = pd.DataFrame(tor)
    tornado["range"] = (tornado["high"] - tornado["low"]).abs()
    tornado = tornado.sort_values("range")
    tornado.to_csv(RES / "tables" / "e6_tornado.csv", index=False)

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    y = np.arange(len(tornado))
    ax[0].barh(y, tornado["high"] - tornado["low"], left=tornado["low"], color="steelblue")
    ax[0].axvline(base, color="k", ls="--", lw=1, label=f"baseline EPI={base:.2f}")
    ax[0].set_yticks(y, tornado["factor"]); ax[0].set_xlabel("EPI EUR/m2")
    ax[0].set_title("E6 tornado — SINDy-MPC EPI sensitivity"); ax[0].legend()
    for meth in methods:
        d = price[(price.price == "energy") & (price.method == meth)]
        ax[1].plot(d["mult"], d["epi"], marker="o", label=meth)
    ax[1].set_xlabel("energy price ×"); ax[1].set_ylabel("EPI EUR/m2")
    ax[1].set_title("EPI vs energy price (ranking robustness)"); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8)
    U.save_figure(fig, RES / "figures" / "e6_sensitivity.png")

    print("=== E6 tornado (SINDy-MPC) ===")
    print(tornado.round(3).to_string(index=False))
    print(f"\nbaseline sindy_mpc EPI = {base:.3f}")
    if not sens.empty:
        print("\n=== design-choice sweeps (mean EPI) ===")
        print(sens.groupby(["factor", "value"])["epi"].mean().round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
