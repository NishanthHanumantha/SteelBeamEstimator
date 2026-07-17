"""Typed models for engineering reasoning results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PHASE_NAME = "Phase AI.1 – Engineering Reasoning Engine"
MODEL_VERSION = "6.4.0"
PHASE = "Phase AI.1"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / PHASE_NAME


@dataclass
class EngineeringReasoningResult:
    reasoning_id: str
    task_type: str
    confidence: float
    summary: str
    observations: List[str]
    recommendations: List[str]
    assumptions: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    checksum: str
    generated_timestamp: str

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeamReasoningResult(EngineeringReasoningResult):
    beam_id: str = ""
    beam_name: str = ""


@dataclass
class AnnotationReasoningResult(EngineeringReasoningResult):
    annotation_id: str = ""
    region_id: str = ""


@dataclass
class ReinforcementReasoningResult(EngineeringReasoningResult):
    beam_id: str = ""
    annotation_text: str = ""


@dataclass
class QAReasoningResult(EngineeringReasoningResult):
    artifact_name: str = ""
    validation_status: str = ""


RESULT_MODEL_MAP = {
    "BEAM_REASONING": BeamReasoningResult,
    "ANNOTATION_CLASSIFICATION": AnnotationReasoningResult,
    "REINFORCEMENT_INTERPRETATION": ReinforcementReasoningResult,
    "QA_REASONING": QAReasoningResult,
    "GENERAL_ENGINEERING_REASONING": EngineeringReasoningResult,
}
