"""
Phase T1.8.1 — Beam Ownership Render Validation.
MODEL_VERSION: 9.5.1

Strictly additive visual validation consumer of T1.8 BeamScopedAnnotations.
Does not modify ownership, graph, or existing renderers.
"""
MODEL_VERSION = "9.5.1"
PHASE_ID = "T1.8.1"

from .phase_t181_orchestrator import PhaseT181Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseT181Orchestrator"]
