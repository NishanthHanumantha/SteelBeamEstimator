"""
Phase T1.8 — Beam Ownership Envelope Resolver.
MODEL_VERSION: 9.5.0

Additive filter AFTER T1.7 Annotation Graph. Does not modify prior phases.
"""
MODEL_VERSION = "9.5.0"
PHASE_ID = "T1.8"

from .phase_t18_orchestrator import PhaseT18Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseT18Orchestrator"]
