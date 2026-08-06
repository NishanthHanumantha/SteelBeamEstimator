"""
spacer_models.py — Dataclasses for Phase M.2 Spacer Bar Rule Engine.
MODEL_VERSION: 9.1.0
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.1.0"
RULE_VERSION = "M.2"

FaceName = str  # "TOP" | "BOTTOM"
Extent = Tuple[float, float]  # (start_mm, end_mm) along beam axis


@dataclass
class LongitudinalGroup:
    """One longitudinal bar group on a single face (MAIN or EXTRA)."""

    role: str
    face: FaceName
    start_mm: Optional[float] = None
    end_mm: Optional[float] = None
    clear_length_mm: Optional[float] = None
    extent_confidence: str = "HIGH"  # HIGH | LOW | MISSING
    diameter_mm: Optional[float] = None
    quantity: int = 1

    def has_extent(self) -> bool:
        if self.start_mm is None or self.end_mm is None:
            return False
        return float(self.end_mm) > float(self.start_mm)

    def extent(self) -> Optional[Extent]:
        if not self.has_extent():
            return None
        return (float(self.start_mm), float(self.end_mm))


@dataclass
class SpacerZone:
    face: FaceName
    start_mm: float
    end_mm: float
    length_mm: float
    quantity: int
    extent_fallback: bool = False


@dataclass
class SpacerRow:
    """Emitted SPACER_BAR row (pure data; no I/O)."""

    beam_id: str
    face: FaceName
    diameter_mm: int
    quantity: int
    spacing_mm: int
    cut_length_mm: float
    zone_start_mm: float
    zone_end_mm: float
    zone_length_mm: float
    cover_mm: float
    beam_width_mm: float
    source: str = "SpacerRuleEngine"
    rule_version: str = RULE_VERSION
    extent_fallback: bool = False
    cover_fallback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_engineering_metadata(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "rule_version": self.rule_version,
            "face": self.face,
            "zone_start_mm": self.zone_start_mm,
            "zone_end_mm": self.zone_end_mm,
            "zone_length_mm": self.zone_length_mm,
            "cut_length_mm": self.cut_length_mm,
            "extent_fallback": self.extent_fallback,
            "cover_fallback": self.cover_fallback,
            "piece_type": "SPACER_BAR",
            "extent": "ZONE",
        }


@dataclass
class BeamSpacerInput:
    """Per-beam inputs for the pure spacer engine."""

    beam_id: str
    beam_width_mm: Optional[float]
    cover_mm: Optional[float]
    groups: List[LongitudinalGroup] = field(default_factory=list)
    already_has_spacer: bool = False


@dataclass
class BeamSpacerResult:
    beam_id: str
    rows: List[SpacerRow] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
