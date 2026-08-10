"""
Phase P2.3 — Controlled Production Gate + Re-benchmark.
MODEL_VERSION: 10.5.5
"""
from .config import MODEL_VERSION, PHASE_ID, GateMode
from .phase_p23_orchestrator import PhaseP23Orchestrator

__all__ = ["PhaseP23Orchestrator", "MODEL_VERSION", "PHASE_ID", "GateMode"]
