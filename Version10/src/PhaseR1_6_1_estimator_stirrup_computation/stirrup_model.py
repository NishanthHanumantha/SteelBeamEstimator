"""
Deterministic stirrup computation models.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.8.1"

# Official IS 1786 unit weights kg/m
IS_UNIT_WEIGHT_KG_PER_M: Dict[int, float] = {
    8: 0.395,
    10: 0.617,
    12: 0.888,
    16: 1.58,
    20: 2.47,
    25: 3.85,
    32: 6.31,
}


@dataclass(frozen=True)
class StirrupNotation:
    raw_label: str
    legs: int
    diameter_mm: float
    spacing_values_mm: Tuple[int, ...]
    spacing_pattern: str
    notation_type: str  # UNIFORM | VARIABLE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StirrupZone:
    zone_index: int
    zone_name: str
    start_mm: float
    end_mm: float
    length_mm: float
    spacing_mm: int
    quantity: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HookResult:
    hook_length_mm: float
    hook_type: str
    hook_angle_deg: int
    multiplier_xd: int
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StirrupComputation:
    beam_id: str
    label: str
    notation: StirrupNotation
    beam_length_mm: float
    beam_width_mm: float
    beam_depth_mm: float
    cover_mm: float
    zones: List[StirrupZone]
    total_quantity: int
    perimeter_mm: float
    hook: HookResult
    cut_length_mm: float
    total_length_m: float
    unit_weight_kg_per_m: float
    weight_kg: float
    source_intent_id: str = ""
    source_detail_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "label": self.label,
            "notation": self.notation.to_dict(),
            "beam_length_mm": self.beam_length_mm,
            "beam_width_mm": self.beam_width_mm,
            "beam_depth_mm": self.beam_depth_mm,
            "cover_mm": self.cover_mm,
            "zones": [z.to_dict() for z in self.zones],
            "zone_count": len(self.zones),
            "total_quantity": self.total_quantity,
            "perimeter_mm": self.perimeter_mm,
            "hook": self.hook.to_dict(),
            "cut_length_mm": self.cut_length_mm,
            "total_length_m": self.total_length_m,
            "unit_weight_kg_per_m": self.unit_weight_kg_per_m,
            "weight_kg": self.weight_kg,
            "source_intent_id": self.source_intent_id,
            "source_detail_id": self.source_detail_id,
            "model_version": MODEL_VERSION,
        }


@dataclass
class StirrupEngineeringBar:
    beam_id: str
    bar_role: str
    diameter_mm: float
    quantity: int
    cut_length_mm: float
    weight_kg: float
    zone: str
    fabrication_type: str
    hooks: Dict[str, Any]
    spacing_mm: Optional[float]
    spacing_pattern: str
    legs: int
    perimeter_mm: float
    source_phase: str = "R.1.6.1"
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
