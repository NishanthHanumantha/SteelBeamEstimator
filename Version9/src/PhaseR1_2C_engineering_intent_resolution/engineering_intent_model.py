"""
EngineeringIntent model — authoritative interpretation before EngineeringBar.
MODEL_VERSION: 8.3.2
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.3.2"

# Production roles consumed by EngineeringBar / L2
ROLE_TOP_MAIN = "TOP_MAIN"
ROLE_BOTTOM_MAIN = "BOTTOM_MAIN"
ROLE_TOP_EXTRA = "TOP_EXTRA"
ROLE_BOTTOM_EXTRA = "BOTTOM_EXTRA"
ROLE_SIDE_FACE = "SIDE_FACE_REINFORCEMENT"
ROLE_SPACER = "SPACER_BAR"
ROLE_STIRRUP = "STIRRUP"
ROLE_UNKNOWN = "UNKNOWN"

EXTENT_FULL_SPAN = "FULL_SPAN"
EXTENT_CONTINUOUS = "CONTINUOUS"
EXTENT_LEFT_SUPPORT = "LEFT_SUPPORT"
EXTENT_RIGHT_SUPPORT = "RIGHT_SUPPORT"
EXTENT_CENTRE_SPAN = "CENTRE_SPAN"
EXTENT_SUPPORT_ZONE = "SUPPORT_ZONE"
EXTENT_CURTAILED = "CURTAILED"
EXTENT_LOCAL = "LOCAL_REINFORCEMENT"
EXTENT_UNKNOWN = "UNKNOWN"

CONTINUITY_CONTINUOUS = "CONTINUOUS"
CONTINUITY_CURTAILED = "CURTAILED"
CONTINUITY_SUPPORT = "SUPPORT"
CONTINUITY_SINGLE = "SINGLE_BEAM"

SUPPORT_NONE = "NONE"
SUPPORT_LEFT = "LEFT"
SUPPORT_RIGHT = "RIGHT"
SUPPORT_BOTH = "BOTH"
SUPPORT_UNKNOWN = "UNKNOWN"


@dataclass
class EngineeringIntent:
    """One deterministic engineering interpretation unit."""

    intent_id: str
    beam_id: str
    role: str
    diameter_mm: float
    quantity: int
    extent: str
    continuity: str
    support_type: str
    layer: str
    bar_label: str = ""
    spacing_mm: Optional[float] = None
    zone: str = ""
    development_length_mm: Optional[int] = None
    engineering_confidence: float = 0.0
    role_confidence: float = 0.0
    diameter_confidence: float = 0.0
    extent_confidence: float = 0.0
    intent_confidence: float = 0.0
    intent_reason: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    annotation_ids: List[str] = field(default_factory=list)
    geometry_ids: List[str] = field(default_factory=list)
    relationship_ids: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    source_role_hypothesis: str = ""
    consistency_flags: List[str] = field(default_factory=list)
    source_phase: str = "R.1.2C"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
