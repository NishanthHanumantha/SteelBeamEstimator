"""Phase K.1.1 — Engineering Intent Resolution Engine."""

from src.engineering_intent_resolution.resolution_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
)
from src.engineering_intent_resolution.resolution_engine import ResolutionEngine

__all__ = [
    "PHASE",
    "MODEL_VERSION",
    "ENGINE_VERSION",
    "ResolutionEngine",
]
