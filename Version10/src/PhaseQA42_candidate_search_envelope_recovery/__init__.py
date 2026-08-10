"""
Phase QA.4.2 — P1 Candidate / Search Envelope Recovery
MODEL_VERSION: 10.5.1

Append-only recovery. Existing ownership engine decides. No P2/P3.
"""
from .phase_qa42_orchestrator import PhaseQA42Orchestrator

MODEL_VERSION = "10.5.1"
PHASE_ID = "QA.4.2"

__all__ = ["PhaseQA42Orchestrator", "MODEL_VERSION", "PHASE_ID"]
