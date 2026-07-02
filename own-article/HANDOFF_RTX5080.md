# Handoff prompt — продолжение работы над экспериментами теплицы (новая машина, RTX 5080)

> Вставь весь текст ниже первым сообщением новому агенту Claude Code на машине с RTX 5080.

---

Ты — опытный учёный-программист. Продолжаешь чужую (мою предыдущую) работу над
**вычислительными экспериментами по интерпретируемому MPC-управлению микроклиматом
теплицы** поверх симулятора GreenLight-Gym2. Сначала выполни обязательную
инициализацию памяти из `~/.claude/CLAUDE.md` (протокол gorness-mem: `candidates_list`
min_confidence 0.8 + подтвердить; `memory_context` по первому запросу). В памяти
проекта (scope `project:greenhouse-control`) уже лежат ключевые решения — подними их.

## 1. Что это за проект и цель
- Тема: **data-efficient интерпретируемое SINDy-MPC** управление теплицей; все
  утверждения in-silico на `gl_gym/GreenLightTomato-v0`.
- Полный план — `own-article/EXPERIMENT_PROTOCOL.md` (эксперименты E0–E8, гипотезы
  Г1–Г4). **Прочитай его.**
- Локация: **Ростов-на-Дону 2018–2023**, реальная погода ERA5. Первичная метрика —
  **EPI** (экономический показатель, €/м²·сезон).

## 2. Что уже сделано (НЕ переделывай)
Реализовано и провалидировано **ядро E0–E3** (E4–E8 — следующий заход):
- `own-article/protocol_config.py` — единый конфиг (Rostov, сплиты train=2018-19/
  test=2020/OOD=2021-23, бюджеты, сиды, HP-бюджет, FAST_MODE) + `read_env_economics()`
  читает цены/коридоры с живого env.
- `own-article/article_experiment_utils.py` — весь хелпер: сбор данных с EPI и PRBS,
  `epi_metrics`, лестница `fit_sindy` (optimizer∈{stlsq,sr3,ensemble,constrained},
  denoise∈{none,savgol,kalman}, library, degree), шлюзы `mpc_embeddability_gate`/
  `transparency_gate`, `rollout_oracle_mpc` (CEM по истинной модели), `train_rl`/
  `rollout_rl` (PPO/SAC), `paired_stats` (Wilcoxon+Holm+bootstrap).
- Ноутбуки `own-article/E0..E3_*.ipynb` + `run_all_notebooks.py`.
- **Смоук (ARTICLE_FAST=1) зелёный на всех 4 ноутбуках.** Статейные E0/E1 уже
  считались (EPI rule-based 60 сут Ростов-2020 = **1.64 €/м²**; κ-кривая 95→40).
  **E2/E3 в статейном масштабе НЕ досчитаны** — это и есть задача (см. §6).

## 3. Где код и данные
- **Код:** репозиторий `https://github.com/chernyaevantont-tech/greenhouse-control`,
  ветка `main` (HEAD `7353422`, весь мой код уже здесь). Работай в `own-article/`.
  → `git clone` на новой машине.
- **gl_gym + погода Ростова:** пакет gl_gym из репо GreenLight-Gym2
  (`https://github.com/mlyashov/greenlight`, ветка `anton`, `be19dba`). **ВАЖНО:**
  погодные CSV Ростова (`gl_gym/data/weather/Rostov-on-Don/{2018..2023}.csv`, ~55 МБ,
  6 файлов) **НЕ закоммичены ни в один remote** — они есть только в моей локальной
  копии. Поэтому:
  - **Скопируй папку `GreenLight-Gym2` целиком со старой машины на новую**
    (со старой: `C:\Users\zergu\repos\greenlight\GreenLight-Gym2`), она содержит и код
    gl_gym, и данные Ростова. (Клонировать mlyashov/greenlight НЕДОСТАТОЧНО — там нет
    Ростова, и ветка может отличаться.)
- **Почва Ростова:** `own-article/rostov_soil.py` (приходит с git). `apply_rostov_soil()`
  уже зашит в `_make_env` (применяется автоматически для location, начинающейся с
  "Rostov", до загрузки погоды).

## 4. Настройка окружения на новой машине
Старое рабочее окружение: uv-venv, Python 3.14. Воспроизведи (Python 3.12+ годится).
Менеджер — **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

```bash
# 1) venv
cd <repo>/greenhouse-control
uv venv --python 3.12 .venv          # путь к GreenLight-Gym2 подставь свой ниже
PY=.venv/bin/python                  # Windows: .venv/Scripts/python.exe

# 2) torch. Workload CPU-bound -> CPU-torch достаточно. Для RTX 5080 (Blackwell,
#    sm_120) GPU-сборка нужна cu128+ (torch>=2.7). ОПЦИОНАЛЬНО:
uv pip install --python $PY torch --index-url https://download.pytorch.org/whl/cu128

# 3) остальной стек (точные версии, проверены). ВАЖНО про numpy: pysindy==2.1.0
#    в метаданных требует numpy>=2.0, но реально РАБОТАЕТ на numpy 1.26.4 (его нужно
#    для casadi/do-mpc/gl_gym). Поэтому pysindy ставим ОТДЕЛЬНО с --no-deps, иначе
#    резолвер ругнётся "unsatisfiable". И пин torch==<ver>, чтобы uv не передёрнул
#    GPU-torch на CPU из PyPI.
uv pip install --python $PY -e <path>/GreenLight-Gym2 torch==<installed_ver> \
  numpy==1.26.4 pandas==2.3.3 scipy==1.17.1 scikit-learn==1.8.0 matplotlib==3.10.8 \
  casadi==3.7.2 do-mpc==5.1.1 gymnasium==1.2.3 stable-baselines3==2.9.0 \
  derivative==0.6.3 nbformat==5.10.4 nbclient==0.11.0 ipykernel
uv pip install --python $PY --no-deps pysindy==2.1.0

# 4) зарегистрировать kernel (run_all_notebooks использует kernel_name="python3")
$PY -m ipykernel install --user --name python3
```

Проверка: `$PY -c "import torch,gl_gym,pysindy,do_mpc,casadi,stable_baselines3,nbclient; print(torch.cuda.is_available())"`
и `$PY -c "import protocol_config as P; print(P.read_env_economics()['corridors'])"`
(из `own-article/`) — должно вернуть корридоры CO2/T/RH.

## 5. Как запускать
Из `own-article/`. `FAST_MODE` берётся из env `ARTICLE_FAST` (1=смоук, 0=статейный).
```bash
ARTICLE_FAST=1 $PY run_all_notebooks.py        # смоук ~6 мин, проверить что всё зелёное
ARTICLE_FAST=0 $PY run_all_notebooks.py        # статейный прогон (часы)
ARTICLE_FAST=0 $PY run_all_notebooks.py E2_identification_ladder.ipynb   # один ноутбук
```
Артефакты → `own-article/results_scenarios/{tables,figures,datasets}` + `protocol.json`
+ `recipe_frozen.json`. Долгие прогоны запускай в фоне с логом и опрашивай лог.

## 6. Задача на новой машине
**Досчитать статейный масштаб (ARTICLE_FAST=0) E0→E3 и собрать результаты:**
- E2: таблица абляции `e2_ladder.csv` + заморозка рецепта `recipe_frozen.json`
  (на старой машине смоук-рецепт = physics/STLSQ/savgol).
- E3 — **главный и самый долгий**: 10 сидов × {rule_based, sindy_mpc, grey_box_mpc,
  nn_mpc, ppo, sac, oracle_mpc}. Узкие места: **oracle CEM ~1.2 c/шаг** (60 сут ≈
  ~2 ч/сид — в коде oracle идёт на сокращённом числе сидов `oracle_seeds=seeds[:1]`),
  RL 200k шагов × (ppo+sac) × `rl_seeds=seeds[:3]`. Итог: главная таблица
  `e3_main_table.csv` (EPI mean±std, разрыв до oracle), `e3_stats_vs_rulebased.csv`
  (Wilcoxon+Holm+CI), Парето-рисунок.
- Если по времени тяжело — можно временно поднять/опустить число сидов в
  `protocol_config.py` (`seeds`, `oracle_seeds`/`rl_seeds` в E3-ноутбуке), но для
  валидной статистики нужно ≥10 сидов.

## 7. Критические нюансы (УЖЕ исправлены в коде — не ломай, не «чини» заново)
- Среда новее протокольных пинов → код адаптирован: sklearn 1.8 (`squared=False`
  убран → `np.sqrt(mean_squared_error)`), pysindy 2.1 (`feature_names` теперь в
  `model.fit`, SR3 — `reg_weight_lam`/`relax_coeff_nu`, TrappingSR3 нет → используем
  ConstrainedSR3), do-mpc/Ipopt заглушены (`nlpsol_opts`), SB3 — `MultiInputPolicy`
  (obs env — Dict).
- uv-venv без pip → ставить только через `uv pip install --python <venv>`.

## 8. Архитектурные решения (НЕ изобретать заново; подробности — в памяти проекта)
- **EPI = Σ `info["profit"]`** из `env.step` (gl_gym GreenhouseReward); выручка/затраты
  декомпозируются из того же info; коридоры/цены — с живого env (`read_env_economics`).
- **oracle-MPC = CEM по `env.unwrapped.F`** (истинный casadi-интегратор симулятора).
  Встраивание F в do-mpc как discrete model технически работает, но Ipopt с
  чувствительностями недопустимо медленный — ОТВЕРГНУТО.
- **grey-box-MPC = `fit_sindy(feature_variant="physics_no_cross", threshold≈1e-6)`**
  (плотная редуцированная линейная физика) — переиспользует существующий MPC.
- **Дисперсия E3 — пересбор train на каждом сиде** (суррогат переобучается), а не
  только seed прогона (чинит претензию протокола к старому `07_multi_seed`).
- **Рецепт идентификации замораживается** в `recipe_frozen.json` ДО E3
  (предрегистрация против цикличности).
- Индексы состояния модели x (28-мерн.): `x[2]`=tAir(°C), `x[0]`=co2 density (→ppm),
  `x[15]`=vapor pressure (→RH), `x[25]`=fruit DM.

## 9. GPU-замечание (RTX 5080)
Тяжёлый счёт здесь **CPU-bound** (Ipopt-MPC, CEM-oracle по casadi, SINDy-фиты).
GPU нагружают только PPO/SAC и NN-суррогат, а сети крошечные (64×64) — выигрыш
маргинальный, узкое место — шаги среды (CPU). Так что RTX 5080 ускорит немного;
главный ресурс — многоядерный CPU. CPU-torch полностью рабочий вариант.
