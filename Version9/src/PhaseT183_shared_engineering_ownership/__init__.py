"""
Phase T1.8.3 — Shared Engineering Ownership & Multi-Beam Annotation Scope.
MODEL_VERSION: 9.5.3

Additive ownership enhancement. Does not modify T1.7–T1.8.2.
"""
MODEL_VERSION = "9.5.3"
PHASE_ID = "T1.8.3"

from .phase_t183_orchestrator import PhaseT183Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseT183Orchestrator"]
