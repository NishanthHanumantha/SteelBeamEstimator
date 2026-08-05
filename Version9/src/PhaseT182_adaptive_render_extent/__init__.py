"""
Phase T1.8.2 — Adaptive Beam Render Extent.
MODEL_VERSION: 9.5.2

Additive viewport layer over T1.8.1. Does not change ownership or graph.
"""
MODEL_VERSION = "9.5.2"
PHASE_ID = "T1.8.2"

from .phase_t182_orchestrator import PhaseT182Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseT182Orchestrator"]
