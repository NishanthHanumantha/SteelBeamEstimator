"""Phase K.2 — Engineering Decision Execution Engine."""

from execution_engine import ExecutionEngine
from decision_collector import ENGINE_VERSION, MODEL_VERSION, PHASE, OUTPUT_DIR_REL

__all__ = [
    "PHASE",
    "MODEL_VERSION",
    "ENGINE_VERSION",
    "OUTPUT_DIR_REL",
    "ExecutionEngine",
]
