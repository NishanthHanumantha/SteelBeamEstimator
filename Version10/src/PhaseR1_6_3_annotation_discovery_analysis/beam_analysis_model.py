"""
Beam analysis models for Phase R.1.6.3.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.8.3"
PHASE_ID = "R.1.6.3"

PIPELINE_STAGES: Tuple[str, ...] = (
    "Annotation Discovery",
    "Intent Resolution",
    "Reinforcement Detail",
    "Piece Generation",
    "EngineeringBars",
)


@dataclass
class BeamInventoryRecord:
    beam_id: str
    beam_length_mm: Optional[float]
    beam_width_mm: Optional[float]
    beam_depth_mm: Optional[float]
    orientation: str
    drawing_name: str
    drawing_path: str
    registry_status: str
    centroid_x: Optional[float] = None
    centroid_y: Optional[float] = None
    bbox: Optional[Dict[str, float]] = None
    section_refs: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["section_refs"] = list(self.section_refs)
        d["model_version"] = MODEL_VERSION
        return d


@dataclass
class StageEvidence:
    stage: str
    status: str  # Present | Missing | Unknown
    evidence_source: str
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StirrupDiscoveryStatus:
    stirrup_detected: str  # YES | NO
    detected_notation: Optional[str] = None
    detected_diameter_mm: Optional[float] = None
    spacing_mm: Optional[Any] = None
    leg_count: Optional[int] = None
    engineeringbar_count: int = 0
    annotation_stirrup_count: int = 0
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DrawingEvidence:
    beam_id: str
    nearby_annotation_texts: List[str]
    associated_reinforcement_labels: List[str]
    associated_dimensions: List[str]
    section_references: List[str]
    leader_references: List[str]
    nearest_annotation_distance: Optional[float]
    annotation_count: int
    text_entity_count: Optional[int]  # Unknown -> None
    mtext_count: Optional[int]
    block_reference_count: Optional[int]
    layer_names: List[str]
    rotation: Optional[float]
    coordinates: Dict[str, Optional[float]]
    bounding_box: Optional[Dict[str, float]]
    role_counts: Dict[str, int]
    leader_count_near_beam: int
    relationship_count: int
    unknown_annotation_texts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeamAnalysisRecord:
    inventory: BeamInventoryRecord
    stirrup_status: StirrupDiscoveryStatus
    pipeline_trace: List[StageEvidence]
    drawing_evidence: DrawingEvidence
    rule012_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": MODEL_VERSION,
            "beam_id": self.inventory.beam_id,
            "rule012_status": self.rule012_status,
            "inventory": self.inventory.to_dict(),
            "stirrup_status": self.stirrup_status.to_dict(),
            "pipeline_trace": [s.to_dict() for s in self.pipeline_trace],
            "drawing_evidence": self.drawing_evidence.to_dict(),
        }
