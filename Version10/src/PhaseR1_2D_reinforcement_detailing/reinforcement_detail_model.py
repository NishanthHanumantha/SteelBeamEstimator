"""
ReinforcementDetail — deterministic detailing object between Intent and Bar.
MODEL_VERSION: 8.4.0
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.4.0"


@dataclass
class StirrupSegment:
    zone_name: str  # Zone_A / Zone_B / Zone_C / LEFT / MID / RIGHT
    start_mm: float
    end_mm: float
    spacing_mm: float
    quantity: int
    length_mm: float
    weight_kg: Optional[float] = None
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReinforcementDetail:
    detail_id: str
    beam_id: str
    intent_id: str
    role: str
    diameter_mm: float
    quantity: int
    layer: str = ""
    bar_label: str = ""
    zone: str = ""
    extent: str = "UNKNOWN"
    continuity: str = "UNKNOWN"
    support_type: str = "UNKNOWN"
    development_length_mm: Optional[int] = None
    lap_length_mm: Optional[int] = None
    hook_type: str = "UNKNOWN"
    anchor_type: str = "UNKNOWN"
    left_support_zone: bool = False
    mid_zone: bool = False
    right_support_zone: bool = False
    start_offset_mm: Optional[float] = None
    end_offset_mm: Optional[float] = None
    spacing_mm: Optional[float] = None
    spacing_pattern: str = ""
    stirrup_zone_count: int = 0
    stirrup_segments: List[Dict[str, Any]] = field(default_factory=list)
    curtailment_type: str = "UNKNOWN"
    side_face: bool = False
    engineering_notes: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    validation_flags: List[str] = field(default_factory=list)
    source_phase: str = "R.1.2D"
    # Extra traceability / rule provenance
    development_rule: str = ""
    development_source: str = ""
    support_region: str = "UNKNOWN"
    intent_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
