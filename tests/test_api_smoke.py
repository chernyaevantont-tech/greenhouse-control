from __future__ import annotations

import pickle
import sys
import types

from fastapi.testclient import TestClient

from greenhouse_mvp.api import server
from greenhouse_mvp.api.simulation_runner import SimulationRunner
from greenhouse_mvp.orchestration.schemas import ActionPayload, OODMetrics


def test_status_and_config_endpoints() -> None:
    client = TestClient(server.app)

    status = client.get("/api/status")
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["running"] is False
    assert status_payload["config"]["controller_mode"] == "mpc"

    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["env_id"] == "gl_gym/GreenLightTomato-v0"


def test_simulation_runner_one_step_with_fake_sindy_artifact(monkeypatch, tmp_path) -> None:
    model_path = tmp_path / "sindy_model.pkl"
    with model_path.open("wb") as f:
        pickle.dump(
            {
                "model": "fake-model",
                "scaler_x": "fake-scaler-x",
                "scaler_u": "fake-scaler-u",
                "mu_train": None,
                "cov_inv": None,
            },
            f,
        )
    monkeypatch.setenv("SINDY_MODEL_PATH", str(model_path))

    class FakeEnv:
        def reset(self, options=None, seed=None):
            return _fake_obs(), {}

        def step(self, action_vec):
            return _fake_obs(), 0.0, True, False, {}

        def close(self):
            pass

    fake_gym = types.ModuleType("gymnasium")
    fake_gym.make = lambda *args, **kwargs: FakeEnv()
    monkeypatch.setitem(sys.modules, "gymnasium", fake_gym)
    monkeypatch.setitem(sys.modules, "gl_gym", types.ModuleType("gl_gym"))

    created_mpc_kwargs: list[dict] = []
    created_tvp_kwargs: list[dict] = []

    fake_mpc_module = types.ModuleType("greenhouse_mvp.control_core.mpc_controller")

    class FakeMPCController:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created_mpc_kwargs.append(kwargs)

        def initialise(self, x0):
            self.x0 = x0

    fake_mpc_module.MPCController = FakeMPCController
    monkeypatch.setitem(
        sys.modules,
        "greenhouse_mvp.control_core.mpc_controller",
        fake_mpc_module,
    )

    fake_llm_module = types.ModuleType("greenhouse_mvp.control_core.llm_controller")
    fake_llm_module.LLMController = lambda **kwargs: object()
    monkeypatch.setitem(
        sys.modules,
        "greenhouse_mvp.control_core.llm_controller",
        fake_llm_module,
    )

    fake_agent_module = types.ModuleType("greenhouse_mvp.agents.notebooklm_agent")
    fake_agent_module.NotebookLMAgent = lambda **kwargs: object()
    monkeypatch.setitem(
        sys.modules,
        "greenhouse_mvp.agents.notebooklm_agent",
        fake_agent_module,
    )

    fake_tvp_module = types.ModuleType("greenhouse_mvp.environment.tvp_forecast")

    class FakeWeatherForecastTVP:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created_tvp_kwargs.append(kwargs)

    fake_tvp_module.WeatherForecastTVP = FakeWeatherForecastTVP
    monkeypatch.setitem(
        sys.modules,
        "greenhouse_mvp.environment.tvp_forecast",
        fake_tvp_module,
    )

    fake_graph_module = types.ModuleType("greenhouse_mvp.orchestration.graph_workflow")

    class FakeGraph:
        def invoke(self, state):
            action = ActionPayload(
                step=state["telemetry"].step,
                approved=True,
                uBoil=0.3,
                uCO2=0.0,
                uThScr=1.0,
                uVent=0.0,
                uLamp=0.0,
                uBlScr=0.0,
            )
            ood = OODMetrics(
                step=state["telemetry"].step,
                mahalanobis_distance=0.0,
                max_residual=0.0,
                in_distribution=True,
                threshold_used=6.0,
            )
            return {**state, "final_action": action, "ood_metrics": ood}

    fake_graph_module.build_graph = lambda *args, **kwargs: FakeGraph()
    monkeypatch.setitem(
        sys.modules,
        "greenhouse_mvp.orchestration.graph_workflow",
        fake_graph_module,
    )

    runner = SimulationRunner()
    runner._run()

    status = runner.get_status()
    assert status.running is False
    assert status.step == 0
    assert status.latest_telemetry is not None
    assert status.latest_action is not None
    assert status.latest_action.approved is True
    assert status.latest_ood is not None
    assert created_mpc_kwargs[0]["horizon"] == runner.config.mpc_horizon
    assert created_tvp_kwargs[0]["horizon"] == runner.config.mpc_horizon


def _fake_obs() -> dict:
    return {
        "IndoorClimateObservations": [700.0, 20.0, 70.0],
        "WeatherObservations": [100.0, 10.0, 0.0, 410.0],
        "BasicCropObservations": [0.0],
    }
