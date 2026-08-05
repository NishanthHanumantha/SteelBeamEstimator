"""
Phase T1.7.1 — Graph-Aware Render Validation.
MODEL_VERSION: 9.4.1

Validation-only. Does not modify T1.7 graph generation or existing renderers.
"""
MODEL_VERSION = "9.4.1"
PHASE_ID = "T1.7.1"

from .phase_t171_orchestrator import PhaseT171Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseT171Orchestrator"]
