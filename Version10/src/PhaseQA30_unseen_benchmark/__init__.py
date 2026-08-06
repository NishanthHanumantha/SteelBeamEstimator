"""
Phase QA.3.0 — Unseen Drawing Benchmark (First Generalization Validation).
MODEL_VERSION: 10.0.0

Orchestration only. No engineering / benchmark-formula changes.
"""
MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"

from .phase_qa30_orchestrator import PhaseQA30Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseQA30Orchestrator"]
