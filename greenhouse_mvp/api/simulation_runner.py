"""
simulation_runner.py — Background thread simulation manager.

Runs the GreenLight gym environment + LangGraph workflow in a single thread.
Emits SSE events (telemetry, action, ood, verdict, llm_action) to registered
asyncio.Queue subscribers (one per connected SSE client).

Replaces the previous MQTT-based multi-service architecture.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pickle
import threading
import time
from typing import Optional

import numpy as np

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    OODMetrics,
    SimConfig,
    SimStatus,
    TelemetryPayload,
)

logger = logging.getLogger(__name__)


class SimulationRunner:
    """
    Single-process simulation manager.

    Lifecycle:
      runner = SimulationRunner()
      runner.set_event_loop(asyncio.get_event_loop())  # call from FastAPI startup
      runner.start()    # begin simulation
      runner.stop()     # stop simulation
      runner.request_reset()  # reset episode mid-run
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # set=running, clear=paused
        self._reset_event = threading.Event()

        # Load initial config from environment variables
        self._config = SimConfig(
            start_date=os.environ.get("START_DATE", "2010-02-28"),
            n_days=int(os.environ.get("N_DAYS", "60")),
            period=int(os.environ.get("PERIOD", "900")),
            mpc_horizon=int(os.environ.get("MPC_HORIZON", "20")),
            controller_mode=os.environ.get("CONTROLLER_MODE", "mpc").lower(),
            agent_enabled=os.environ.get("AGENT_ENABLED_DEFAULT", "false").lower() == "true",
            llm_call_interval=int(os.environ.get("LLM_CALL_INTERVAL", "1")),
            llm_history_window=int(os.environ.get("LLM_HISTORY_WINDOW", "1")),
        )

        # Live mutable config (safe to update at runtime)
        self._controller_mode: str = self._config.controller_mode
        self._agent_enabled: bool = self._config.agent_enabled
        self._speed_multiplier: float = 1.0
        self._paused: bool = False

        # Shared state (read by /api/status)
        self._running: bool = False
        self._step: int = 0
        self._latest_telemetry: Optional[dict] = None
        self._latest_action: Optional[dict] = None
        self._latest_ood: Optional[dict] = None

        # SSE subscribers (asyncio.Queue, one per connected client)
        self._subscribers: list[asyncio.Queue] = []
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._event_loop = loop

    def start(self) -> None:
        """Start the simulation in a background thread."""
        with self._lock:
            if self._running:
                logger.info("SimulationRunner: already running")
                return
            self._stop_event.clear()
            self._reset_event.clear()
            self._pause_event.set()  # begin unpaused
            self._paused = False
            self._thread = threading.Thread(
                target=self._run, daemon=True, name="sim-runner"
            )
            self._thread.start()
            logger.info("SimulationRunner: started")

    def stop(self) -> None:
        """Stop the simulation thread."""
        self._stop_event.set()
        self._pause_event.set()  # unblock if paused
        with self._lock:
            self._running = False
        logger.info("SimulationRunner: stop requested")

    def request_reset(self) -> None:
        """Request an episode reset (takes effect at the start of the next step)."""
        self._reset_event.set()
        self._pause_event.set()  # unblock if paused
        logger.info("SimulationRunner: reset requested")

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = paused
        if paused:
            self._pause_event.clear()
            logger.info("SimulationRunner: paused")
        else:
            self._pause_event.set()
            logger.info("SimulationRunner: resumed")

    def set_speed(self, speed: float) -> None:
        with self._lock:
            self._speed_multiplier = max(0.1, min(20.0, speed))

    def set_controller_mode(self, mode: str) -> None:
        with self._lock:
            self._controller_mode = mode
            self._config = self._config.model_copy(update={"controller_mode": mode})
        logger.info("SimulationRunner: controller mode -> %s", mode)

    def set_agent_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._agent_enabled = enabled
            self._config = self._config.model_copy(update={"agent_enabled": enabled})
        logger.info("SimulationRunner: agent_enabled -> %s", enabled)

    def update_config(self, new_config: SimConfig) -> None:
        """Update simulation config (applies on next start/reset)."""
        with self._lock:
            self._config = new_config
            self._controller_mode = new_config.controller_mode
            self._agent_enabled = new_config.agent_enabled
            self._speed_multiplier = new_config.speed_multiplier

    @property
    def config(self) -> SimConfig:
        with self._lock:
            return self._config.model_copy(update={
                "controller_mode": self._controller_mode,
                "agent_enabled": self._agent_enabled,
                "speed_multiplier": self._speed_multiplier,
            })

    def get_status(self) -> SimStatus:
        with self._lock:
            return SimStatus(
                running=self._running,
                paused=self._paused,
                step=self._step,
                config=self.config,
                latest_telemetry=(
                    TelemetryPayload(**self._latest_telemetry)
                    if self._latest_telemetry else None
                ),
                latest_action=(
                    ActionPayload(**self._latest_action)
                    if self._latest_action else None
                ),
                latest_ood=(
                    OODMetrics(**self._latest_ood)
                    if self._latest_ood else None
                ),
            )

    # ------------------------------------------------------------------
    # SSE pub/sub
    # ------------------------------------------------------------------

    def add_subscriber(self, q: asyncio.Queue) -> None:
        self._subscribers.append(q)

    def remove_subscriber(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def _emit(self, event: dict) -> None:
        loop = self._event_loop
        if loop is None or not loop.is_running():
            return
        for q in list(self._subscribers):
            try:
                loop.call_soon_threadsafe(q.put_nowait, event)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Simulation loop (background thread)
    # ------------------------------------------------------------------

    def _run(self) -> None:
        with self._lock:
            self._running = True
            self._step = 0

        env = None
        step = 0

        try:
            import gl_gym  # noqa: F401
            import gymnasium as gym

            mpc_ctrl, llm_ctrl, supervisor = self._build_controllers()

            from greenhouse_mvp.orchestration.graph_workflow import build_graph

            cfg = self._config
            weather_cfg = {
                "env_id": cfg.env_id,
                "start_date": cfg.start_date,
                "n_days": cfg.n_days,
                "period": cfg.period,
            }
            graph = build_graph(
                mpc_ctrl, llm_ctrl, supervisor,
                dagger_dataset={}, weather_cfg=weather_cfg,
            )

            env = gym.make(
                cfg.env_id,
                normalize_actions=False,
                observation_modules=[
                    "IndoorClimateObservations",
                    "WeatherObservations",
                    "BasicCropObservations",
                ],
                season_length=cfg.n_days,
            )

            obs, _ = env.reset(options={"start_date": cfg.start_date}, seed=42)

            indoor = obs["IndoorClimateObservations"]
            x0 = np.array([float(indoor[1]), float(indoor[0]), float(indoor[2])])
            mpc_ctrl.initialise(x0)

            max_retries = int(os.environ.get("MAX_RETRIES", "2"))

            graph_state: dict = {
                "telemetry": None,
                "proposed_action": None,
                "supervisor_verdict": None,
                "final_action": None,
                "ood_metrics": None,
                "ood_detected": False,
                "llm_reasoning": None,
                "retry_count": 0,
                "max_retries": max_retries,
                "episode_log": [],
                "last_supervisor_step": -999,
                "_terminated": False,
                "controller_mode": self._controller_mode,
                "agent_enabled": self._agent_enabled,
            }

            from greenhouse_mvp.environment.sim_adapter import (
                SAFE_FALLBACK_ACTION,
                action_to_array,
                obs_to_telemetry,
            )
            from greenhouse_mvp.environment.fault_injector import FaultInjector
            fault_injector = FaultInjector(cfg.faults)

            while not self._stop_event.is_set():
                # Honor pause
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                # Honor reset
                if self._reset_event.is_set():
                    self._reset_event.clear()
                    obs, _ = env.reset(options={"start_date": cfg.start_date}, seed=42)
                    step = 0
                    indoor = obs["IndoorClimateObservations"]
                    x0 = np.array([float(indoor[1]), float(indoor[0]), float(indoor[2])])
                    mpc_ctrl.initialise(x0)
                    graph_state["episode_log"] = []
                    graph_state["last_supervisor_step"] = -999
                    with self._lock:
                        self._step = 0
                    self._emit({"type": "reset", "data": {}})
                    logger.info("SimulationRunner: episode reset at step %d", step)
                    continue

                # Build telemetry from observation (apply sensor faults before LLM sees it)
                telemetry = obs_to_telemetry(obs, step, cfg.period)
                telemetry = fault_injector.inject_sensor(telemetry, step)

                with self._lock:
                    self._step = step
                    self._latest_telemetry = telemetry.model_dump()

                self._emit({"type": "telemetry", "data": telemetry.model_dump()})

                # Read live controller/agent settings
                with self._lock:
                    ctrl_mode = self._controller_mode
                    agent_on = self._agent_enabled

                # Run LangGraph step
                graph_state = graph.invoke({
                    **graph_state,
                    "telemetry": telemetry,
                    "retry_count": 0,
                    "proposed_action": None,
                    "supervisor_verdict": None,
                    "final_action": None,
                    "ood_metrics": None,
                    "ood_detected": False,
                    "llm_reasoning": None,
                    "_terminated": False,
                    "controller_mode": ctrl_mode,
                    "agent_enabled": agent_on,
                })

                final_action: Optional[ActionPayload] = graph_state.get("final_action")
                ood: Optional[OODMetrics] = graph_state.get("ood_metrics")
                verdict = graph_state.get("supervisor_verdict")
                llm_reasoning: Optional[str] = graph_state.get("llm_reasoning")

                if final_action:
                    with self._lock:
                        self._latest_action = final_action.model_dump()
                    self._emit({"type": "action", "data": final_action.model_dump()})

                if ood:
                    with self._lock:
                        self._latest_ood = ood.model_dump()
                    self._emit({"type": "ood", "data": ood.model_dump()})

                if verdict:
                    self._emit({"type": "verdict", "data": verdict.model_dump()})

                if llm_reasoning and ctrl_mode == "llm" and final_action:
                    fault_report = getattr(llm_ctrl, "last_fault_report", "OK")
                    self._emit({"type": "llm_action", "data": {
                        "step": step,
                        "reasoning": llm_reasoning,
                        "fault_report": fault_report,
                        "uBoil": final_action.uBoil,
                        "uCO2": final_action.uCO2,
                        "uThScr": final_action.uThScr,
                        "uVent": final_action.uVent,
                        "uLamp": final_action.uLamp,
                        "uBlScr": final_action.uBlScr,
                    }})

                # Step the environment (apply actuator faults after LLM decision, before gym)
                action_vec = (
                    action_to_array(final_action) if final_action
                    else SAFE_FALLBACK_ACTION.copy()
                )
                action_vec = fault_injector.inject_actuator(action_vec, step)
                obs, _reward, terminated, truncated, _info = env.step(action_vec)
                step += 1

                if terminated or truncated:
                    self._emit({"type": "episode_done", "data": {"step": step}})
                    logger.info("SimulationRunner: episode finished after %d steps", step)
                    break

                # Speed-controlled sleep (BASE = 0.5 s at 1×)
                with self._lock:
                    speed = self._speed_multiplier
                sleep_s = 0.5 / speed
                if sleep_s > 0:
                    time.sleep(sleep_s)

        except Exception:
            logger.exception("SimulationRunner: unhandled error in simulation thread")
            self._emit({"type": "error", "data": {"message": "Simulation error — see server logs"}})
        finally:
            if env is not None:
                try:
                    env.close()
                except Exception:
                    pass
            with self._lock:
                self._running = False
            logger.info("SimulationRunner: thread exited (step=%d)", step)

    # ------------------------------------------------------------------
    # Controller factory
    # ------------------------------------------------------------------

    def _build_controllers(self):
        """Instantiate MPC, LLM controllers and supervisor agent from env vars / config."""
        from greenhouse_mvp.control_core.llm_controller import LLMController
        from greenhouse_mvp.control_core.mpc_controller import MPCController
        from greenhouse_mvp.agents.notebooklm_agent import NotebookLMAgent
        from greenhouse_mvp.environment.tvp_forecast import WeatherForecastTVP

        cfg = self._config

        # LLM settings from environment
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        backend = os.environ.get("LLM_BACKEND", "openai")
        timeout_str = os.environ.get("LLM_TIMEOUT", "")
        timeout = float(timeout_str) if timeout_str else None

        llm_ctrl = LLMController(
            backend=backend,
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            timeout=timeout,
            call_interval=cfg.llm_call_interval,
            history_window=cfg.llm_history_window,
        )

        supervisor = NotebookLMAgent(
            backend=backend,
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            timeout=timeout or 30.0,
        )

        # Load SINDy model artifact
        model_path = os.environ.get("SINDY_MODEL_PATH", "/app/models/sindy_model.pkl")
        with open(model_path, "rb") as f:
            artifact = pickle.load(f)

        sindy_model = artifact["model"]
        scaler_x = artifact["scaler_x"]
        scaler_u = artifact["scaler_u"]
        mu_train = artifact.get("mu_train")
        cov_inv = artifact.get("cov_inv")

        weather_provider = WeatherForecastTVP(
            env_id=cfg.env_id,
            start_date=cfg.start_date,
            n_days=cfg.n_days,
            period=cfg.period,
        )

        mpc_ctrl = MPCController(
            sindy_model=sindy_model,
            scaler_x=scaler_x,
            scaler_u=scaler_u,
            weather_provider=weather_provider,
            horizon=cfg.mpc_horizon,
            period=float(cfg.period),
            mu_train=mu_train,
            cov_inv=cov_inv,
        )

        return mpc_ctrl, llm_ctrl, supervisor
