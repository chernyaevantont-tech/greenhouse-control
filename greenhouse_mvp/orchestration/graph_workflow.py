"""
graph_workflow.py — LangGraph StateGraph orchestration for greenhouse control.

One invocation of the compiled graph corresponds to one simulation timestep:
    ingest_telemetry → run_mpc → check_ood → [supervisor_review] → approve/reject → log_step → END

See plan/04_langgraph_orchestration.md for the full design spec.
"""

from __future__ import annotations

import logging
import threading
from queue import Queue
from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from greenhouse_mvp.orchestration.schemas import (
    ActionPayload,
    AgentControlPayload,
    ControllerSelectPayload,
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
    from greenhouse_mvp.orchestration.mqtt_bus import MQTTBus

logger = logging.getLogger(__name__)

# How often (in steps) to trigger a DAgger retrain check.
RETRAIN_INTERVAL: int = 96  # ≈ 1 day at 15-min timesteps

# Prevents concurrent DAgger retrains: acquired non-blocking inside the worker thread.
_dagger_lock = threading.Lock()

# Mutable configs updated from MQTT dashboard control messages.
# Safe to mutate from Paho network thread; reads happen on the graph thread.
import os as _os
_agent_cfg: dict = {"enabled": _os.environ.get("AGENT_ENABLED_DEFAULT", "false").lower() == "true"}
# Active controller: "mpc" or "llm". Switched by dashboard via greenhouse/control/controller.
_controller_cfg: dict = {"mode": _os.environ.get("CONTROLLER_MODE", "mpc").lower()}


# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------


def make_ingest_node(telemetry_queue: "Queue[TelemetryPayload]"):
    """
    Returns a node that blocks on *telemetry_queue* until the SimAdapter
    pushes the next TelemetryPayload, then resets per-tick mutable state.
    """

    def ingest_telemetry(state: GraphState) -> GraphState:
        tel = telemetry_queue.get(timeout=60.0)
        # Detect simulation reset: step rolls back to 0 after a running episode.
        episode_log = state.get("episode_log", [])
        if tel.step == 0 and len(episode_log) > 0:
            logger.info(
                "ingest_telemetry: simulation reset detected after %d steps — clearing episode log",
                len(episode_log),
            )
            episode_log = []
        return {
            **state,
            "telemetry": tel,
            "retry_count": 0,
            "proposed_action": None,
            "supervisor_verdict": None,
            "final_action": None,
            "ood_metrics": None,
            "ood_detected": False,
            "llm_reasoning": None,
            "episode_log": episode_log,
            # Mirror the current global controller mode into state.
            "controller_mode": _controller_cfg["mode"],
        }

    return ingest_telemetry


def make_mpc_node(mpc_ctrl: "MPCController"):
    """Returns a node that calls MPCController.step() and stores the results."""

    def run_mpc(state: GraphState) -> GraphState:
        telemetry: TelemetryPayload = state["telemetry"]
        # Re-initialise the MPC when the simulation resets so its internal
        # state stays consistent with the new episode.
        if telemetry.step == 0:
            import numpy as np
            x0 = np.array(
                [telemetry.t_in, telemetry.co2, telemetry.rh], dtype=np.float64
            )
            try:
                mpc_ctrl.initialise(x0)
            except Exception:  # noqa: BLE001
                logger.warning("run_mpc: MPC re-init on reset failed — continuing anyway")
        action, ood = mpc_ctrl.step(telemetry)
        return {**state, "proposed_action": action, "ood_metrics": ood}

    return run_mpc


def make_llm_node(llm_ctrl: "LLMController", bus: "MQTTBus"):
    """Returns a node that calls LLMController.step() and stores the result."""

    def run_llm(state: GraphState) -> GraphState:
        telemetry: TelemetryPayload = state["telemetry"]
        action, reasoning = llm_ctrl.step(telemetry)
        # Publish reasoning payload for the dashboard.
        llm_payload = LLMActionPayload(
            step=telemetry.step,
            reasoning=reasoning,
            uBoil=action.uBoil,
            uCO2=action.uCO2,
            uThScr=action.uThScr,
            uVent=action.uVent,
            uLamp=action.uLamp,
            uBlScr=action.uBlScr,
        )
        bus.publish("greenhouse/llm/action", llm_payload, qos=0)
        return {**state, "proposed_action": action, "llm_reasoning": reasoning}

    return run_llm


def check_ood_node(state: GraphState) -> GraphState:
    """Set ood_detected flag from OODMetrics."""
    ood: OODMetrics | None = state.get("ood_metrics")
    ood_detected = False if ood is None else not ood.in_distribution
    return {**state, "ood_detected": ood_detected}


def make_supervisor_node(agent: "NotebookLMAgent"):
    """Returns a node that calls the LLM supervisor agent."""

    def supervisor_review(state: GraphState) -> GraphState:
        verdict: SupervisorVerdict = agent.review(state)
        telemetry: TelemetryPayload | None = state.get("telemetry")
        current_step = telemetry.step if telemetry else 0
        return {**state, "supervisor_verdict": verdict, "last_supervisor_step": current_step}

    return supervisor_review


def apply_override_node(state: GraphState) -> GraphState:
    """Replace the proposed action with the supervisor's override action."""
    verdict: SupervisorVerdict | None = state.get("supervisor_verdict")
    if verdict is not None and verdict.override_action is not None:
        return {**state, "proposed_action": verdict.override_action}
    logger.warning("apply_override_node: no valid override_action found; keeping MPC proposal")
    return state


def make_approve_node(bus: "MQTTBus"):
    """Returns a node that marks the action as approved and publishes it."""

    def approve_action(state: GraphState) -> GraphState:
        proposed: ActionPayload | None = state.get("proposed_action")
        if proposed is None:
            logger.error("approve_action: proposed_action is None – cannot publish")
            return state
        approved = proposed.model_copy(update={"approved": True})
        bus.publish("greenhouse/action/approved", approved, qos=1)
        return {**state, "final_action": approved}

    return approve_action


def reject_replan_node(state: GraphState) -> GraphState:
    """Increment retry counter and clear the failed proposal so run_mpc is called again."""
    new_count = state["retry_count"] + 1
    logger.info("reject_replan: retry %d/%d", new_count, state["max_retries"])
    return {**state, "retry_count": new_count, "proposed_action": None}


def make_log_node(
    mpc_ctrl: "MPCController",
    dagger_dataset: dict,
    weather_cfg: dict,
    bus: "MQTTBus | None" = None,
):
    """
    Returns a log_step node that records telemetry + action (including weather
    fields needed for DAgger feature reconstruction), and triggers DAgger
    retraining every RETRAIN_INTERVAL steps (MPC mode only).
    """

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

        # DAgger retraining only makes sense when running in MPC mode.
        if (
            len(new_log) % RETRAIN_INTERVAL == 0
            and state.get("controller_mode", "mpc") == "mpc"
        ):
            _trigger_dagger_retrain(new_log, mpc_ctrl, dagger_dataset, weather_cfg, bus)

        return {**state, "episode_log": new_log, "_terminated": False}

    return log_step


# Minimum number of steps between consecutive LLM supervisor calls.
SUPERVISOR_COOLDOWN_STEPS: int = 20

# Number of initial steps during which the LLM is never called.
# Gives the MPC time to reach a stable operating point before supervision starts.
WARMUP_STEPS: int = 20


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------


def route_after_check_ood(state: GraphState) -> str:
    if not state["ood_detected"] or not _agent_cfg["enabled"]:
        return "approve_action"
    telemetry: TelemetryPayload | None = state.get("telemetry")
    current_step = telemetry.step if telemetry else 0
    if current_step < WARMUP_STEPS:
        logger.debug(
            "OOD detected at step %d but still in warmup period (%d steps)",
            current_step, WARMUP_STEPS,
        )
        return "approve_action"
    last_call = state.get("last_supervisor_step", -SUPERVISOR_COOLDOWN_STEPS)
    if current_step - last_call < SUPERVISOR_COOLDOWN_STEPS:
        logger.debug(
            "OOD detected at step %d but supervisor is on cooldown (last called step %d)",
            current_step, last_call,
        )
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
    # Exhausted retries → best-effort approve
    logger.warning(
        "route_after_supervisor: max retries (%d) reached; approving best-effort action",
        state["max_retries"],
    )
    return "approve_action"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def route_by_controller(state: GraphState) -> str:
    """Dispatch to the correct controller node based on the current mode."""
    return "run_llm" if state.get("controller_mode", "mpc") == "llm" else "run_mpc"


def build_graph(
    mpc_ctrl: "MPCController",
    llm_ctrl: "LLMController",
    agent: "NotebookLMAgent",
    bus: "MQTTBus",
    telemetry_queue: "Queue[TelemetryPayload]",
    dagger_dataset: "dict | None" = None,
    weather_cfg: "dict | None" = None,
):
    """
    Construct and compile the LangGraph StateGraph.

    After ``ingest_telemetry`` the graph branches:
      - controller_mode == "mpc"  →  run_mpc → check_ood → [supervisor_review] → approve
      - controller_mode == "llm"  →  run_llm → approve

    Returns
    -------
    CompiledGraph
        Ready to call via ``graph.invoke(state)``.
    """
    sg = StateGraph(GraphState)

    sg.add_node("ingest_telemetry", make_ingest_node(telemetry_queue))
    sg.add_node("run_mpc", make_mpc_node(mpc_ctrl))
    sg.add_node("run_llm", make_llm_node(llm_ctrl, bus))
    sg.add_node("check_ood", check_ood_node)
    sg.add_node("supervisor_review", make_supervisor_node(agent))
    sg.add_node("apply_override", apply_override_node)
    sg.add_node("approve_action", make_approve_node(bus))
    sg.add_node("reject_replan", reject_replan_node)
    sg.add_node("log_step", make_log_node(mpc_ctrl, dagger_dataset or {}, weather_cfg or {}, bus))

    sg.set_entry_point("ingest_telemetry")

    # Route to MPC or LLM controller based on current mode.
    sg.add_conditional_edges(
        "ingest_telemetry",
        route_by_controller,
        {
            "run_mpc": "run_mpc",
            "run_llm": "run_llm",
        },
    )

    # MPC path
    sg.add_edge("run_mpc", "check_ood")
    sg.add_conditional_edges(
        "check_ood",
        route_after_check_ood,
        {
            "supervisor_review": "supervisor_review",
            "approve_action": "approve_action",
        },
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

    # LLM path — direct to approve
    sg.add_edge("run_llm", "approve_action")

    # Shared tail
    sg.add_edge("approve_action", "log_step")
    sg.add_edge("log_step", END)

    return sg.compile()


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------


def run_episode(graph, initial_state: GraphState) -> list[dict]:
    """
    Drive the compiled LangGraph for a full episode (until env is done).

    Parameters
    ----------
    graph:
        Compiled LangGraph returned by ``build_graph()``.
    initial_state:
        Seed state — typically has ``episode_log=[]``, ``max_retries=2``,
        ``retry_count=0``, all payloads ``None``.

    Returns
    -------
    list[dict]
        The accumulated ``episode_log``.
    """
    state = initial_state
    while True:
        state = graph.invoke(state)
        if state.get("_terminated"):
            break
    return state["episode_log"]


# ---------------------------------------------------------------------------
# DAgger: episode runner + retrain worker
# ---------------------------------------------------------------------------


def _run_dagger_worker(
    mpc_ctrl: "MPCController",
    dagger_dataset: dict,
    weather_cfg: dict,
    bus: "MQTTBus | None" = None,
) -> None:
    """
    Full DAgger iteration — matches the notebook cell ``#VSC-94001a16`` exactly.

    1. Build a fresh do_mpc controller from the current SINDy model.
    2. Run a short MPC episode (``dagger_episode_days`` days) collecting
       (state_k, physics_features_k, state_{k+1}) triples.
    3. Aggregate with all previously collected DAgger data.
    4. Refit scalers on the full aggregated dataset.
    5. Retrain SINDy (STLSQ, thr=0.05, alpha=0.01).
    6. Build a fresh full-length WeatherForecastTVP for the live MPC.
    7. Hot-swap the live MPCController via ``update_model()``.
    """
    import math

    import gymnasium as gym
    import numpy as np
    import pysindy as ps
    from sklearn.preprocessing import StandardScaler

    import gl_gym  # noqa: F401 — registers gl_gym namespace
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

    # Offset the episode start_date to match the current simulation time so that
    # DAgger collects data from the same part of the season as the live controller.
    # Without this, every DAgger episode starts from day 1 regardless of the
    # current simulation day, causing the aggregated dataset to be dominated by
    # early-season weather and making the model progressively worse.
    import pandas as _pd
    current_sim_day = int(mpc_ctrl._t0 / (86400.0))  # whole days elapsed
    episode_start_date = (
        _pd.to_datetime(base_start_date) + _pd.Timedelta(days=current_sim_day)
    ).strftime("%Y-%m-%d")
    logger.info(
        "DAgger: sim day %d → episode start_date=%s", current_sim_day, episode_start_date
    )
    start_date = episode_start_date

    sindy_model = mpc_ctrl._sindy_model
    scaler_x = mpc_ctrl._scaler_x
    scaler_u = mpc_ctrl._scaler_u

    # --- Step 2: Weather forecast for the short DAgger episode ---
    logger.info("DAgger: building %d-day episode weather forecast…", episode_days)
    try:
        wp_episode = WeatherForecastTVP(
            env_id=env_id,
            start_date=start_date,
            n_days=episode_days,
            horizon=horizon,
            period=period,
        )
    except Exception:
        logger.exception("DAgger: WeatherForecastTVP (episode) failed")
        return

    # --- Step 3: Build a fresh do_mpc controller for the episode ---
    try:
        mpc_ep, _, _, _ = _MPC._build(
            sindy_model, scaler_x, scaler_u, wp_episode, horizon, period
        )
    except Exception:
        logger.exception("DAgger: MPCController._build failed")
        return

    # --- Step 4: Run the DAgger episode ---
    try:
        env = gym.make(
            env_id,
            normalize_actions=False,
            observation_modules=[
                "IndoorClimateObservations",
                "WeatherObservations",
                "BasicCropObservations",
            ],
        )
        obs, _ = env.reset(options={"start_date": start_date}, seed=42)
    except Exception:
        logger.exception("DAgger: gym.make / env.reset failed")
        return

    indoor = obs["IndoorClimateObservations"]
    x0 = np.array(
        [float(indoor[1]), float(indoor[0]), float(indoor[2])], dtype=np.float64
    ).reshape(-1, 1)
    mpc_ep.x0 = x0
    mpc_ep.set_initial_guess()

    new_states: list[np.ndarray] = []
    new_weather_list: list[list[float]] = []
    new_sin_cos: list[list[float]] = []
    new_actions: list[np.ndarray] = []

    logger.info("DAgger: running %d-step MPC episode…", steps_per_episode)
    for step in range(steps_per_episode):
        try:
            u_opt = mpc_ep.make_step(x0).flatten().astype(np.float32)
        except Exception:
            logger.exception("DAgger: mpc.make_step failed at step %d", step)
            break
        u_opt = np.clip(u_opt, 0.0, 1.0)

        weather_obs = obs["WeatherObservations"]
        new_states.append(x0.flatten())
        new_actions.append(u_opt.copy())
        new_weather_list.append(
            [float(weather_obs[1]), float(weather_obs[0]), float(weather_obs[3])]
        )
        hour = (step * period / 3600.0) % 24.0
        new_sin_cos.append(
            [math.sin(2 * math.pi * hour / 24.0), math.cos(2 * math.pi * hour / 24.0)]
        )

        obs, _, terminated, truncated, _ = env.step(u_opt)
        indoor_new = obs["IndoorClimateObservations"]
        x0 = np.array(
            [float(indoor_new[1]), float(indoor_new[0]), float(indoor_new[2])],
            dtype=np.float64,
        ).reshape(-1, 1)

        # Early stopping — matches notebook: abort if temperature leaves safe range
        if x0[0, 0] < 2.0 or x0[0, 0] > 45.0:
            logger.warning(
                "DAgger: early stop at step %d, t_in=%.1f°C", step, x0[0, 0]
            )
            break
        if terminated or truncated:
            break

    env.close()

    if len(new_states) < 2:
        logger.warning(
            "DAgger: episode too short (%d steps), skipping retrain", len(new_states)
        )
        return

    # Append the final state to form aligned (x_k, u_k, x_{k+1}) pairs
    new_states.append(x0.flatten())

    new_states_arr = np.array(new_states, dtype=np.float64)
    new_actions_phys = compute_physics_features(
        new_states_arr[:-1],
        np.array(new_weather_list, dtype=np.float64),
        np.array(new_sin_cos, dtype=np.float64),
        np.array(new_actions, dtype=np.float64),
    )
    logger.info("DAgger: collected %d new transition pairs.", len(new_actions))

    # --- Step 6: Dataset Aggregation (DAgger core) ---
    new_x_in = new_states_arr[:-1]
    new_u_in = new_actions_phys
    new_x_out = new_states_arr[1:]

    if dagger_dataset.get("x_in") is None:
        dagger_dataset["x_in"] = new_x_in
        dagger_dataset["u_in"] = new_u_in
        dagger_dataset["x_out"] = new_x_out
    else:
        dagger_dataset["x_in"] = np.vstack([dagger_dataset["x_in"], new_x_in])
        dagger_dataset["u_in"] = np.vstack([dagger_dataset["u_in"], new_u_in])
        dagger_dataset["x_out"] = np.vstack([dagger_dataset["x_out"], new_x_out])

    full_x_in_raw: np.ndarray = dagger_dataset["x_in"]
    full_u_in_raw: np.ndarray = dagger_dataset["u_in"]
    full_x_out_raw: np.ndarray = dagger_dataset["x_out"]

    # --- Step 7: Refit scalers on the full aggregated dataset ---
    new_scaler_x = StandardScaler().fit(full_x_in_raw)
    new_scaler_u = StandardScaler().fit(full_u_in_raw)

    x_in_sc = new_scaler_x.transform(full_x_in_raw)
    u_in_sc = new_scaler_u.transform(full_u_in_raw)
    x_out_sc = new_scaler_x.transform(full_x_out_raw)

    # --- Step 7: Retrain SINDy ---
    new_sindy = ps.SINDy(
        optimizer=ps.STLSQ(
            threshold=SINDyFitter.DEFAULT_THR,
            alpha=SINDyFitter.DEFAULT_ALPHA,
            max_iter=200,
            normalize_columns=False,
        ),
        feature_library=ps.PolynomialLibrary(degree=1, include_bias=True),
        feature_names=FEATURE_NAMES,
    )
    try:
        new_sindy.fit(x_in_sc, u=u_in_sc, x_dot=x_out_sc, t=float(period))
    except Exception:
        logger.exception("DAgger: SINDy.fit failed")
        return

    n_nz = int(np.count_nonzero(new_sindy.coefficients()))
    n_total = new_sindy.coefficients().size
    logger.info(
        "DAgger: SINDy retrained. Non-zero: %d/%d. Aggregated samples: %d",
        n_nz, n_total, len(full_x_in_raw),
    )

    # Compute OOD statistics on the full scaled dataset
    combined = np.hstack([x_in_sc, u_in_sc])
    mu_train = combined.mean(axis=0)
    cov_inv = np.linalg.pinv(np.cov(combined.T))

    # --- Step 8: Full-length WeatherForecastTVP for the live MPC ---
    # IMPORTANT: use base_start_date (not episode_start_date) so that the TVP
    # index k_start = mpc.t0 / period correctly maps into the weather array.
    # episode_start_date is only used for DAgger data collection.
    try:
        wp_full = WeatherForecastTVP(
            env_id=env_id,
            start_date=base_start_date,
            n_days=n_days_full,
            horizon=horizon,
            period=period,
        )
    except Exception:
        logger.exception("DAgger: WeatherForecastTVP (full) failed")
        return

    # --- Step 9: Hot-swap the live MPCController ---
    # Pause the simulation while swapping so that the sim_adapter doesn't
    # send stale telemetry against a partially-updated controller.
    _sim_paused_by_dagger = False
    if bus is not None:
        try:
            from greenhouse_mvp.orchestration.schemas import SimControlPayload as _SCP
            bus.publish("greenhouse/control/speed", _SCP(paused=True), qos=1)
            _sim_paused_by_dagger = True
            logger.info("DAgger: simulation paused for hot-swap.")
        except Exception:
            logger.warning("DAgger: could not pause simulation before hot-swap.")
    try:
        mpc_ctrl.update_model(
            new_sindy=new_sindy,
            new_scaler_x=new_scaler_x,
            new_scaler_u=new_scaler_u,
            weather_provider=wp_full,
            mu_train=mu_train,
            cov_inv=cov_inv,
        )
        logger.info("DAgger: MPCController hot-swapped successfully.")
    except Exception:
        logger.exception("DAgger: MPCController.update_model failed")
    finally:
        if _sim_paused_by_dagger and bus is not None:
            try:
                from greenhouse_mvp.orchestration.schemas import SimControlPayload as _SCP
                bus.publish("greenhouse/control/speed", _SCP(paused=False, speed_multiplier=1.0), qos=1)
                logger.info("DAgger: simulation resumed after hot-swap.")
            except Exception:
                logger.warning("DAgger: could not resume simulation after hot-swap.")


def _trigger_dagger_retrain(
    episode_log: list[dict],
    mpc_ctrl: "MPCController",
    dagger_dataset: dict,
    weather_cfg: dict,
    bus: "MQTTBus | None" = None,
) -> None:
    """
    Start a background thread that runs a full DAgger iteration.
    Non-blocking: the current MPC model stays active during retraining.
    Skips silently if a retrain is already in progress.
    """

    def _worker() -> None:
        if not _dagger_lock.acquire(blocking=False):
            logger.info(
                "DAgger retrain already running — skipping trigger at %d log entries.",
                len(episode_log),
            )
            return
        try:
            logger.info("DAgger retrain started (%d log entries).", len(episode_log))
            _run_dagger_worker(mpc_ctrl, dagger_dataset, weather_cfg, bus)
        except Exception:
            logger.exception("DAgger: _run_dagger_worker raised an exception")
        finally:
            _dagger_lock.release()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


if __name__ == "__main__":
    import os
    import pickle
    import signal
    from queue import Queue

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from greenhouse_mvp.agents.notebooklm_agent import NotebookLMAgent
    from greenhouse_mvp.control_core.llm_controller import LLMController
    from greenhouse_mvp.control_core.mpc_controller import MPCController
    from greenhouse_mvp.environment.tvp_forecast import WeatherForecastTVP
    from greenhouse_mvp.orchestration.mqtt_bus import MQTTBus

    _host = os.environ.get("MQTT_HOST", "localhost")
    _port = int(os.environ.get("MQTT_PORT", "1883"))
    _model_path = os.environ.get("SINDY_MODEL_PATH", "/app/models/sindy_model.pkl")
    _max_retries = int(os.environ.get("MAX_RETRIES", "2"))
    _horizon = int(os.environ.get("MPC_HORIZON", "20"))
    _start_date = os.environ.get("START_DATE", "2010-02-28")
    _n_days = int(os.environ.get("N_DAYS", "60"))
    _period = int(os.environ.get("PERIOD", "900"))

    with open(_model_path, "rb") as _fh:
        _bundle = pickle.load(_fh)

    _weather = WeatherForecastTVP(
        start_date=_start_date,
        n_days=_n_days,
        horizon=_horizon,
        period=_period,
    )

    _bus = MQTTBus(host=_host, port=_port)
    _bus.loop_start()

    _telemetry_queue: Queue[TelemetryPayload] = Queue()
    _bus.subscribe(
        topic="greenhouse/telemetry",
        schema=TelemetryPayload,
        handler=_telemetry_queue.put,
        qos=0,
    )

    _ctrl = MPCController(
        sindy_model=_bundle["model"],
        scaler_x=_bundle["scaler_x"],
        scaler_u=_bundle["scaler_u"],
        weather_provider=_weather,
        bus=_bus,
        horizon=_horizon,
        mu_train=_bundle.get("mu_train"),
        cov_inv=_bundle.get("cov_inv"),
        auto_subscribe=False,   # LangGraph drives step() calls directly
    )

    _agent = NotebookLMAgent(
        backend=os.environ.get("LLM_BACKEND", "openai"),
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    )

    _llm_timeout_raw = os.environ.get("LLM_TIMEOUT", "")
    _llm_ctrl = LLMController(
        backend=os.environ.get("LLM_BACKEND", "openai"),
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        timeout=float(_llm_timeout_raw) if _llm_timeout_raw else None,
        call_interval=int(os.environ.get("LLM_CALL_INTERVAL", "1")),
    )

    _dagger_dataset: dict = {
        "x_in": _bundle.get("x_in_raw"),
        "u_in": _bundle.get("u_in_raw"),
        "x_out": _bundle.get("x_out_raw"),
    }
    if _dagger_dataset["x_in"] is not None:
        logger.info(
            "orchestration: DAgger dataset pre-seeded with %d bootstrap samples.",
            len(_dagger_dataset["x_in"]),
        )
    else:
        logger.warning(
            "orchestration: bundle has no raw training data — DAgger will start from scratch. "
            "Re-run bootstrap to regenerate the model file."
        )
    _weather_cfg: dict = {
        "env_id": "gl_gym/GreenLightTomato-v0",
        "start_date": _start_date,
        "n_days": _n_days,
        "dagger_episode_days": 5,
    }
    _graph = build_graph(_ctrl, _llm_ctrl, _agent, _bus, _telemetry_queue, _dagger_dataset, _weather_cfg)

    # --- Agent on/off control from dashboard ---
    def _on_agent_control(msg: AgentControlPayload) -> None:
        _agent_cfg["enabled"] = msg.enabled
        logger.info("LLM supervisor %s by dashboard", "ENABLED" if msg.enabled else "DISABLED")

    _bus.subscribe(
        topic="greenhouse/control/agent",
        schema=AgentControlPayload,
        handler=_on_agent_control,
        qos=1,
    )

    # --- Controller mode selection from dashboard ---
    def _on_controller_select(msg: ControllerSelectPayload) -> None:
        _controller_cfg["mode"] = msg.mode
        logger.info("Controller switched to '%s' by dashboard", msg.mode)

    _bus.subscribe(
        topic="greenhouse/control/controller",
        schema=ControllerSelectPayload,
        handler=_on_controller_select,
        qos=1,
    )

    _initial_state: GraphState = {
        "telemetry": None,
        "proposed_action": None,
        "ood_metrics": None,
        "supervisor_verdict": None,
        "final_action": None,
        "ood_detected": False,
        "last_supervisor_step": -SUPERVISOR_COOLDOWN_STEPS,
        "retry_count": 0,
        "max_retries": _max_retries,
        "controller_mode": _controller_cfg["mode"],
        "llm_reasoning": None,
        "episode_log": [],
        "_terminated": False,
    }

    logger.info("orchestration: graph ready, waiting for sim_adapter to publish telemetry...")
    try:
        run_episode(_graph, _initial_state)
    finally:
        _agent.close()
        _llm_ctrl.close()
        _bus.loop_stop()
