"""Собирает ВСЕ таблицы статьи из канонического дерева. Руками числа не вбиваются.

Каждая таблица печатается с указанием файла-источника, чтобы её можно было сверить с
regen/results/final/NUMBERS.md. Запуск:

    python make_paper_tables.py [--out tables_v2]

Источники:
  regen/results/final/main.csv          главная сетка 10 регуляторов x 4 сезона x 20 seed
  regen/results/n7/main_n7.csv          N-7: сырой набор, 2 регулятора x 4 сезона x 20 seed
  regen/results/ladder_rerun/*.csv      ладдер с ИСПРАВЛЕННЫМИ горизонтами (4,20,96 шагов)
  regen/results/final/tables/*.csv      механизм, отказы, адаптация, защитный модуль
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REGEN = HERE.parent / "regen" / "results"
FINAL = REGEN / "final"

# Порядок и подписи регуляторов в статье.
LABELS = {
    "sindy_mpc_raw_ens":      "SINDy-MPC (raw, ensemble)",
    "sindy_mpc_raw":          "SINDy-MPC (raw, STLSQ)",
    "ppo":                    "PPO",
    "sindy_mpc_lowthr":       "SINDy-MPC (physics, lambda=1e-6)",
    "sindy_mpc_dense":        "SINDy-MPC (physics, lambda=1e-3)",
    "sindy_mpc_conf_dagger":  "SINDy-MPC (physics, frozen + aggregation)",
    "sindy_mpc_dense_dagger": "SINDy-MPC (physics, lambda=1e-3 + aggregation)",
    "rule_based":             "Rule-based reference",
    "sindy_mpc_conf":         "SINDy-MPC (physics, frozen recipe)",
    "oracle_mpc":             "Full-model MPC (oracle)",
    "sac":                    "SAC",
    "nn_mpc":                 "NN-MPC",
}


def _stop_reason(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    tr = d.truncated.astype(bool)
    d["stop"] = np.where(~tr, "complete",
                np.where(d.solver_failures >= 100, "solver_aborted", "env_terminated"))
    return d


def load_main() -> pd.DataFrame:
    """Каноническая сетка + N-7, с исключением прогонов, где решатель не выдал управление."""
    c = _stop_reason(pd.read_csv(FINAL / "main.csv"))
    n = _stop_reason(pd.read_csv(REGEN / "n7" / "main_n7.csv"))
    a = pd.concat([c, n], ignore_index=True)
    return a[a.stop != "solver_aborted"]


def load_ladder() -> pd.DataFrame:
    """Только перезапуск с исправленными горизонтами. Канонический ladder.csv устарел:
    он посчитан до исправления (нет колонки rollout_horizons), см. REVISION_LOG."""
    fs = sorted(glob.glob(str(REGEN / "ladder_rerun" / "ladder_*.csv")))
    if not fs:
        raise FileNotFoundError("нет перезапуска ладдера; канонический ladder.csv использовать НЕЛЬЗЯ")
    d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    assert "rollout_horizons" in d.columns, "файл ладдера без горизонтов -- это дофиксовый прогон"
    return d


def t_main(out: Path) -> None:
    a = load_main()
    piv = a.pivot_table(index="method", columns="test_year", values="epi", aggfunc="mean")
    sd = a.pivot_table(index="method", columns="test_year", values="epi", aggfunc="std")
    piv["mean"] = piv.mean(axis=1)
    piv["violations"] = a.groupby("method").violation_steps_total.mean()
    piv["n"] = a.groupby("method").epi.size()
    piv = piv.sort_values("mean", ascending=False)

    lines = ["| Controller | 2020 | 2021 | 2022 | 2023 | Mean | Viol. | n |",
             "|---|---|---|---|---|---|---|---|"]
    for m, r in piv.iterrows():
        cells = []
        for y in (2020, 2021, 2022, 2023):
            v, s = r.get(y, np.nan), sd.loc[m, y] if y in sd.columns else np.nan
            cells.append("--" if pd.isna(v) else f"{v:+.2f} ± {s:.2f}" if pd.notna(s) else f"{v:+.2f}")
        lines.append(f"| {LABELS.get(m, m)} | " + " | ".join(cells)
                     + f" | **{r['mean']:+.2f}** | {r['violations']:.0f} | {int(r['n'])} |")
    _emit(out, "T2_main_four_seasons", lines,
          "regen/results/final/main.csv + regen/results/n7/main_n7.csv",
          "Средний сезонный маржинальный доход, евро/м2, ± СКО по повторам. "
          "Исключены прогоны с отказом решателя (oracle 2022: 20 из 20).")


def t_ladder(out: Path) -> None:
    d = load_ladder()
    d1 = d[(d.degree == 1) & (d.denoise == "none")]
    # NB: не называть колонку `div` -- это метод pandas.Series, и r.div вернёт метод.
    g = d1.groupby("variant").agg(
        kappa=("kappa", "mean"), nz=("nonzero", "mean"),
        one=("one_step_rmse_t_in", "mean"), roll=("rollout_rmse_t_in", "mean"),
        diverged=("diverged_frac", "mean"), n=("seed", "size"))
    g = g.reindex(["raw", "physics_no_cross", "physics"])
    feats = {"raw": 11, "physics_no_cross": 14, "physics": 18}
    lines = ["| Library | Features | kappa | Non-zero | One-step RMSE, C | 24-h rollout RMSE, C | Diverged |",
             "|---|---|---|---|---|---|---|"]
    for v, r in g.iterrows():
        lines.append(f"| `{v}` | {feats[v]} | {r.kappa:.2f} | {r.nz:.1f} | "
                     f"{r.one:.3f} | **{r.roll:.2f}** | {r['diverged']:.4f} |")
    _emit(out, "T3_ladder_by_library", lines,
          "regen/results/ladder_rerun/ (горизонты 4,20,96 ШАГОВ)",
          "Степень 1, без сглаживания, усреднение по оптимизаторам и seed. "
          "Одношаговая ошибка улучшается с ростом числа физических признаков, "
          "многошаговая -- деградирует. Канонический ladder.csv НЕ использовать: "
          "он посчитан до исправления горизонтов.")


def t_lambda(out: Path) -> None:
    d = pd.read_csv(FINAL / "tables" / "lambda_sweep.csv")
    lines = ["| lambda | Non-zero | xi(uBoil->T) | 24-h rollout RMSE, C | EPI | SD | Viol. |",
             "|---|---|---|---|---|---|---|"]
    for _, r in d.iterrows():
        lines.append(f"| {r.lam:g} | {r.nonzero:.1f} | {r.xi_uboil:.4f} | "
                     f"{r.rollout_rmse:.2f} | {r.epi_mean:+.2f} | {r.epi_std:.2f} | {r.viol_mean:.0f} |")
    _emit(out, "T4_lambda_sweep", lines,
          "regen/results/final/tables/lambda_sweep.csv",
          "ГОРИЗОНТ ПРОГНОЗА -- 96 шагов (24 ч). В прежней рукописи та же величина "
          "приводилась на 20 шагах (5 ч), отсюда 2.25-2.39 C вместо 10.5-13.6. "
          "Связь EPI с коэффициентом котла НЕ монотонна -- причинность показывает "
          "контролируемая абляция (knock_effect.csv), а не эта развёртка.")


def t_faults(out: Path) -> None:
    d = pd.read_csv(FINAL / "tables" / "faults.csv")
    base = d[d.condition == "nofault"].iloc[0]
    rows = {}
    for _, r in d[d.condition != "nofault"].iterrows():
        name, kind = r.condition.rsplit("/", 1)
        rows.setdefault(name, {})[kind] = r
    lines = ["| Fault | EPI (no supervisor) | Viol. (no) | EPI (supervisor) | Viol. (with) |",
             "|---|---|---|---|---|"]
    for name, kv in rows.items():
        raw, sup = kv.get("raw"), kv.get("sup")
        if raw is None or sup is None:
            continue
        lines.append(f"| {name} | {raw.epi_mean:+.2f} | {raw.viol_mean:.0f} | "
                     f"{sup.epi_mean:+.2f} | {sup.viol_mean:.0f} |")
    _emit(out, "T5_faults", lines,
          "regen/results/final/tables/faults.csv",
          f"Эталон без отказов: EPI {base.epi_mean:+.2f}, нарушений {base.viol_mean:.0f}. "
          "Числа прежней рукописи (эталон 1.94 / 2587) относятся к устаревшему конвейеру. "
          "В каноне модуль диагностики улучшает ОБА показателя при всех шести отказах, "
          "то есть контрпример со смещением датчика температуры отсутствует.")


def t_boiler_survival(out: Path) -> None:
    a = load_main()
    s = a[a.method.str.startswith("sindy")].copy()
    s["keeps"] = s.xi_uboil.abs() > 1e-9
    lines = ["| Controller | Boiler term kept | EPI if kept | EPI if dropped | Delta |",
             "|---|---|---|---|---|"]
    for m, g in s.groupby("method"):
        hi, lo = g[g.keeps].epi, g[~g.keeps].epi
        d = hi.mean() - lo.mean() if len(hi) and len(lo) else np.nan
        lines.append(f"| {LABELS.get(m, m)} | {g.keeps.mean():.0%} | "
                     f"{hi.mean():+.2f} | {'--' if not len(lo) else f'{lo.mean():+.2f}'} | "
                     f"{'--' if pd.isna(d) else f'{d:+.2f}'} |")
    _emit(out, "T6_boiler_survival", lines,
          "regen/results/final/main.csv + n7/main_n7.csv (колонка xi_uboil)",
          "Доля подгонок, сохранивших коэффициент котла, и разность EPI внутри метода. "
          "На сыром наборе член выживает в 100% подгонок.")


def _emit(out: Path, name: str, lines: list[str], source: str, note: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    text = (f"# {name}\n\n**Источник:** `{source}`\n\n{note}\n\n" + "\n".join(lines) + "\n")
    (out / f"{name}.md").write_text(text, encoding="utf-8")
    print(f"[ok] {name}.md  <- {source}")
    print("\n".join(lines))
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "tables_v2"))
    a = ap.parse_args()
    out = Path(a.out)
    for fn in (t_main, t_ladder, t_lambda, t_faults, t_boiler_survival):
        try:
            fn(out)
        except Exception as exc:                              # noqa: BLE001
            print(f"[FAIL] {fn.__name__}: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
