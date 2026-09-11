"""Canonical EngineeringBarModel — single reinforcement representation."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class EngineeringBarModel:
    """Canonical reinforcement bar consumed by all production modules."""
    beam_id: str
    bar_role: str
    diameter_mm: float
    quantity: int
    zone: str
    spacing_mm: Optional[float] = None
    development_length_mm: Optional[int] = None
    cover_mm: Optional[int] = None
    steel_grade: str = "Y"
    concrete_grade: str = "M30"
    hook_rule: Optional[int] = None
    lap_rule_mm: Optional[int] = None
    source_phase: str = "R.1"
    bar_label: str = ""
    engineering_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeamEngineeringModel:
    """All engineering bars for one beam."""
    beam_id: str
    beam_name: str
    bars: List[EngineeringBarModel]
    geometry: Dict[str, Any] = field(default_factory=dict)
    source_phase: str = "R.1.3"
    classification_complete: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "beam_name": self.beam_name,
            "geometry": self.geometry,
            "source_phase": self.source_phase,
            "classification_complete": self.classification_complete,
            "bar_count": len(self.bars),
            "bars": [b.to_dict() for b in self.bars],
        }
