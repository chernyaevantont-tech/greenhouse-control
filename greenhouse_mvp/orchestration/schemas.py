"""
Pydantic v2 schemas for all inter-module communication.
Every message travelling over the MQTT bus must be validated using one of these models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator
from typing_extensions import TypedDict


class TelemetryPayload(BaseModel):
    """Published by SimAdapter after every env.step() call."""

    step: int                    # Global simulation step counter
    timestamp_sim: float         # Simulation time in seconds from episode start
    # Controlled states
    t_in: float                  # Indoor temperature [°C]
    co2: float                   # Indoor CO2 concentration [ppm]
    rh: float                    # Relative humidity [%]
    # External disturbances (TVP for MPC)
    T_out: float                 # Outdoor temperature [°C]
    rad: float                   # Solar radiation [W/m²]
    co2_out: float               # Outdoor CO2 [ppm]
    # Time encoding
    sin_h: float                 # sin(2π * hour_of_day / 24)
    cos_h: float                 # cos(2π * hour_of_day / 24)


class ActionPayload(BaseModel):
    """
    Used for both proposed (MPC → Bus) and approved (Bus → Sim) actions.
    The `approved` flag distinguishes the two.
    All actuator signals are clamped to [0.0, 1.0].
    """

    step: int                    # Must match the triggering TelemetryPayload.step
    approved: bool = False       # False = proposed; True = approved by Supervisor
    # Actuator signals [0.0, 1.0]
    uBoil: float                 # Boiler heating
    uCO2: float                  # CO2 injection
    uThScr: float                # Thermal screen
    uVent: float                 # Ventilation
    uLamp: float                 # Supplementary lighting
    uBlScr: float                # Blackout screen

    @model_validator(mode="after")
    def clamp_actuators(self) -> "ActionPayload":
        for field in ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]:
            setattr(self, field, max(0.0, min(1.0, getattr(self, field))))
        return self


class OODMetrics(BaseModel):
    """
    Published by MPCController alongside the proposed action to quantify how far
    the current state is from the SINDy training distribution.
    """

    step: int
    mahalanobis_distance: float  # Distance from training set centroid
    max_residual: float          # Max absolute SINDy one-step prediction error
    in_distribution: bool        # True if mahalanobis_distance < threshold
    threshold_used: float        # The threshold applied (e.g., 3.0 sigma)


class SupervisorVerdict(BaseModel):
    """Returned by the NotebookLMAgent after evaluating the proposed action and OOD metrics."""

    step: int
    decision: Literal["APPROVE", "REJECT", "OVERRIDE"]
    # If OVERRIDE, these values replace the MPC proposal
    override_action: ActionPayload | None = None
    reason: str                  # Human-readable explanation from LLM
    confidence: float            # [0.0, 1.0] LLM self-reported confidence


class GraphState(TypedDict):
    """
    Shared mutable state flowing through the LangGraph StateGraph.
    Each node reads from it and writes back to it.
    """

    # Current tick data
    telemetry: TelemetryPayload | None
    proposed_action: ActionPayload | None
    ood_metrics: OODMetrics | None
    supervisor_verdict: SupervisorVerdict | None
    # Final resolved action (may be MPC proposal or LLM override)
    final_action: ActionPayload | None
    # Routing flags
    ood_detected: bool
    last_supervisor_step: int    # step index of the last LLM supervisor call (cooldown)
    retry_count: int             # Number of times MPC was asked to re-plan
    max_retries: int             # Config: abort to fallback after N retries
    # Active controller: "mpc" or "llm"
    controller_mode: str
    # LLM controller reasoning text from the last step
    llm_reasoning: str | None
    # Accumulator for logging / DAgger data collection
    episode_log: list[dict]
    # Set to True when the simulation episode terminates
    _terminated: bool


class SimControlPayload(BaseModel):
    """Published by the dashboard to control simulation speed and pause state."""

    paused: bool = False
    speed_multiplier: float = 1.0  # 0.1 to 20.0 — multiplier for real-time step rate


class AgentControlPayload(BaseModel):
    """Published by the dashboard to enable/disable the LLM supervisor agent."""

    enabled: bool = True


class ControllerSelectPayload(BaseModel):
    """Published by the dashboard to switch between MPC and LLM controllers."""

    mode: Literal["mpc", "llm"] = "mpc"


class SimResetPayload(BaseModel):
    """Published by the dashboard to restart the simulation episode."""

    requested: bool = True


class LLMActionPayload(BaseModel):
    """
    Published on ``greenhouse/llm/action`` each step the LLM controller is active.
    Carries the reasoning string alongside the chosen actuator values.
    """

    step: int
    reasoning: str
    # Actuator signals [0.0, 1.0] — mirror of ActionPayload fields
    uBoil: float
    uCO2: float
    uThScr: float
    uVent: float
    uLamp: float
    uBlScr: float
