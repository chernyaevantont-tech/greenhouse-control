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

from greenhouse_mvp.environment.incident_manager import INCIDENT_CATALOG, IncidentManager
from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    IncidentAlert,
    IncidentSpec,
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
        self._incident_detector_enabled: bool = True

        # Shared state (read by /api/status)
        self._running: bool = False
        self._step: int = 0
        self._latest_telemetry: Optional[dict] = None
        self._latest_action: Optional[dict] = None
        self._latest_ood: Optional[dict] = None

        # Incident management
        self._incident_manager = IncidentManager()

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

    def set_incident_detector_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._incident_detector_enabled = enabled
        logger.info("SimulationRunner: incident_detector_enabled -> %s", enabled)

    # ------------------------------------------------------------------
    # Incident management
    # ------------------------------------------------------------------

    def add_incident(self, spec: IncidentSpec) -> IncidentAlert:
        """Add an incident and return an IncidentAlert for SSE emission."""
        with self._lock:
            current_step = self._step
        # Set start_step to current if not specified
        if spec.start_step == 0 and current_step > 0:
            spec = spec.model_copy(update={"start_step": current_step})
        self._incident_manager.add(spec, current_step)
        meta = INCIDENT_CATALOG.get(spec.incident_type, {})
        alert = IncidentAlert(
            incident_id=spec.incident_id,
            incident_type=spec.incident_type,
            action="triggered",
            step=current_step,
            severity=spec.severity,
            description=spec.description or meta.get("description", ""),
        )
        self._emit({"type": "incident", "data": alert.model_dump()})
        return alert

    def remove_incident(self, incident_id: str) -> bool:
        """Remove an incident by ID; returns True if it existed."""
        with self._lock:
            current_step = self._step
        removed = self._incident_manager.remove(incident_id)
        if removed:
            self._emit({"type": "incident", "data": {
                "incident_id": incident_id,
                "incident_type": "unknown",
                "action": "resolved",
                "step": current_step,
                "severity": 0.0,
                "description": "Resolved by operator",
            }})
        return removed

    def list_incidents(self) -> list[dict]:
        """Return serialised list of all active incidents."""
        return self._incident_manager.summary()

    def get_active_incidents(self) -> list[IncidentSpec]:
        """Return active IncidentSpec objects at the current step."""
        with self._lock:
            step = self._step
        return self._incident_manager.get_active(step)

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
            step = self._step
        active_incidents = self._incident_manager.get_active(step)
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
                active_incidents=active_incidents,
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

            # Build incident detector (shares LLM credentials with the supervisor)
            from greenhouse_mvp.agents.incident_detector import IncidentDetector
            incident_detector = IncidentDetector(
                backend=os.environ.get("LLM_BACKEND", "openai"),
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
            )

            graph = build_graph(
                mpc_ctrl, llm_ctrl, supervisor,
                incident_detector=incident_detector,
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
                # Incident detection
                "active_incidents": [],
                "incident_report": None,
                "last_incident_detect_step": -999,
                "incident_detector_enabled": self._incident_detector_enabled,
            }

            from greenhouse_mvp.environment.sim_adapter import (
                SAFE_FALLBACK_ACTION,
                action_to_array,
                obs_to_telemetry,
            )
            from greenhouse_mvp.environment.fault_injector import FaultInjector
            fault_injector = FaultInjector(cfg.faults)

            # Incident manager is long-lived across episodes within one start() call
            incident_manager = self._incident_manager

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
                    graph_state["last_incident_detect_step"] = -999
                    incident_manager.reset()
                    with self._lock:
                        self._step = 0
                    self._emit({"type": "reset", "data": {}})
                    logger.info("SimulationRunner: episode reset at step %d", step)
                    continue

                # Check for expired incidents and emit alerts
                expired_alerts = incident_manager.expire_check(step)
                for alert in expired_alerts:
                    self._emit({"type": "incident", "data": alert.model_dump()})

                # Build telemetry from observation (apply sensor faults, then incident disturbances)
                telemetry = obs_to_telemetry(obs, step, cfg.period)
                telemetry = fault_injector.inject_sensor(telemetry, step)
                telemetry = incident_manager.apply_to_telemetry(telemetry, step)

                with self._lock:
                    self._step = step
                    self._latest_telemetry = telemetry.model_dump()

                self._emit({"type": "telemetry", "data": telemetry.model_dump()})

                # Read live controller/agent settings
                with self._lock:
                    ctrl_mode = self._controller_mode
                    agent_on = self._agent_enabled
                    detector_on = self._incident_detector_enabled

                # Collect active incidents for the graph context
                active_incident_dicts = [
                    inc.model_dump() for inc in incident_manager.get_active(step)
                ]

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
                    "incident_report": None,
                    "_terminated": False,
                    "controller_mode": ctrl_mode,
                    "agent_enabled": agent_on,
                    "active_incidents": active_incident_dicts,
                    "incident_detector_enabled": detector_on,
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

                # Emit incident detection report (if detector ran this step)
                incident_report = graph_state.get("incident_report")
                if incident_report is not None:
                    self._emit({"type": "incident_report", "data": {
                        "step": incident_report.step,
                        "detected_type": incident_report.detected_type,
                        "confidence": incident_report.confidence,
                        "affected_systems": incident_report.affected_systems,
                        "repair_steps": incident_report.repair_steps,
                        "reasoning": incident_report.reasoning,
                        "urgency": incident_report.urgency,
                        "mitigation_action": (
                            incident_report.mitigation_action.model_dump()
                            if incident_report.mitigation_action else None
                        ),
                    }})

                # Step the environment:
                #   1. fault injector (sensor faults already applied above; actuator faults here)
                #   2. incident constraints (physical actuator limitations)
                action_vec = (
                    action_to_array(final_action) if final_action
                    else SAFE_FALLBACK_ACTION.copy()
                )
                action_vec = fault_injector.inject_actuator(action_vec, step)
                action_vec = incident_manager.apply_to_action(action_vec, step)
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
            horizon=cfg.mpc_horizon,
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
