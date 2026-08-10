"""
Phase QA.4.3 — P2 Leader Recovery
MODEL_VERSION: 10.5.2

Append-only. T18 remains authoritative. No P3.
"""
from .phase_qa43_orchestrator import PhaseQA43Orchestrator

MODEL_VERSION = "10.5.2"
PHASE_ID = "QA.4.3"

__all__ = ["PhaseQA43Orchestrator", "MODEL_VERSION", "PHASE_ID"]
