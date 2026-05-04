# Plan 06: Docker Compose Deployment

## Overview

The entire stack runs as six containers orchestrated by a single
`docker-compose.yml`. Each service maps to exactly one architectural layer and
communicates exclusively over an internal Docker bridge network via the MQTT
broker.

---

## 1. Service Map

| Service | Image / Build context | Role |
|---|---|---|
| `mqtt_broker` | `eclipse-mosquitto:2` | Central message bus |
| `sim_adapter` | `./` (app image) | Runs `SimAdapter.loop_forever()` |
| `control_core` | `./` (app image) | Runs `MPCController` + `SINDyFitter` |
| `orchestration` | `./` (app image) | Runs LangGraph `GraphWorkflow` |
| `dashboard` | `./` (app image) | Runs `streamlit run dashboard/app.py` |
| `llm_agent` | `./` (app image) | Runs `NotebookLMAgent` HTTP wrapper (optional, can be inlined into orchestration) |

All Python services use the same base image so there is only one `Dockerfile` to
maintain.

---

## 2. Directory Layout

```
greenhouse_mvp/
├── Dockerfile
├── docker-compose.yml
├── mosquitto/
│   └── mosquitto.conf        # Minimal broker config
├── .env                      # Secrets: OPENAI_API_KEY, MQTT_HOST, etc.
└── ... (source code)
```

---

## 3. `Dockerfile`

```dockerfile
FROM python:3.11-slim

# System deps needed by do_mpc / CasADi / gl_gym
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default entrypoint is overridden per-service in docker-compose.yml
CMD ["python", "-m", "orchestration.graph_workflow"]
```

---

## 4. `mosquitto/mosquitto.conf`

```conf
listener 1883
allow_anonymous true
persistence false
log_type error
log_type warning
```

For production, replace `allow_anonymous true` with password-file authentication.

---

## 5. `docker-compose.yml`

```yaml
version: "3.9"

# ──────────────────────────────────────────────
# Shared environment variables for all services
# ──────────────────────────────────────────────
x-common-env: &common-env
  MQTT_HOST: mqtt_broker
  MQTT_PORT: 1883
  START_DATE: "2010-02-28"
  N_DAYS: "60"
  PERIOD: "900"
  MPC_HORIZON: "20"

services:

  # ─── 1. MQTT Broker ─────────────────────────
  mqtt_broker:
    image: eclipse-mosquitto:2
    container_name: mqtt_broker
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
    ports:
      - "1883:1883"       # Expose for local MQTT clients (e.g., MQTTX)
    networks:
      - greenhouse_net
    restart: unless-stopped

  # ─── 2. Simulation Adapter ──────────────────
  sim_adapter:
    build: .
    container_name: sim_adapter
    command: python -m environment.sim_adapter
    environment:
      <<: *common-env
    depends_on:
      - mqtt_broker
    networks:
      - greenhouse_net
    restart: on-failure

  # ─── 3. Control Core (SINDy + MPC) ─────────
  control_core:
    build: .
    container_name: control_core
    command: python -m control_core.mpc_controller
    environment:
      <<: *common-env
      SINDY_MODEL_PATH: /app/models/sindy_model.pkl
      OOD_THRESHOLD: "3.0"
    volumes:
      - model_store:/app/models    # Persisted SINDy model files
    depends_on:
      - mqtt_broker
    networks:
      - greenhouse_net
    restart: on-failure

  # ─── 4. Orchestration (LangGraph) ───────────
  orchestration:
    build: .
    container_name: orchestration
    command: python -m orchestration.graph_workflow
    environment:
      <<: *common-env
      MAX_RETRIES: "2"
      RETRAIN_INTERVAL: "96"
    depends_on:
      - mqtt_broker
      - control_core
    networks:
      - greenhouse_net
    restart: on-failure

  # ─── 5. LLM Agent (Supervisor) ──────────────
  llm_agent:
    build: .
    container_name: llm_agent
    command: python -m agents.notebooklm_agent
    environment:
      <<: *common-env
      LLM_BACKEND: "openai"
      LLM_MODEL: "gpt-4o-mini"
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
    depends_on:
      - mqtt_broker
    networks:
      - greenhouse_net
    restart: on-failure

  # ─── 6. Dashboard (Streamlit) ───────────────
  dashboard:
    build: .
    container_name: dashboard
    command: streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0
    environment:
      <<: *common-env
    ports:
      - "8501:8501"       # Open in browser: http://localhost:8501
    depends_on:
      - mqtt_broker
    networks:
      - greenhouse_net
    restart: unless-stopped

# ──────────────────────────────────────────────
networks:
  greenhouse_net:
    driver: bridge

volumes:
  model_store:    # Persists trained SINDy model between container restarts
```

---

## 6. `.env` File (secrets, not committed to git)

```env
OPENAI_API_KEY=sk-...
```

Add `.env` to `.gitignore`. All other config uses the `x-common-env` block in
`docker-compose.yml`.

---

## 7. Startup Order and Health

`depends_on` guarantees that `mqtt_broker` starts before any subscriber. However,
Compose does not wait for the broker to be *ready* (accepting connections), only
for the container to be *running*. Each Python service must therefore implement a
**connection retry loop** on startup (already handled by the `MQTTBus` exponential
back-off from Plan 01).

For a more robust setup, add a healthcheck to `mqtt_broker`:

```yaml
mqtt_broker:
  ...
  healthcheck:
    test: ["CMD", "mosquitto_sub", "-t", "$$SYS/#", "-C", "1", "-i", "healthcheck"]
    interval: 5s
    timeout: 3s
    retries: 5
```

Then use `condition: service_healthy` in dependent services:

```yaml
sim_adapter:
  depends_on:
    mqtt_broker:
      condition: service_healthy
```

---

## 8. Common Commands

```bash
# Build all images and start the stack
docker compose up --build

# Start in detached mode (background)
docker compose up --build -d

# View logs for a specific service
docker compose logs -f control_core

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including the model_store volume
docker compose down -v

# Restart a single service after a code change
docker compose up --build -d control_core
```

---

## 9. Development Override (`docker-compose.override.yml`)

For local development, mount the source code as a volume so you don't have to
rebuild the image on every code change:

```yaml
# docker-compose.override.yml  (auto-loaded by docker compose up)
services:
  sim_adapter:
    volumes:
      - .:/app
  control_core:
    volumes:
      - .:/app
  orchestration:
    volumes:
      - .:/app
  llm_agent:
    volumes:
      - .:/app
  dashboard:
    volumes:
      - .:/app
```

---

## 10. Production Notes

| Concern | Recommendation |
|---|---|
| MQTT security | Switch `allow_anonymous false`, add `password_file` in `mosquitto.conf` |
| Secrets management | Use Docker Secrets or a vault instead of `.env` |
| Persistent data | Mount `model_store` to a host path for model checkpointing |
| Resource limits | Add `mem_limit: 2g` / `cpus: "1.0"` to `control_core` (CasADi is CPU-heavy) |
| Logging | Add `logging: driver: json-file, options: max-size: "10m"` to all services |
