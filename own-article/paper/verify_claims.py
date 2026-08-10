"""Независимая перепроверка заявленных чисел — из сырых файлов, без промежуточных скриптов."""
import glob
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

R = "C:/Users/zergu/repos/greenhouse-control/own-article/regen/results/"
ok = []


def chk(name, got, want, tol=0.02):
    good = abs(got - want) <= tol
    ok.append(good)
    print(f"  [{'OK ' if good else 'РАСХОЖДЕНИЕ'}] {name}: получено {got:+.3f}, заявлено {want:+.3f}")


print("=" * 74)
print("1. N-7: сырой набор")
n = pd.read_csv(R + "n7/main_n7.csv")
assert len(n) == 160 and n.seed.nunique() == 20, (len(n), n.seed.nunique())
re_ = n[n.method == "sindy_mpc_raw_ens"]
chk("raw_ens среднее по 4 сезонам", re_.groupby("test_year").epi.mean().mean(), 4.07)
chk("raw среднее", n[n.method == "sindy_mpc_raw"].groupby("test_year").epi.mean().mean(), 3.62)
print(f"  усечённых у N-7: {int(n.truncated.astype(bool).sum())} (заявлено 0)")
ok.append(n.truncated.astype(bool).sum() == 0)

print()
print("2. Побеждает ли raw_ens во всех четырёх сезонах")
c = pd.read_csv(R + "final/main.csv")
c = c[~(c.truncated.astype(bool) & (c.solver_failures >= 100))]
a = pd.concat([c, n], ignore_index=True)
wins = 0
for y, g in a.groupby("test_year"):
    m = g.groupby("method").epi.mean().sort_values(ascending=False)
    first = m.index[0]
    wins += first == "sindy_mpc_raw_ens"
    print(f"  {y}: {first} {m.iloc[0]:+.2f}")
print(f"  побед raw_ens: {wins}/4 (заявлено 4/4)")
ok.append(wins == 4)

print()
print("3. Парный критерий raw_ens против PPO (80 пар)")
k = ["seed", "test_year"]
b = n[n.method == "sindy_mpc_raw_ens"].set_index(k).epi
p = a[a.method == "ppo"].set_index(k).epi
i = b.index.intersection(p.index)
d = b.loc[i] - p.loc[i]
st, pv = wilcoxon(d)
print(f"  n={len(i)} Δсред={d.mean():+.3f} выигрышей={int((d>0).sum())} p={pv:.2e}")
chk("Δ против ppo", d.mean(), 3.62)
ok.append(pv < 1e-9)

print()
print("4. Разложение 2x2 (библиотека x член котла)")
s = a[a.method.isin(["sindy_mpc_raw_ens", "sindy_mpc_conf"])].copy()
s["keeps"] = s.xi_uboil.abs() > 1e-9
s["lib"] = np.where(s.method.str.contains("raw"), "raw", "phys")
m = s.groupby(["lib", "keeps"]).epi.mean()
chk("эффект члена внутри raw", m[("raw", True)] - m[("raw", False)], 0.97)
chk("эффект члена внутри phys", m[("phys", True)] - m[("phys", False)], 0.54)
chk("эффект библиотеки при сохранённом", m[("raw", True)] - m[("phys", True)], 5.31)
chk("эффект библиотеки при удалённом", m[("raw", False)] - m[("phys", False)], 4.88)

print()
print("5. Ладдер: порядок по числу обусловленности")
lad = pd.concat([pd.read_csv(f) for f in glob.glob(R + "ladder_rerun/ladder_*.csv")],
                ignore_index=True)
d1 = lad[(lad.degree == 1) & (lad.denoise == "none")]
g = d1.groupby("variant").kappa.mean()
print(f"  raw={g['raw']:.2f} phys_no_cross={g['physics_no_cross']:.2f} physics={g['physics']:.2f}")
ok.append(g["raw"] < g["physics_no_cross"] < g["physics"])
print(f"  монотонность κ: {'ОК' if ok[-1] else 'НАРУШЕНА'}")

print()
print("6. N-2: настроенная эвристика")
t = pd.read_csv(R + "n2_tune/tune_rb_n2.csv")
tt = t[t.block == "tuned_test"].groupby("test_year").epi.mean()
ss = t[t.block == "stock_test"].groupby("test_year").epi.mean()
chk("настроенная, среднее", tt.mean(), 2.26)
chk("зашитая, среднее", ss.mean(), -1.23)

print()
print("=" * 74)
print("7. ПЕРЕСЧЁТ, КОТОРЫЙ Я ПОМЕТИЛ КАК ДОЛГ:")
print("   парные критерии против НАСТРОЕННОГО эталона, а не зашитого")
print("=" * 74)
tuned = t[t.block == "tuned_test"].set_index("test_year").epi
rows = []
for meth, g in a.groupby("method"):
    per = g.groupby(["seed", "test_year"]).epi.mean().reset_index()
    per["ref"] = per.test_year.map(tuned)
    dd = per.epi - per.ref
    if dd.isna().any() or len(dd) < 10:
        continue
    try:
        _, pv = wilcoxon(dd)
    except ValueError:
        pv = np.nan
    rows.append((meth, len(dd), dd.mean(), int((dd > 0).sum()), pv))
rr = pd.DataFrame(rows, columns=["метод", "n", "Δ", "выигр", "p"]).sort_values("Δ", ascending=False)
rr["p_holm"] = np.minimum(1, rr.p * (len(rr) - np.arange(len(rr))))
print(rr.to_string(index=False, float_format=lambda v: f"{v:.3g}"))

print()
print("=" * 74)
print(f"ИТОГ ПРОВЕРКИ: {sum(ok)}/{len(ok)} сошлось")
