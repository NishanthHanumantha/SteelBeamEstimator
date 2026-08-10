"""
Phase P2.1 — Leader Tip / Chain Acceptance Analysis
MODEL_VERSION: 10.5.3

Diagnostic / counterfactual only. No T18 or production mutations.
"""
from .phase_p21_orchestrator import PhaseP21Orchestrator

MODEL_VERSION = "10.5.3"
PHASE_ID = "P2.1"

__all__ = ["PhaseP21Orchestrator", "MODEL_VERSION", "PHASE_ID"]
