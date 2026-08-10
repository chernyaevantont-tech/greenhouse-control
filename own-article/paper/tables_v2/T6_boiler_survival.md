# T6_boiler_survival

**Источник:** `regen/results/final/main.csv + n7/main_n7.csv (колонка xi_uboil)`

Доля подгонок, сохранивших коэффициент котла, и разность EPI внутри метода. На сыром наборе член выживает в 100% подгонок.

| Controller | Boiler term kept | EPI if kept | EPI if dropped | Delta |
|---|---|---|---|---|
| SINDy-MPC (physics, frozen recipe) | 15% | -0.80 | -1.34 | +0.54 |
| SINDy-MPC (physics, frozen + aggregation) | 75% | +0.41 | -1.71 | +2.11 |
| SINDy-MPC (physics, lambda=1e-3) | 100% | +0.34 | -- | -- |
| SINDy-MPC (physics, lambda=1e-3 + aggregation) | 100% | -0.36 | -- | -- |
| SINDy-MPC (physics, lambda=1e-6) | 100% | +0.41 | -- | -- |
| SINDy-MPC (raw, STLSQ) | 50% | +4.34 | +2.90 | +1.44 |
| SINDy-MPC (raw, ensemble) | 55% | +4.51 | +3.54 | +0.97 |
