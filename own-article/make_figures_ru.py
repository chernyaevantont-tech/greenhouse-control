"""Русифицированные рисунки для русской версии статьи (АиТ, Белый список ур. 1).

Читает ТОЛЬКО готовые агрегированные CSV из results_scenarios/tables и пишет
шесть рисунков в results_scenarios/figures/ru/ (канонические англоязычные
рисунки и таблицы не трогает):

  e3_pareto_annotated.png      <- e3_pareto_table.csv
  e3_lambda_sweep_ablation.png <- e3_lambda_sweep_table.csv
  oracle_horizon_sweep.png     <- oracle_horizon_sweep.csv
  e5_generalization.png        <- e5_generalization_matrix.csv + e5_grid_*.csv + e5_roc_*.csv
  e6_sensitivity.png           <- e6_tornado.csv + e6_price_sensitivity.csv + e3_seeded.csv
  e7_faults.png                <- e7_degradation.csv

Запуск:  uv run --with pandas --with matplotlib make_figures_ru.py
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

RES = Path(__file__).resolve().parent / "results_scenarios"
TAB = RES / "tables"
OUT = RES / "figures" / "ru"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 10.5,
    "figure.dpi": 110,
})

# Русские наименования регуляторов (единые для всех рисунков и таблиц статьи)
RU_LABEL = {
    "rule_based": "Эвристический (правила)",
    "grey_box_mpc": "УПМ «серый ящик»",
    "oracle_mpc": "УПМ, полная модель симулятора",
    "nn_mpc": "Нейросетевое УПМ",
    "ppo": "PPO",
    "sac": "SAC",
    "sindy_mpc": "SINDy-УПМ (исходный)",
    "sindy_mpc_confirmatory": "SINDy-УПМ (исходный)",
    "sindy_mpc_dense": "SINDy-УПМ (неразрежённый)",
    "sindy_mpc_conf_dagger": "SINDy-УПМ (исходн.+дообуч.)",
    "sindy_mpc_dense_dagger": "SINDy-УПМ (неразреж.+дообуч.)",
}


def ru(v: float, nd: int = 2, sign: bool = False) -> str:
    """Число с десятичной запятой и типографским минусом (русская типографика)."""
    s = f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"
    return s.replace(".", ",").replace("-", "−")


def comma_axis(ax, which: str = "y") -> None:
    f = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",").replace("-", "−"))
    if which in ("y", "both"):
        ax.yaxis.set_major_formatter(f)
    if which in ("x", "both"):
        ax.xaxis.set_major_formatter(f)


def save(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("написан", OUT / name)


# ---------------------------------------------------------------- 1. Парето E3
def fig_pareto() -> None:
    m = pd.read_csv(TAB / "e3_pareto_table.csv")
    m["rlabel"] = m.method.map(RU_LABEL).fillna(m.method)
    fr, dm = m[m.on_frontier], m[~m.on_frontier]

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.scatter(dm.viol, dm.epi, s=70, c="lightgrey", edgecolor="grey",
               zorder=2, label="доминируемые")
    ax.scatter(fr.viol, fr.epi, s=110, c="tab:red", edgecolor="k",
               zorder=3, label="фронт Парето (недоминируемые)")
    frs = fr.sort_values("viol")
    ax.plot(frs.viol, frs.epi, "--", color="tab:red", lw=1.2, alpha=0.7, zorder=1)
    ax.axhline(0, color="grey", lw=0.6, ls=":")

    OFFSET = {
        "grey_box_mpc": (8, -16), "sindy_mpc_dense": (8, 7), "nn_mpc": (8, 4),
        "oracle_mpc": (8, -14), "sindy_mpc_confirmatory": (8, 6),
        "sindy_mpc_conf_dagger": (-60, 9), "sac": (8, -4),
    }
    for _, r in m.iterrows():
        dx, dy = OFFSET.get(r.method, (6, 4))
        ax.annotate(r.rlabel, (r.viol, r.epi), fontsize=8.5,
                    xytext=(dx, dy), textcoords="offset points",
                    fontweight=("bold" if r.on_frontier else "normal"))
    gb = m[m.method == "grey_box_mpc"]
    if not gb.empty:
        ax.annotate("неразрежённый вариант ≈ «серый ящик»:\nкомпактность ≠ интерпретируемость",
                    (gb.viol.iloc[0], gb.epi.iloc[0]), fontsize=7.5, color="dimgray",
                    xytext=(-160, -52), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color="dimgray", lw=0.7))
    ax.set_xlim(right=float(m.viol.max()) * 1.18)
    ax.set_ylim(float(m.epi.min()) - 1.1, float(m.epi.max()) + 0.7)
    ax.set_xlabel("Число шагов с нарушениями ограничений за сезон (меньше — лучше)")
    ax.set_ylabel("Маржинальный доход за сезон $J$, евро/м$^2$ (больше — лучше)")
    ax.legend(loc="lower left", fontsize=8.5)
    ax.grid(alpha=0.3)
    comma_axis(ax, "y")
    save(fig, "e3_pareto_annotated.png")


# ------------------------------------------------------- 2. Варьирование λ, E3
def fig_lambda() -> None:
    a = pd.read_csv(TAB / "e3_lambda_sweep_table.csv").sort_values("lam")
    x = a["lam"].to_numpy()

    fig, axL = plt.subplots(figsize=(7.5, 5))
    axL.set_xscale("log")
    l1 = axL.plot(x, a["epi"], "o-", color="tab:blue",
                  label="маржинальный доход $J$ (замкнутый контур)")[0]
    axL.set_xlabel("Порог разреженности $\\lambda$")
    axL.set_ylabel("Маржинальный доход $J$ в замкнутом контуре, евро/м$^2$", color="tab:blue")
    axL.axhline(0, color="grey", lw=0.6, ls=":")
    axR = axL.twinx()
    l2 = axR.plot(x, a["rmse"], "s--", color="tab:red",
                  label="ошибка прогноза $T_{\\mathrm{in}}$ (разомкнутый контур)")[0]
    l3 = axR.plot(x, a["uBoil"] * 50.0, "^:", color="tab:green",
                  label="коэффициент котла $u_{\\mathrm{boil}}\\to T_{\\mathrm{in}}$, $\\times$50")[0]
    axR.set_ylabel("Ошибка прогноза, °C  /  коэффициент котла $\\times$50",
                   color="tab:red")
    axL.legend(handles=[l1, l2, l3], loc="lower left", fontsize=9)
    axL.grid(alpha=0.3)
    comma_axis(axL, "y")
    comma_axis(axR, "y")
    save(fig, "e3_lambda_sweep_ablation.png")


# ------------------------------------------- 3. Горизонт планирования (оракул)
def fig_oracle() -> None:
    g = pd.read_csv(TAB / "oracle_horizon_sweep.csv").sort_values("horizon_h")
    rb = float(g["rule_based_epi"].iloc[0])

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.axhline(rb, ls="--", color="tab:green", lw=1.8,
               label=f"эвристический регулятор ({ru(rb, 2, sign=True)})")
    ax.plot(g["horizon_h"], g["epi"], "o-", color="tab:blue", lw=2,
            label="УПМ с истинной моделью")
    for _, r in g.iterrows():
        dx, dy = (14, -16) if r["horizon_h"] == 6 else (0, 8)  # развести метки 3 ч и 6 ч
        ax.annotate(ru(r["epi"], 2, sign=True), (r["horizon_h"], r["epi"]),
                    textcoords="offset points", xytext=(dx, dy), fontsize=8, ha="center")
    ax.set_xlabel("Горизонт планирования, ч")
    ax.set_ylabel("Маржинальный доход $J$ за 14 сут, евро/м$^2$")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    comma_axis(ax, "y")
    save(fig, "oracle_horizon_sweep.png")


# ------------------------------------------------- 4. Обобщение и детекция E5
MONTH_RU = {"01": "янв.", "03": "март", "07": "июль", "10": "окт."}


def season_ru(s: str) -> str:
    y, md = s.split(":")
    return f"{MONTH_RU.get(md[:2], md[:2])} {y}"


def roc_curve_auc(y: np.ndarray, score: np.ndarray):
    o = np.argsort(-score)
    y = np.asarray(y, dtype=float)[o]
    P, N = y.sum(), (1 - y).sum()
    tpr = np.concatenate([[0.0], np.cumsum(y) / P])
    fpr = np.concatenate([[0.0], np.cumsum(1 - y) / N])
    _trapz = getattr(np, "trapezoid", getattr(np, "trapz"))  # numpy 2.x / 1.x
    return fpr, tpr, float(_trapz(tpr, fpr))


def _concat(pattern: str) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in sorted(glob.glob(str(TAB / pattern)))
              if os.path.getsize(p) > 0]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fig_e5() -> None:
    mat = pd.read_csv(TAB / "e5_generalization_matrix.csv", index_col=0)
    grid = _concat("e5_grid_*.csv")
    roc = _concat("e5_roc_*.csv")

    m = np.isfinite(grid["maha"]) & np.isfinite(grid["rollout_rmse"])
    r = float(np.corrcoef(grid["maha"][m], grid["rollout_rmse"][m])[0, 1])
    if not roc.empty and roc["violation"].nunique() > 1:
        fpr, tpr, auc = roc_curve_auc(roc["violation"].to_numpy(), roc["ood"].to_numpy())
    else:
        fpr = tpr = np.array([0.0, 1.0]); auc = float("nan")

    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    im = ax[0].imshow(mat.values, aspect="auto", cmap="RdYlGn")
    ax[0].set_xticks(range(len(mat.columns)), [season_ru(c) for c in mat.columns],
                     rotation=30, ha="right", fontsize=8)
    ax[0].set_yticks(range(len(mat.index)), [season_ru(i) for i in mat.index], fontsize=8)
    ax[0].set_xlabel("Сезон применения")
    ax[0].set_ylabel("Сезон обучения")
    ax[0].set_title("а) Обобщение: маржинальный доход $J$ (обучение $\\to$ тест)")
    fig.colorbar(im, ax=ax[0])
    ax[1].scatter(grid["maha"], grid["rollout_rmse"], color="tab:blue")
    ax[1].set_xlabel("Расстояние Махаланобиса")
    ax[1].set_ylabel("Ошибка многошагового прогноза, °C")
    ax[1].set_title(f"б) Сигнал — ошибка прогноза, $r = {ru(r, 2)}$")
    ax[1].grid(alpha=0.3)
    comma_axis(ax[1], "both")
    ax[2].plot(fpr, tpr, color="tab:blue")
    ax[2].plot([0, 1], [0, 1], "k--", lw=0.8)
    ax[2].set_xlabel("Доля ложных срабатываний")
    ax[2].set_ylabel("Доля верных срабатываний")
    ax[2].set_title(f"в) ROC-кривая детектора, AUC = {ru(auc, 2)}")
    ax[2].grid(alpha=0.3)
    comma_axis(ax[2], "both")
    save(fig, "e5_generalization.png")
    print(f"   r(Махаланобис, RMSE) = {r:.3f}; AUC = {auc:.3f}")


# ----------------------------------------------------- 5. Чувствительность E6
FACTOR_RU = {
    "mpc_horizon": "горизонт УПМ",
    "stlsq_threshold": "порог разреженности $\\lambda$",
    "coef_uncertainty": "возмущение коэффициентов\nсуррогатной модели",
    "fruit_price": "цена плодов",
    "energy_price": "цена энергии",
    "co2_price": "цена CO$_2$",
}


def fig_e6() -> None:
    tornado = pd.read_csv(TAB / "e6_tornado.csv").sort_values("range")
    price = pd.read_csv(TAB / "e6_price_sensitivity.csv")
    e3 = pd.read_csv(TAB / "e3_seeded.csv")
    meth = "sindy_mpc" if "sindy_mpc" in set(e3.method) else "sindy_mpc_confirmatory"
    base = float(e3[e3.method == meth]["epi"].mean())

    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    y = np.arange(len(tornado))
    ax[0].barh(y, tornado["high"] - tornado["low"], left=tornado["low"], color="steelblue")
    ax[0].axvline(base, color="k", ls="--", lw=1,
                  label=f"базовое значение $J$ = {ru(base, 2)}")
    ax[0].set_yticks(y, [FACTOR_RU.get(f, f) for f in tornado["factor"]])
    ax[0].set_xlabel("Маржинальный доход $J$, евро/м$^2$")
    ax[0].set_title("а) Размах $J$ по факторам (SINDy-УПМ)")
    ax[0].legend(fontsize=9)
    comma_axis(ax[0], "x")
    for meth_i in ["rule_based", "grey_box_mpc", "sindy_mpc", "nn_mpc", "oracle_mpc"]:
        d = price[(price.price == "energy") & (price.method == meth_i)]
        if not d.empty:
            ax[1].plot(d["mult"], d["epi"], marker="o",
                       label=RU_LABEL.get(meth_i, meth_i))
    ax[1].set_xlabel("Множитель цены энергии")
    ax[1].set_ylabel("Маржинальный доход $J$, евро/м$^2$")
    ax[1].set_title("б) $J$ при изменении цены энергии")
    ax[1].grid(alpha=0.3)
    ax[1].legend(fontsize=8)
    comma_axis(ax[1], "both")
    save(fig, "e6_sensitivity.png")


# ------------------------------------------------------------- 6. Отказы E7
FAULT_RU = {
    "t_in_stuck": "залипание датчика $T_{\\mathrm{in}}$",
    "rh_offset": "смещение датчика RH",
    "uVent_dead": "отказ вентиляции",
    "t_in_offset": "смещение датчика $T_{\\mathrm{in}}$",
    "uLamp_dead": "отказ досветки",
    "uBoil_stuck": "залипание котла",
}


def fig_e7() -> None:
    tab = pd.read_csv(TAB / "e7_degradation.csv").sort_values("viol_unsup", ascending=False)
    base_viol = float(tab["baseline_viol"].iloc[0])

    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(tab)); w = 0.38
    ax.bar(x - w / 2, tab["viol_unsup"], w, label="без супервизора")
    ax.bar(x + w / 2, tab["viol_sup"], w, label="с супервизором")
    ax.axhline(base_viol, color="k", ls="--", lw=1,
               label=f"без отказов ({base_viol:.0f})")
    ax.set_xticks(x, [FAULT_RU.get(f, f) for f in tab["fault"]], rotation=25, ha="right")
    ax.set_ylabel("Число шагов с нарушениями ограничений")
    ax.legend(fontsize=9)
    save(fig, "e7_faults.png")


if __name__ == "__main__":
    fig_pareto()
    fig_lambda()
    fig_oracle()
    fig_e5()
    fig_e6()
    fig_e7()
    print("готово:", OUT)
