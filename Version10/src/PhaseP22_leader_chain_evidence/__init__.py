"""
Phase P2.2 — Leader-Chain Evidence Enhancement.
MODEL_VERSION: 10.5.4
"""
from .config import MODEL_VERSION, PHASE_ID, ProductionGate
from .evaluator import LeaderChainEvidenceEvaluator, LeaderEvidence
from .phase_p22_orchestrator import PhaseP22Orchestrator

__all__ = [
    "PhaseP22Orchestrator",
    "LeaderChainEvidenceEvaluator",
    "LeaderEvidence",
    "ProductionGate",
    "MODEL_VERSION",
    "PHASE_ID",
]
