# Physics-Informed SINDy + MPC Greenhouse Control

Этот репозиторий содержит исследовательский прототип контроллера теплицы:
модель динамики строится из данных симулятора GreenLight-Gym2 методом
Physics-Informed SINDy, после чего встраивается в нелинейный MPC-контроллер на
`do-mpc`/CasADi. В качестве цифровой теплицы используется среда
`gl_gym/GreenLightTomato-v0`, основанная на модели GreenLight.

Главный исследовательский артефакт проекта - `physics_informed_mpc.ipynb`.
Вынесенный код в `greenhouse_mvp/` превращает notebook-пайплайн в приложение:
FastAPI-сервер запускает симуляцию, контроллер, OOD-мониторинг, опциональный
LLM-супервизор и web-dashboard.

## Идея статьи

По структуре удобнее ориентироваться на статью iGrow: сначала сформулировать
задачу автономного управления теплицей, затем описать симулятор, модель
динамики, контроллер, замкнутый цикл и экспериментальную валидацию. Отличие
этой работы от iGrow можно подать так:

- iGrow строит автономное управление через MDP, нейросетевой симулятор и
  bi-level optimization.
- Здесь используется более интерпретируемая связка: GreenLight-Gym2 как
  физически обоснованный симулятор, Physics-Informed SINDy как разреженная
  суррогатная модель, MPC как constrained optimizer.
- Главная заявка: получить data-driven контроллер, который остается
  физически интерпретируемым и пригодным для включения инженерных ограничений.

## Симулируемая система

Симулятор: `gl_gym/GreenLightTomato-v0`.

Период дискретизации: `900` секунд, то есть 15 минут. Один день содержит
`96` шагов. Базовые эксперименты в notebook и Docker-конфигурации используют
стартовую дату `2010-02-28`, сезон длиной `60` дней и горизонт MPC `20` шагов
(5 часов).

Управляемые состояния:


| Обозначение | Смысл | Единицы |
| --- | --- | --- |
| `t_in` | температура воздуха внутри теплицы | deg C |
| `co2` | концентрация CO2 внутри теплицы | ppm |
| `rh` | относительная влажность | % |

Внешние возмущения и time-varying parameters для MPC:

| Обозначение | Смысл |
| --- | --- |
| `T_out` | наружная температура |
| `rad` | солнечная радиация |
| `co2_out` | наружная концентрация CO2 |
| `sin_h`, `cos_h` | циклическое кодирование времени суток |

Актуаторы нормализованы в диапазон `[0, 1]`:

| Актуатор | Смысл |
| --- | --- |
| `uBoil` | отопление/котел |
| `uCO2` | подача CO2 |
| `uThScr` | тепловой экран |
| `uVent` | вентиляция |
| `uLamp` | досветка |
| `uBlScr` | blackout screen |

## Обучение SINDy-модели

Первичные данные собираются из GreenLight-Gym2 при помощи rule-based
контроллера `RuleBasedController`. Чтобы SINDy увидела более широкий диапазон
действий, к базовым действиям добавляется гауссов шум:

- `NOISE_SCALE = 0.1`
- `NOISE_PERIOD = 5`

Сырые траектории переводятся в пары:

```text
x_k     = [t_in, co2, rh]_k
u_k     = physics_features(x_k, weather_k, time_k, action_k)
x_{k+1} = [t_in, co2, rh]_{k+1}
```

Модель обучается в дискретной next-step постановке:

```text
x_{k+1} = Xi^T * Theta(x_k, u_k)
```

В коде состояния и physics-features масштабируются раздельными
`StandardScaler`. Далее используется `pysindy.SINDy` с:

- `STLSQ(threshold=0.05, alpha=0.01)`
- `PolynomialLibrary(degree=1, include_bias=True)`

Так как нелинейность вынесена в заранее вычисленные физические признаки,
библиотека SINDy остается линейной по признакам. Это снижает риск
мультиколлинеарности и сохраняет интерпретируемость коэффициентов.

## Physics-informed признаки

Ключевая идея - не давать SINDy произвольную полиномиальную библиотеку высокой
степени, а вручную добавить физически осмысленные нелинейности:

| Признак | Формула | Смысл |
| --- | --- | --- |
| `psat` | `0.6108 * exp(17.27 * t_in / (t_in + 237.3))` | давление насыщенного пара |
| `vpd` | `(1 - rh / 100) * psat` | vapor pressure deficit |
| `S_eff` | `rad * (1 - uThScr)` | эффективный солнечный приток через экран |
| `t_S_eff` | `t_in * S_eff` | связь температуры и солнечного притока |
| `h_uVent` | `rh * uVent` | осушение вентиляцией |
| `dc_uVent` | `(co2 - co2_out) * uVent` | потеря CO2 через вентиляцию |
| `t_uBoil` | `t_in * uBoil` | тепловая связь температуры и отопления |

Полный вектор `u` для SINDy содержит 18 признаков:

```text
[T_out, rad, co2_out, sin_h, cos_h,
 uBoil, uCO2, uThScr, uVent, uLamp, uBlScr,
 psat, vpd, S_eff,
 t_S_eff, h_uVent, dc_uVent, t_uBoil]
```

Важное методическое решение: `dT = T_out - t_in` и
`dc_ext = co2 - co2_out` не добавляются как отдельные признаки, потому что при
наличии `T_out`, `t_in`, `co2`, `co2_out` они создают точные линейные
зависимости после нормализации. `dc_ext` используется только внутри
нелинейного произведения `dc_uVent`.

## MPC-контроллер

SINDy-модель встраивается в `do_mpc.model.Model("discrete")` как CasADi-граф.
На каждом шаге MPC:

1. получает текущие `t_in`, `co2`, `rh`;
2. получает forecast-window для `T_out`, `rad`, `co2_out`, `sin_h`, `cos_h`;
3. символьно вычисляет physics-features;
4. нормализует `x` и `u` теми же scaler-параметрами, что использовались при
   обучении SINDy;
5. строит `Theta = [1, x_scaled, u_scaled]`;
6. вычисляет `x_next_scaled = coefficients @ Theta`;
7. возвращает предсказание в физические единицы;
8. решает MPC-задачу на горизонте 20 шагов.

В финальном notebook-варианте objective нормирует разные физические величины:

```text
err_T   = (t_in - 20.0) / 5.0
err_co2 = (co2 - 800.0) / 200.0
err_rh  = max(0, rh - 85.0) / 5.0

lterm = 100 * err_T^2
      +  30 * err_co2^2
      +  50 * err_rh^2
      +  20 * uBoil
      +  10 * uLamp
      +   2 * uCO2
```

Ограничения:

- все актуаторы: `[0, 1]`;
- вентиляция в зимнем сценарии: `uVent <= 0.4`;
- температура: примерно `12 <= t_in <= 35` deg C в финальном notebook-варианте.

## DAgger / dataset aggregation

В notebook есть DAgger-цикл:

1. начальная SINDy-модель обучается на данных rule-based controller + noise;
2. текущая SINDy-MPC политика запускается в GreenLight-Gym2;
3. новые траектории `x_k, u_k, x_{k+1}` добавляются к обучающему набору;
4. scaler и SINDy-модель переобучаются на агрегированных данных;
5. контроллер пересобирается с обновленной SINDy-моделью.

Это хороший экспериментальный блок для статьи: он показывает, как контроллер
выходит за пределы демонстрационных траекторий rule-based controller и
постепенно улучшает суррогатную модель в области, где сам MPC принимает
решения.

## OOD-мониторинг и LLM-супервизор

В `greenhouse_mvp/` добавлен прикладной слой безопасности. После обучения
сохраняются статистики обучающего распределения, а в online-режиме считается
Mahalanobis distance. Если состояние/признаки выходят за обучающее
распределение, LangGraph может отправить действие MPC на LLM-супервизора.

Логика workflow:

```text
telemetry -> MPC or LLM controller -> OOD check
          -> optional supervisor review
          -> approve / override / replan
          -> env.step(action)
```

Для статьи этот блок лучше позиционировать как инженерное расширение к
основному методу, а не как центральный вклад, если эксперименты с LLM еще не
валидированы количественно.

## Архитектура приложения

Текущая сервисная версия работает в одном FastAPI-процессе:

- `greenhouse_mvp.sindy_pipeline.bootstrap` создает `sindy_model.pkl`;
- `greenhouse_mvp.api.simulation_runner` запускает GreenLight-Gym2 в фоне;
- `greenhouse_mvp.control_core.mpc_controller` решает MPC;
- `greenhouse_mvp.orchestration.graph_workflow` управляет approve/reject/override;
- `dashboard/` показывает telemetry, actuators, weather, OOD и настройки.

Запуск через Docker Compose:

```bash
docker compose up --build
```

После запуска:

- API: `http://localhost:8000`
- dashboard: `http://localhost:8080`

## Важные замечания по текущей реализации

Есть расхождения между notebook-версией и сервисным кодом:

- `physics_informed_mpc.ipynb` содержит более полный финальный objective:
  температура + CO2 + влажность + энергозатраты.
- `greenhouse_mvp/control_core/mpc_controller.py` сейчас использует более
  простой objective: температура + штрафы на `uBoil` и `uLamp`, с более
  широкими bounds `5 <= t_in <= 45`.
- В сервисном `_compute_ood()` вызов `compute_physics_features` сейчас не
  совпадает с сигнатурой функции из `sindy_pipeline/physics_features.py`.
  Исключение перехватывается, поэтому OOD может возвращать safe default вместо
  реальной метрики. Перед статьей и экспериментами это стоит поправить.
- Сервисный DAgger-путь в `graph_workflow.py` выглядит экспериментальным и
  требует проверки: там тоже есть рассинхрон с API `compute_physics_features`
  и `SINDyFitter.fit`.

Для статьи лучше считать notebook основным источником методологии, а
`greenhouse_mvp/` - прототипом демонстрационной системы, который надо довести
до полного совпадения с notebook перед финальными экспериментами.

## Литература в `articles/`

Главный структурный ориентир:

- `21440-13-25453-1-2-20220628.pdf` - iGrow: A Smart Agriculture Solution to
  Autonomous Greenhouse Control. Использовать как ориентир по построению
  статьи: постановка AGC, симулятор/testbed, алгоритм, real-world validation,
  comparison.

Уже лежавшие полезные источники:

- `!!!Interpretable_modelling_of_greenhouse_environment_through_SINDy.pdf` -
  прямой источник по SINDy для greenhouse environment.
- `!!!!!!prediction_and_control_of_greenhouse_temperature_wageningen.pdf` -
  свежий обзор методов prediction/control для температуры теплиц.
- `paper_10.47978@TUS.2024.74.01.001.pdf` - короткая статья по MPC для
  greenhouse management.

Добавленные PDF-источники:

- `greenlight_gym_van_laatum_2025_ifac.pdf` - GreenLight-Gym/GreenLight-Gym2,
  основной источник по выбранному симулятору.
- `greenlight_katzin_2020_biosystems_engineering.pdf` - GreenLight как
  open-source физическая модель теплицы с досветкой.
- `sindy_brunton_2016_arxiv_1509.03580.pdf` - базовая статья по SINDy.
- `sindyc_brunton_2016_arxiv_1605.06682.pdf` - SINDy with control, важна для
  включения актуаторов.
- `sindy_mpc_kaiser_2018_arxiv_1711.05501.pdf` - SINDy + MPC в low-data
  setting, самый близкий методологический источник.
- `greenhouse_mpc_lin_2021_applied_energy.pdf` - MPC для Venlo-type теплицы с
  учетом энергии, воды и CO2.
- `greenhouse_dd_rmpc_chen_you_2020_cet.pdf` - data-driven robust MPC для
  greenhouse temperature/CO2 control.

## Возможная структура будущей статьи

1. Introduction: autonomous greenhouse control, ресурсоэффективность,
   ограничения чисто black-box подходов.
2. Related work: iGrow и AGC, GreenLight/GreenLight-Gym2, SINDy/SINDYc,
   SINDy-MPC, greenhouse MPC.
3. Simulation environment: GreenLight-Gym2, states, actions, weather,
   rule-based baseline.
4. Physics-Informed SINDy: сбор данных, признаки, нормализация, sparse
   regression, интерпретируемые уравнения.
5. MPC formulation: embedded SINDy dynamics, objective, constraints, TVP
   weather forecast.
6. DAgger refinement: dataset aggregation from MPC rollouts.
7. Experiments: сравнение rule-based baseline, initial SINDy-MPC,
   post-DAgger SINDy-MPC; метрики tracking, constraint violations, energy,
   CO2 usage, compute time.
8. Safety layer: OOD detection and optional supervisor, если будет
   количественная проверка.
9. Discussion: интерпретируемость, limitations, перенос из симулятора в
   реальную теплицу.

## Минимальные эксперименты перед написанием

- Зафиксировать единую финальную реализацию objective и constraints между
  notebook и `greenhouse_mvp/control_core/mpc_controller.py`.
- Исправить OOD/DAgger API mismatch в сервисном коде.
- Получить таблицу сравнения:
  rule-based baseline vs initial SINDy-MPC vs post-DAgger SINDy-MPC.
- Сохранить графики: `t_in`, `co2`, `rh`, все 6 актуаторов, `rad`, `T_out`,
  constraint violations, cumulative energy proxy.
- Отдельно проверить generalization на другой start date/weather trajectory.
