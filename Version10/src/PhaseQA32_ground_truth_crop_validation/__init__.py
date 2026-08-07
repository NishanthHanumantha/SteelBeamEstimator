"""
Phase QA.3.2 — Ground Truth Crop Verification
MODEL_VERSION: 10.0.2

Read-only diagnostic package. No engineering logic changes.
"""
from .phase_qa32_orchestrator import PhaseQA32Orchestrator

MODEL_VERSION = "10.0.2"
PHASE_ID = "QA.3.2"

__all__ = ["PhaseQA32Orchestrator", "MODEL_VERSION", "PHASE_ID"]
