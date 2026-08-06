"""
Phase QA.2B.0 — End-to-End Benchmark Pipeline Integration.
MODEL_VERSION: 9.6.0

Connects latest production / Track1 visual outputs to the benchmark spine.
Does not change engineering rules, rendering algorithms, or accuracy math.
"""
MODEL_VERSION = "9.6.0"
PHASE_ID = "QA.2B.0"

from .phase_qa2b0_orchestrator import PhaseQA2B0Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseQA2B0Orchestrator"]
