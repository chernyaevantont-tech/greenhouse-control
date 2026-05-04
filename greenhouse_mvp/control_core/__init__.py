"""control_core — do_mpc MPC controller backed by a SINDy surrogate model."""

from greenhouse_mvp.control_core.mpc_controller import MPCController, OOD_THRESHOLD

__all__ = ["MPCController", "OOD_THRESHOLD"]
