"""Phase AI — AI-powered engineering capabilities."""

from __future__ import annotations

import sys
from pathlib import Path

PHASE_AI_1_DIR = Path(__file__).resolve().parent / "Phase AI.1 – Engineering Reasoning Engine"
_phase_path = str(PHASE_AI_1_DIR)
if _phase_path not in sys.path:
    sys.path.insert(0, _phase_path)

from engineering_reasoning_engine import EngineeringReasoningEngine  # noqa: E402
from reasoning_models import (  # noqa: E402
    AnnotationReasoningResult,
    BeamReasoningResult,
    EngineeringReasoningResult,
    QAReasoningResult,
    ReinforcementReasoningResult,
)
from reasoning_registry import MODEL_VERSION, PHASE  # noqa: E402

__all__ = [
    "PHASE",
    "MODEL_VERSION",
    "PHASE_AI_1_DIR",
    "AnnotationReasoningResult",
    "BeamReasoningResult",
    "EngineeringReasoningEngine",
    "EngineeringReasoningResult",
    "QAReasoningResult",
    "ReinforcementReasoningResult",
]
