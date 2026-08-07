"""
Phase QA.3.3 — Ownership Explainability & Decision Trace Engine
MODEL_VERSION: 10.0.3

Read-only diagnostic package. Does NOT modify ownership decisions.
"""
from .phase_qa33_orchestrator import PhaseQA33Orchestrator

MODEL_VERSION = "10.0.3"
PHASE_ID = "QA.3.3"

__all__ = ["PhaseQA33Orchestrator", "MODEL_VERSION", "PHASE_ID"]
