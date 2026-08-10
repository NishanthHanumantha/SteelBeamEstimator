"""
Phase P2.3.1 — Controlled Engineering Recompute / Steel Re-benchmark.
MODEL_VERSION: 10.5.6
"""
from .config import MODEL_VERSION, PHASE_ID
from .phase_p231_orchestrator import PhaseP231Orchestrator

__all__ = ["PhaseP231Orchestrator", "MODEL_VERSION", "PHASE_ID"]
