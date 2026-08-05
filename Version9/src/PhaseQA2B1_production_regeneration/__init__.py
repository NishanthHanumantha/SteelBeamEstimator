"""
Phase QA.2B.1 — Production Output Regeneration & Ground Truth Re-Benchmark.
MODEL_VERSION: 9.6.1
"""
MODEL_VERSION = "9.6.1"
PHASE_ID = "QA.2B.1"

from .phase_qa2b1_orchestrator import PhaseQA2B1Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseQA2B1Orchestrator"]
