"""
Phase QA.4.1 — Dropped Entity Recovery Audit
MODEL_VERSION: 10.5.0

Diagnostic-only. Fourth Set controlled population. No recovery.
"""
from .phase_qa41_orchestrator import PhaseQA41Orchestrator

MODEL_VERSION = "10.5.0"
PHASE_ID = "QA.4.1"

__all__ = ["PhaseQA41Orchestrator", "MODEL_VERSION", "PHASE_ID"]
