"""
ReinforcementPiece — fabricated manufacturing member.
MODEL_VERSION: 8.5.0
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.5.0"

# Piece types
TOP_MAIN = "TOP_MAIN"
BOTTOM_MAIN = "BOTTOM_MAIN"
TOP_EXTRA_LEFT = "TOP_EXTRA_LEFT"
TOP_EXTRA_RIGHT = "TOP_EXTRA_RIGHT"
BOTTOM_EXTRA_LEFT = "BOTTOM_EXTRA_LEFT"
BOTTOM_EXTRA_RIGHT = "BOTTOM_EXTRA_RIGHT"
CONTINUOUS_BAR = "CONTINUOUS_BAR"
CURTAILED_BAR = "CURTAILED_BAR"
SUPPORT_BAR = "SUPPORT_BAR"
STIRRUP_ZONE_A = "STIRRUP_ZONE_A"
STIRRUP_ZONE_B = "STIRRUP_ZONE_B"
STIRRUP_ZONE_C = "STIRRUP_ZONE_C"
SPACER = "SPACER"
SIDE_FACE = "SIDE_FACE"
LAP_BAR = "LAP_BAR"
ANCHOR_BAR = "ANCHOR_BAR"
UNKNOWN_PIECE = "UNKNOWN_PIECE"

# Fabrication types
FAB_STRAIGHT = "Straight"
FAB_BENT = "Bent"
FAB_HOOKED = "Hooked"
FAB_STIRRUP = "Stirrup Closed Loop"
FAB_SPACER = "Spacer"
FAB_UNKNOWN = "Unknown"


@dataclass(frozen=True)
class ReinforcementPiece:
    """Immutable fabricated reinforcement member."""

    piece_id: str
    detail_id: str
    intent_id: str
    beam_id: str
    role: str
    layer: str
    diameter_mm: float
    quantity: int
    piece_type: str
    fabrication_type: str
    cut_length_mm: Optional[float]
    development_length_mm: Optional[int]
    lap_length_mm: Optional[int]
    hook_type: str
    anchor_type: str
    continuity: str
    curtailment: str
    support_region: str
    zone: str
    piece_start_mm: Optional[float]
    piece_end_mm: Optional[float]
    shape_code: str
    estimated_weight_kg: Optional[float]
    confidence: float
    evidence: tuple = field(default_factory=tuple)
    validation_flags: tuple = field(default_factory=tuple)
    source_phase: str = "R.1.3"
    bar_label: str = ""
    spacing_mm: Optional[float] = None
    spacing_pattern: str = ""
    detail_confidence: float = 0.0
    annotation_ids: tuple = field(default_factory=tuple)
    geometry_ids: tuple = field(default_factory=tuple)
    relationship_ids: tuple = field(default_factory=tuple)
    fact_ids: tuple = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # asdict already handles tuples
        return d
