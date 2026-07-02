"""Merge E5 (generalization + OOD) partials.

Outputs: tables/e5_generalization_matrix.csv, tables/e5_ood_correlation.csv,
         tables/e5_guard_summary.csv, figures/e5_generalization.png
"""
from __future__ import annotations
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402


def _concat(pattern):
    frames = []
    for p in sorted(glob.glob(str(U.results_dir() / "tables" / pattern))):
        try:
            if os.path.getsize(p) > 0:
                frames.append(pd.read_csv(p))
        except Exception as exc:  # noqa: BLE001
            print("skip", os.path.basename(p), exc)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> int:
    RES = U.results_dir()
    grid = _concat("e5_grid_*.csv")
    roc = _concat("e5_roc_*.csv")
    if grid.empty:
        print("no e5 grid partials"); return 1

    # 1) generalization matrix: train x test EPI (mean over seeds)
    mat = grid.pivot_table(index="train", columns="test", values="epi_unguarded", aggfunc="mean")
    mat.to_csv(RES / "tables" / "e5_generalization_matrix.csv")

    # 2) OOD <-> error correlations across the grid
    def cc(x, y):
        m = np.isfinite(grid[x]) & np.isfinite(grid[y])
        return float(np.corrcoef(grid[x][m], grid[y][m])[0, 1]) if m.sum() > 2 else float("nan")
    corr = pd.DataFrame([
        {"signal": "mahalanobis", "vs_rollout_rmse": cc("maha", "rollout_rmse"), "vs_epi": cc("maha", "epi_unguarded")},
        {"signal": "ensemble_std", "vs_rollout_rmse": cc("ens_std", "rollout_rmse"), "vs_epi": cc("ens_std", "epi_unguarded")},
    ])
    corr.to_csv(RES / "tables" / "e5_ood_correlation.csv", index=False)

    # 3) guard ablation
    g = pd.DataFrame([{
        "viol_unguarded": grid["viol_unguarded"].mean(), "viol_guarded": grid["viol_guarded"].mean(),
        "epi_unguarded": grid["epi_unguarded"].mean(), "epi_guarded": grid["epi_guarded"].mean(),
        "guard_frac": grid["guard_frac"].mean(),
    }])
    g.to_csv(RES / "tables" / "e5_guard_summary.csv", index=False)

    # 4) detector ROC (per-step ood vs corridor violation)
    auc = float("nan")
    if not roc.empty and roc["violation"].nunique() > 1:
        from sklearn.metrics import roc_auc_score, roc_curve
        auc = float(roc_auc_score(roc["violation"], roc["ood"]))
        fpr, tpr, _ = roc_curve(roc["violation"], roc["ood"])
    else:
        fpr = tpr = np.array([0, 1])

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    im = ax[0].imshow(mat.values, aspect="auto", cmap="RdYlGn")
    ax[0].set_xticks(range(len(mat.columns)), mat.columns, rotation=30, ha="right", fontsize=7)
    ax[0].set_yticks(range(len(mat.index)), mat.index, fontsize=8)
    ax[0].set_title("Generalization: EPI (train→test)"); fig.colorbar(im, ax=ax[0])
    ax[1].scatter(grid["maha"], grid["rollout_rmse"], label="Mahalanobis")
    ax[1].set_xlabel("OOD signal (Mahalanobis)"); ax[1].set_ylabel("rollout-RMSE")
    ax[1].set_title(f"OOD↔error (r={cc('maha','rollout_rmse'):.2f})"); ax[1].grid(alpha=.3)
    ax[2].plot(fpr, tpr); ax[2].plot([0, 1], [0, 1], "k--", lw=0.8)
    ax[2].set_xlabel("FPR"); ax[2].set_ylabel("TPR"); ax[2].set_title(f"OOD detector ROC (AUC={auc:.2f})"); ax[2].grid(alpha=.3)
    U.save_figure(fig, RES / "figures" / "e5_generalization.png")

    print("=== generalization matrix (EPI) ===")
    print(mat.round(2).to_string())
    print("\n=== OOD-vs-error correlation ===")
    print(corr.round(2).to_string(index=False))
    print("\n=== guard ablation ===")
    print(g.round(2).to_string(index=False))
    print(f"\nOOD detector ROC AUC (per-step ood→violation) = {auc:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
