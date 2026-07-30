"""
Phase QA.2A — Ground Truth Benchmark Comparison Engine
MODEL_VERSION: 8.9.1

Runs the production pipeline per Drawing Set, then compares
Model Estimation_Output.xlsx against Estimator Excel (ground truth).

Does NOT modify engineering logic or production runners.
"""

MODEL_VERSION = "8.9.1"
PHASE_ID = "QA.2A"
PHASE_TITLE = "Ground Truth Benchmark Comparison Engine"

__all__ = ["MODEL_VERSION", "PHASE_ID", "PHASE_TITLE"]
