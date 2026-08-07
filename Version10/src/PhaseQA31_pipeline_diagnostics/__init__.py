"""
Phase QA.3.1 — Ownership & Render Pipeline Diagnostics.
MODEL_VERSION: 10.0.1

Diagnostic only. No engineering / ownership / render changes.
"""
MODEL_VERSION = "10.0.1"
PHASE_ID = "QA.3.1"

from .phase_qa31_orchestrator import PhaseQA31Orchestrator  # noqa: E402

__all__ = ["MODEL_VERSION", "PHASE_ID", "PhaseQA31Orchestrator"]
