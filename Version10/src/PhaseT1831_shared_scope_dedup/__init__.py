"""
Phase T1.8.3.1 — Shared Engineering Scope Deduplication.
MODEL_VERSION: 9.5.4

Additive registry-stage fix. Does not change ownership merge semantics or rendering.
"""
MODEL_VERSION = "9.5.4"
PHASE_ID = "T1.8.3.1"

from .phase_t1831_orchestrator import PhaseT1831Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseT1831Orchestrator"]
