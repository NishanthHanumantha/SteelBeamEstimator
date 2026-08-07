"""
Phase QA.3.4 — Ownership Competition Validation Engine
MODEL_VERSION: 10.0.4

Read-only validation. Does NOT modify ownership decisions.
"""
from .phase_qa34_orchestrator import PhaseQA34Orchestrator

MODEL_VERSION = "10.0.4"
PHASE_ID = "QA.3.4"

__all__ = ["PhaseQA34Orchestrator", "MODEL_VERSION", "PHASE_ID"]
