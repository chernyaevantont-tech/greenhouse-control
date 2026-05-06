"""
server.py — FastAPI REST + SSE server for greenhouse control.

Replaces the MQTT broker + multiple separate services with a single HTTP API.

Endpoints:
  GET  /api/status       — current simulation state
  GET  /api/config       — simulation configuration
  POST /api/config       — update config (applies on next start/reset)
  POST /api/start        — start simulation (starts stopped/paused)
  POST /api/stop         — stop simulation
  POST /api/reset        — reset episode
  POST /api/control      — pause/resume + speed multiplier
  POST /api/controller   — switch MPC / LLM controller
  POST /api/agent        — enable/disable LLM supervisor
  GET  /api/events       — SSE stream (telemetry, action, ood, verdict, llm_action)
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from greenhouse_mvp.orchestration.schemas import (
    AgentControlPayload,
    ControllerSelectPayload,
    SimConfig,
    SimControlPayload,
    SimResetPayload,
    SimStatus,
)
from greenhouse_mvp.api.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

runner = SimulationRunner()


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner.set_event_loop(asyncio.get_event_loop())
    logger.info("Greenhouse API server started — simulation is stopped. POST /api/start to begin.")
    yield
    runner.stop()
    logger.info("Greenhouse API server shutting down.")


app = FastAPI(title="Greenhouse Controller API", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Status & config
# ---------------------------------------------------------------------------


@app.get("/api/status", response_model=SimStatus)
def get_status() -> SimStatus:
    return runner.get_status()


@app.get("/api/config", response_model=SimConfig)
def get_config() -> SimConfig:
    return runner.config


@app.post("/api/config")
def update_config(config: SimConfig) -> dict:
    runner.update_config(config)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Simulation control
# ---------------------------------------------------------------------------


@app.post("/api/start")
def start_simulation() -> dict:
    runner.start()
    return {"ok": True}


@app.post("/api/stop")
def stop_simulation() -> dict:
    runner.stop()
    return {"ok": True}


@app.post("/api/reset")
def reset_simulation(_req: SimResetPayload = None) -> dict:
    runner.request_reset()
    return {"ok": True}


@app.post("/api/control")
def control_simulation(req: SimControlPayload) -> dict:
    runner.set_paused(req.paused)
    runner.set_speed(req.speed_multiplier)
    return {"ok": True}


@app.post("/api/controller")
def set_controller(req: ControllerSelectPayload) -> dict:
    runner.set_controller_mode(req.mode)
    return {"ok": True}


@app.post("/api/agent")
def set_agent(req: AgentControlPayload) -> dict:
    runner.set_agent_enabled(req.enabled)
    return {"ok": True}


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------


@app.get("/api/events")
async def sse_events():
    """
    Server-Sent Events endpoint.  Each event is a JSON object with a ``type``
    field and a ``data`` payload:

      {"type": "telemetry", "data": {...}}
      {"type": "action",    "data": {...}}
      {"type": "ood",       "data": {...}}
      {"type": "verdict",   "data": {...}}
      {"type": "llm_action","data": {...}}
      {"type": "reset",     "data": {}}
      {"type": "episode_done", "data": {"step": N}}
      {"type": "heartbeat", "data": {}}
    """
    async def generate():
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        runner.add_subscriber(q)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield 'data: {"type":"heartbeat","data":{}}\n\n'
        except asyncio.CancelledError:
            pass
        finally:
            runner.remove_subscriber(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    uvicorn.run(
        "greenhouse_mvp.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
