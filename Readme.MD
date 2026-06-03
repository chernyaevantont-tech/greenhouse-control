# Greenhouse Control

Система управления микроклиматом теплицы поверх симулятора
`gl_gym/GreenLightTomato-v0`. Текущая реализация состоит из FastAPI backend,
фонового `SimulationRunner`, SINDy/MPC-контроллера, опционального LLM-контроллера,
LLM-supervisor и React dashboard.

Ранняя MQTT/Streamlit-архитектура удалена из активного дерева кода, чтобы в
проекте не было двух конкурирующих вариантов запуска.

## Что запускается

Основной запуск описан в `docker-compose.yml`:

1. `sindy_bootstrap` собирает данные в headless-симуляции, обучает SINDy-модель
   и сохраняет `/app/models/sindy_model.pkl`.
2. `api_server` запускает `greenhouse_mvp.api.server` на порту `8000`.
3. `dashboard` собирает React-приложение и отдает его через nginx на порту `8080`,
   проксируя `/api/*` в `api_server`.

```text
React dashboard
  | REST: start/stop/reset/config/controller/agent
  | SSE : telemetry/action/ood/verdict/llm_action
  v
FastAPI server
  v
SimulationRunner, background thread
  v
gl_gym simulator -> telemetry -> LangGraph workflow -> action -> gl_gym step
                         |              |
                         |              +-- MPC или LLM controller
                         +-- OOD metrics / optional LLM supervisor
```

## Быстрый старт

```bash
cp example.env .env
docker compose up --build
```

После запуска:

- Dashboard: <http://localhost:8080>
- API: <http://localhost:8000>
- SSE stream: <http://localhost:8000/api/events>

Симуляция не стартует автоматически. Запустите ее кнопкой `Start` в dashboard или:

```bash
curl -X POST http://localhost:8000/api/start
```

## Конфигурация

| Параметр | Назначение | По умолчанию |
| --- | --- | --- |
| `START_DATE` | дата старта эпизода | `2010-02-28` |
| `N_DAYS` | длина сезона в днях | `60` |
| `PERIOD` | шаг симуляции в секундах | `900` |
| `MPC_HORIZON` | горизонт MPC в шагах | `20` |
| `CONTROLLER_MODE` | `mpc` или `llm` | `mpc` |
| `AGENT_ENABLED_DEFAULT` | включать LLM-supervisor для MPC | `false` |
| `LLM_CALL_INTERVAL` | период вызова LLM-контроллера в шагах | `1` |
| `LLM_HISTORY_WINDOW` | глубина истории в prompt LLM | `1` |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint | пусто |
| `OPENAI_API_KEY` | ключ или локальная заглушка | пусто |
| `LLM_MODEL` | модель для LLM-контроллера и supervisor | `gpt-4o-mini` |

`example.env` настроен под OpenAI-compatible локальный endpoint, например LM Studio:

```env
OPENAI_BASE_URL=http://host.docker.internal:1234/v1
OPENAI_API_KEY=lm-studio
LLM_MODEL=qwen3.5-9b
```

## API

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/status` | текущее состояние симуляции |
| `GET` | `/api/config` | текущая конфигурация |
| `POST` | `/api/config` | обновить конфигурацию для следующего start/reset |
| `POST` | `/api/start` | запустить симуляцию |
| `POST` | `/api/stop` | остановить симуляцию |
| `POST` | `/api/reset` | сбросить эпизод |
| `POST` | `/api/control` | пауза и скорость симуляции |
| `POST` | `/api/controller` | переключить `mpc` / `llm` |
| `POST` | `/api/agent` | включить или выключить LLM-supervisor |
| `GET` | `/api/events` | Server-Sent Events поток |

SSE-события:

- `telemetry` - состояние теплицы и внешняя погода;
- `action` - примененное управляющее воздействие;
- `ood` - Mahalanobis distance и флаг выхода из обучающего распределения;
- `verdict` - решение LLM-supervisor в MPC-режиме;
- `llm_action` - reasoning и fault report LLM-контроллера;
- `reset`, `episode_done`, `heartbeat`, `error`.

## Контроллеры

### MPC

`MPCController` использует дискретную SINDy-модель как суррогат динамики теплицы.
Модель обучается bootstrap-сервисом на данных из GreenLightGym через rule-based
controller с небольшим шумом. Для MPC формируются физически мотивированные
признаки: погода, время суток, управляющие воздействия, VPD, эффективная радиация
и cross-terms.

Цели MPC:

- температура внутри: 18-22 C, setpoint 20 C;
- CO2: 600-1000 ppm, setpoint 800 ppm;
- относительная влажность: до 85%;
- штрафы за энергозатратные действия.

`WeatherForecastTVP` получает тот же `horizon`, что и MPC, поэтому TVP-шаблон
согласован с настройкой `MPC_HORIZON`.

### OOD

Для online-пути используется `compute_physics_features_single()`, который строит
один 18-мерный feature vector через тот же векторный код, что и bootstrap. OOD
считается через Mahalanobis distance по обучающему распределению SINDy-признаков.

### LLM controller

LLM-контроллер напрямую выбирает шесть actuator-сигналов через tool call
`set_actuators`. При ошибке LLM используется safe fallback: умеренный обогрев,
закрытый thermal screen, остальные воздействия выключены.

### LLM supervisor

В MPC-режиме можно включить supervisor-agent. Он вызывается при OOD-событии после
warmup и с cooldown. Supervisor может:

- `APPROVE` - принять действие MPC;
- `REJECT` - попросить MPC перепланировать;
- `OVERRIDE` - заменить действие своими actuator-значениями.

## Fault injection

Dashboard может отправлять fault presets в конфиг. Faults применяются в
`FaultInjector`:

- sensor faults: `t_in`, `co2`, `rh`;
- actuator faults: `uBoil`, `uCO2`, `uThScr`, `uVent`, `uLamp`, `uBlScr`;
- типы: `stuck_high`, `stuck_low`, `random`, `offset`, `dead`.

Sensor faults применяются до передачи телеметрии контроллеру, actuator faults -
после выбора действия и перед `env.step()`.

## Структура проекта

```text
greenhouse_mvp/
  api/
    server.py             FastAPI endpoints и SSE
    simulation_runner.py  фоновый цикл симуляции
  control_core/
    mpc_controller.py     SINDy + do-mpc контроллер
    llm_controller.py     LLM actuator controller
  environment/
    sim_adapter.py        конвертация obs/action для runner
    tvp_forecast.py       прогноз погоды для MPC TVP
    fault_injector.py     инъекция отказов
  orchestration/
    graph_workflow.py     LangGraph workflow одного simulation step
    schemas.py            Pydantic-схемы REST/SSE/internal state
  sindy_pipeline/
    bootstrap.py          сбор данных и обучение SINDy
    physics_features.py   physics-informed признаки
    sindy_fitter.py       обучение и persistence SINDy
dashboard/
  src/                    актуальный React dashboard
  nginx.conf              proxy /api в api_server
docs/
  architecture.md         актуальная FastAPI/SSE архитектура
tests/
  test_api_smoke.py       smoke-тесты API и одного simulation step
```

## Что было очищено

- Удалены legacy MQTT/Streamlit файлы: старый Streamlit dashboard, MQTT listener,
  MQTT bus wrapper, standalone MQTT HTML и Mosquitto config.
- Удалено неиспользуемое поле `connected` из frontend state; фактический статус
  соединения хранится в `serverConnected`.
- Исправлен online-вызов physics features: OOD и DAgger больше не вызывают
  batch-функцию с несовместимыми keyword-аргументами.
- Исправлен DAgger retrain path: `SINDyFitter.fit()` вызывается с актуальной
  сигнатурой и возвращает новую модель вместе со scaler-ами.
- Default `CMD` в `Dockerfile` теперь указывает на API server.

## Документация

Подробная архитектура: `docs/architecture.md`.

## Разработка

Backend локально:

```bash
python -m greenhouse_mvp.sindy_pipeline.bootstrap
python -m greenhouse_mvp.api.server
```

Frontend локально:

```bash
cd dashboard
npm install
npm run dev
```

Тесты:

```bash
python -m pytest tests/test_api_smoke.py
```
