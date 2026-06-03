"""
Pydantic v2 schemas for all inter-module communication.
Every message travelling over the MQTT bus must be validated using one of these models.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from typing_extensions import TypedDict


class FaultSpec(BaseModel):
    """Describes a single injected fault for stress-testing LLM anomaly detection."""

    target: Literal[
        "t_in", "co2", "rh",
        "uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"
    ]
    fault_type: Literal["stuck_high", "stuck_low", "random", "offset", "dead", "min_floor", "max_cap"]
    start_step: int = 0
    # For stuck_high / stuck_low: the fixed value to emit
    # For offset: delta added to the real value
    # For min_floor: max(original, value)  — actuator can't go below this
    # For max_cap:   min(original, value)  — actuator can't go above this
    value: float = 0.0
    # For random: uniform(value_lo, value_hi)
    value_lo: float = 0.0
    value_hi: float = 1.0


# ---------------------------------------------------------------------------
# Incident / event schemas
# ---------------------------------------------------------------------------

INCIDENT_TYPES = Literal[
    "door_open",
    "heater_failure",
    "co2_supply_failure",
    "ventilation_stuck_open",
    "ventilation_stuck_closed",
    "lamp_failure",
    "thermal_screen_broken",
    "sensor_temp_stuck",
    "sensor_co2_drift",
    "sensor_rh_failure",
    "power_surge",
    "high_humidity_event",
]


class IncidentSpec(BaseModel):
    """A triggered incident / abnormal event in the greenhouse simulation."""

    incident_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    incident_type: INCIDENT_TYPES
    start_step: int = 0
    duration_steps: Optional[int] = None   # None = permanent until manually resolved
    severity: float = Field(default=1.0, ge=0.0, le=1.0)
    description: str = ""                  # optional operator annotation


class IncidentReport(BaseModel):
    """Output of the incident detection agent after analysing telemetry anomalies."""

    step: int
    detected_type: str              # incident type key, "nominal", or "unknown_anomaly"
    confidence: float               # [0.0, 1.0]
    affected_systems: List[str]
    repair_steps: List[str]         # ordered repair recommendations for the operator
    mitigation_action: Optional["ActionPayload"] = None  # suggested immediate control action
    reasoning: str                  # LLM reasoning text
    urgency: Literal["low", "medium", "high", "critical"] = "medium"


class IncidentAlert(BaseModel):
    """Emitted via SSE when an incident is triggered, resolved, or expires."""

    incident_id: str
    incident_type: str
    action: Literal["triggered", "resolved", "expired"]
    step: int
    severity: float
    description: str


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
    # Whether the LLM supervisor agent is enabled (MPC path only)
    agent_enabled: bool
    # LLM controller reasoning text from the last step
    llm_reasoning: str | None
    # Accumulator for logging / DAgger data collection
    episode_log: list[dict]
    # Set to True when the simulation episode terminates
    _terminated: bool
    # ---- Incident / event tracking ----
    # Active incidents passed in from IncidentManager (serialised dicts)
    active_incidents: list[dict]
    # Result from the incident detection agent (None if not triggered this step)
    incident_report: IncidentReport | None
    # Step of the last incident detector LLM call (for cooldown)
    last_incident_detect_step: int
    # Whether incident detector is enabled
    incident_detector_enabled: bool


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
    fault_report: str = "OK"  # LLM self-reported anomaly / fault diagnosis
    # Actuator signals [0.0, 1.0] — mirror of ActionPayload fields
    uBoil: float
    uCO2: float
    uThScr: float
    uVent: float
    uLamp: float
    uBlScr: float


# ---------------------------------------------------------------------------
# REST API / HTTP schemas (replace MQTT control topics)
# ---------------------------------------------------------------------------


class SimConfig(BaseModel):
    """Simulation configuration — can be updated at runtime before (re)start."""

    env_id: str = "gl_gym/GreenLightTomato-v0"
    start_date: str = "2010-02-28"
    n_days: int = 60
    period: int = 900
    controller_mode: Literal["mpc", "llm"] = "mpc"
    agent_enabled: bool = False
    speed_multiplier: float = 1.0
    mpc_horizon: int = 20
    llm_call_interval: int = 1
    llm_history_window: int = 1  # Number of past telemetry steps to include in LLM prompt (1 = current only)
    faults: List[FaultSpec] = Field(default_factory=list)  # Active fault injections


class SimStatus(BaseModel):
    """Returned by GET /api/status."""

    running: bool
    paused: bool
    step: int
    config: SimConfig
    latest_telemetry: TelemetryPayload | None = None
    latest_action: ActionPayload | None = None
    latest_ood: OODMetrics | None = None
    active_incidents: List[IncidentSpec] = Field(default_factory=list)
