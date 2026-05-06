"""
graph_workflow.py — LangGraph StateGraph orchestration for greenhouse control.

Refactored to run in-process without MQTT.
One invocation corresponds to one simulation timestep:
  [mpc|llm] -> check_ood -> [supervisor_review] -> approve -> log_step -> END

Telemetry is passed directly in state — no blocking queue needed.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    GraphState,
    LLMActionPayload,
    OODMetrics,
    SupervisorVerdict,
    TelemetryPayload,
)

if TYPE_CHECKING:
    from greenhouse_mvp.agents.notebooklm_agent import NotebookLMAgent
    from greenhouse_mvp.control_core.llm_controller import LLMController
    from greenhouse_mvp.control_core.mpc_controller import MPCController

logger = logging.getLogger(__name__)

RETRAIN_INTERVAL: int = 96  # steps between DAgger retrain checks
_dagger_lock = threading.Lock()

# Supervisor cooldown and warmup
SUPERVISOR_COOLDOWN_STEPS: int = 20
WARMUP_STEPS: int = 20


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def make_mpc_node(mpc_ctrl: "MPCController"):
    def run_mpc(state: GraphState) -> GraphState:
        telemetry: TelemetryPayload = state["telemetry"]
        if telemetry.step == 0:
            import numpy as np
            x0 = np.array([telemetry.t_in, telemetry.co2, telemetry.rh], dtype=np.float64)
            try:
                mpc_ctrl.initialise(x0)
            except Exception:
                logger.warning("run_mpc: MPC re-init failed — continuing anyway")
        action, ood = mpc_ctrl.step(telemetry)
        return {**state, "proposed_action": action, "ood_metrics": ood}
    return run_mpc


def make_llm_node(llm_ctrl: "LLMController"):
    def run_llm(state: GraphState) -> GraphState:
        telemetry: TelemetryPayload = state["telemetry"]
        action, reasoning = llm_ctrl.step(telemetry)
        return {**state, "proposed_action": action, "llm_reasoning": reasoning}
    return run_llm


def check_ood_node(state: GraphState) -> GraphState:
    ood: OODMetrics | None = state.get("ood_metrics")
    ood_detected = False if ood is None else not ood.in_distribution
    return {**state, "ood_detected": ood_detected}


def make_supervisor_node(agent: "NotebookLMAgent"):
    def supervisor_review(state: GraphState) -> GraphState:
        verdict: SupervisorVerdict = agent.review(state)
        telemetry: TelemetryPayload | None = state.get("telemetry")
        current_step = telemetry.step if telemetry else 0
        return {**state, "supervisor_verdict": verdict, "last_supervisor_step": current_step}
    return supervisor_review


def apply_override_node(state: GraphState) -> GraphState:
    verdict: SupervisorVerdict | None = state.get("supervisor_verdict")
    if verdict is not None and verdict.override_action is not None:
        return {**state, "proposed_action": verdict.override_action}
    logger.warning("apply_override_node: no valid override_action; keeping MPC proposal")
    return state


def approve_action_node(state: GraphState) -> GraphState:
    """Mark the proposed action as approved and store as final_action."""
    proposed: ActionPayload | None = state.get("proposed_action")
    if proposed is None:
        logger.error("approve_action_node: proposed_action is None")
        return state
    approved = proposed.model_copy(update={"approved": True})
    return {**state, "final_action": approved}


def reject_replan_node(state: GraphState) -> GraphState:
    new_count = state["retry_count"] + 1
    logger.info("reject_replan: retry %d/%d", new_count, state["max_retries"])
    return {**state, "retry_count": new_count, "proposed_action": None}


def make_log_node(mpc_ctrl: "MPCController", dagger_dataset: dict, weather_cfg: dict):
    def log_step(state: GraphState) -> GraphState:
        telemetry: TelemetryPayload | None = state.get("telemetry")
        final: ActionPayload | None = state.get("final_action")
        ood: OODMetrics | None = state.get("ood_metrics")
        verdict: SupervisorVerdict | None = state.get("supervisor_verdict")

        entry = {
            "step": telemetry.step if telemetry else None,
            "t_in": telemetry.t_in if telemetry else None,
            "co2": telemetry.co2 if telemetry else None,
            "rh": telemetry.rh if telemetry else None,
            "T_out": telemetry.T_out if telemetry else None,
            "rad": telemetry.rad if telemetry else None,
            "co2_out": telemetry.co2_out if telemetry else None,
            "sin_h": telemetry.sin_h if telemetry else None,
            "cos_h": telemetry.cos_h if telemetry else None,
            "action": final.model_dump() if final else None,
            "ood": ood.model_dump() if ood else None,
            "controller": state.get("controller_mode", "mpc"),
            "verdict": verdict.decision if verdict else state.get("llm_reasoning") or "AUTO_APPROVE",
        }

        new_log = list(state["episode_log"]) + [entry]

        if (
            len(new_log) % RETRAIN_INTERVAL == 0
            and state.get("controller_mode", "mpc") == "mpc"
        ):
            _trigger_dagger_retrain(new_log, mpc_ctrl, dagger_dataset, weather_cfg)

        return {**state, "episode_log": new_log, "_terminated": False}
    return log_step


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_by_controller(state: GraphState) -> str:
    return "run_llm" if state.get("controller_mode", "mpc") == "llm" else "run_mpc"


def route_after_check_ood(state: GraphState) -> str:
    agent_enabled = state.get("agent_enabled", False)
    if not state["ood_detected"] or not agent_enabled:
        return "approve_action"
    telemetry: TelemetryPayload | None = state.get("telemetry")
    current_step = telemetry.step if telemetry else 0
    if current_step < WARMUP_STEPS:
        return "approve_action"
    last_call = state.get("last_supervisor_step", -SUPERVISOR_COOLDOWN_STEPS)
    if current_step - last_call < SUPERVISOR_COOLDOWN_STEPS:
        return "approve_action"
    return "supervisor_review"


def route_after_supervisor(state: GraphState) -> str:
    verdict: SupervisorVerdict | None = state.get("supervisor_verdict")
    if verdict is None or verdict.decision == "APPROVE":
        return "approve_action"
    if verdict.decision == "OVERRIDE":
        return "apply_override"
    # REJECT
    if state["retry_count"] < state["max_retries"]:
        return "reject_replan"
    logger.warning("route_after_supervisor: max retries reached; approving best-effort action")
    return "approve_action"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(
    mpc_ctrl: "MPCController",
    llm_ctrl: "LLMController",
    agent: "NotebookLMAgent",
    dagger_dataset: "dict | None" = None,
    weather_cfg: "dict | None" = None,
):
    """Build and compile the LangGraph StateGraph (no MQTT needed)."""
    sg = StateGraph(GraphState)

    sg.add_node("run_mpc", make_mpc_node(mpc_ctrl))
    sg.add_node("run_llm", make_llm_node(llm_ctrl))
    sg.add_node("check_ood", check_ood_node)
    sg.add_node("supervisor_review", make_supervisor_node(agent))
    sg.add_node("apply_override", apply_override_node)
    sg.add_node("approve_action", approve_action_node)
    sg.add_node("reject_replan", reject_replan_node)
    sg.add_node("log_step", make_log_node(mpc_ctrl, dagger_dataset or {}, weather_cfg or {}))

    # Entry: branch by controller mode
    sg.set_conditional_entry_point(
        route_by_controller,
        {"run_mpc": "run_mpc", "run_llm": "run_llm"},
    )

    # MPC path
    sg.add_edge("run_mpc", "check_ood")
    sg.add_conditional_edges(
        "check_ood",
        route_after_check_ood,
        {"supervisor_review": "supervisor_review", "approve_action": "approve_action"},
    )
    sg.add_conditional_edges(
        "supervisor_review",
        route_after_supervisor,
        {
            "approve_action": "approve_action",
            "apply_override": "apply_override",
            "reject_replan": "reject_replan",
        },
    )
    sg.add_edge("apply_override", "approve_action")
    sg.add_edge("reject_replan", "run_mpc")

    # LLM path — direct approve
    sg.add_edge("run_llm", "approve_action")

    # Shared tail
    sg.add_edge("approve_action", "log_step")
    sg.add_edge("log_step", END)

    return sg.compile()


# ---------------------------------------------------------------------------
# DAgger retrain
# ---------------------------------------------------------------------------


def _trigger_dagger_retrain(
    episode_log: list[dict],
    mpc_ctrl: "MPCController",
    dagger_dataset: dict,
    weather_cfg: dict,
) -> None:
    """Trigger a DAgger retrain in a background thread (non-blocking)."""
    if not _dagger_lock.acquire(blocking=False):
        logger.info("DAgger retrain already in progress — skipping")
        return

    def _worker():
        try:
            _run_dagger_worker(mpc_ctrl, dagger_dataset, weather_cfg)
        except Exception:
            logger.exception("DAgger retrain failed")
        finally:
            _dagger_lock.release()

    threading.Thread(target=_worker, daemon=True, name="dagger-retrain").start()
    logger.info("DAgger retrain triggered after %d steps", len(episode_log))


def _run_dagger_worker(
    mpc_ctrl: "MPCController",
    dagger_dataset: dict,
    weather_cfg: dict,
) -> None:
    """Full DAgger iteration — collects new data and retrains the SINDy model."""
    import math

    import gymnasium as gym
    import numpy as np
    import pysindy as ps
    from sklearn.preprocessing import StandardScaler

    import gl_gym  # noqa: F401
    from greenhouse_mvp.control_core.mpc_controller import MPCController as _MPC
    from greenhouse_mvp.environment.tvp_forecast import WeatherForecastTVP
    from greenhouse_mvp.sindy_pipeline.physics_features import (
        FEATURE_NAMES,
        compute_physics_features,
    )
    from greenhouse_mvp.sindy_pipeline.sindy_fitter import SINDyFitter

    env_id = weather_cfg.get("env_id", "gl_gym/GreenLightTomato-v0")
    base_start_date = weather_cfg.get("start_date", "2010-02-28")
    episode_days: int = weather_cfg.get("dagger_episode_days", 5)
    n_days_full: int = weather_cfg.get("n_days", 60)
    period = int(mpc_ctrl._period)
    horizon: int = mpc_ctrl._horizon
    steps_per_episode = episode_days * int(86400 / period)

    dagger_env = gym.make(
        env_id,
        normalize_actions=False,
        observation_modules=[
            "IndoorClimateObservations",
            "WeatherObservations",
            "BasicCropObservations",
        ],
        season_length=episode_days,
    )

    dagger_weather = WeatherForecastTVP(
        env_id=env_id,
        start_date=base_start_date,
        n_days=episode_days,
        period=period,
    )
    dagger_mpc = _MPC(
        sindy_model=mpc_ctrl._sindy_model,
        scaler_x=mpc_ctrl._scaler_x,
        scaler_u=mpc_ctrl._scaler_u,
        weather_provider=dagger_weather,
        horizon=horizon,
        period=float(period),
        mu_train=mpc_ctrl._mu_train,
        cov_inv=mpc_ctrl._cov_inv,
    )

    obs, _ = dagger_env.reset(options={"start_date": base_start_date}, seed=0)
    indoor = obs["IndoorClimateObservations"]
    x0 = np.array([float(indoor[1]), float(indoor[0]), float(indoor[2])])
    dagger_mpc.initialise(x0)

    from greenhouse_mvp.environment.sim_adapter import obs_to_telemetry, action_to_array

    xs, us = [], []
    for _ in range(steps_per_episode):
        telemetry = obs_to_telemetry(obs, 0, period)
        action, _ = dagger_mpc.step(telemetry)
        u_arr = action_to_array(action)

        x_state = np.array([telemetry.t_in, telemetry.co2, telemetry.rh])
        feat = compute_physics_features(
            t_in=telemetry.t_in, co2=telemetry.co2, rh=telemetry.rh,
            T_out=telemetry.T_out, rad=telemetry.rad, co2_out=telemetry.co2_out,
            u_vec=u_arr,
        )
        xs.append(x_state)
        us.append(feat)

        obs, _, terminated, truncated, _ = dagger_env.step(u_arr)
        if terminated or truncated:
            break

    dagger_env.close()

    if len(xs) < 10:
        logger.warning("DAgger: not enough data points (%d); skipping retrain", len(xs))
        return

    # Aggregate with previous DAgger data
    xs_all = np.array(xs)
    us_all = np.array(us)
    if "xs" in dagger_dataset:
        xs_all = np.vstack([dagger_dataset["xs"], xs_all])
        us_all = np.vstack([dagger_dataset["us"], us_all])
    dagger_dataset["xs"] = xs_all
    dagger_dataset["us"] = us_all

    # Refit scalers
    new_scaler_x = StandardScaler().fit(xs_all)
    new_scaler_u = StandardScaler().fit(us_all)

    # Retrain SINDy
    fitter = SINDyFitter(threshold=0.05, alpha=0.01)
    xs_sc = new_scaler_x.transform(xs_all)
    us_sc = new_scaler_u.transform(us_all)
    new_sindy = fitter.fit(xs_sc, us_sc, t=float(period))

    # New weather forecast for live episode
    new_weather = WeatherForecastTVP(
        env_id=env_id,
        start_date=base_start_date,
        n_days=n_days_full,
        period=period,
    )

    # Hot-swap the live controller
    mu_new = us_sc.mean(axis=0)
    cov_new = np.linalg.pinv(np.cov(us_sc.T))
    mpc_ctrl.update_model(
        new_sindy=new_sindy,
        new_scaler_x=new_scaler_x,
        new_scaler_u=new_scaler_u,
        weather_provider=new_weather,
        mu_train=mu_new,
        cov_inv=cov_new,
    )
    logger.info("DAgger retrain complete — SINDy model updated")
