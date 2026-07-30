"""
models.py — Normalized engineering objects for Ground Truth comparison.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.9.1"


@dataclass
class BarRecord:
    beam_id: str
    bar_role: str
    diameter: Optional[int] = None
    quantity: float = 0.0
    shape: str = ""
    cut_length: Optional[float] = None
    steel_weight: float = 0.0
    remarks: str = ""
    source_description: str = ""
    source_row: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeamRecord:
    beam_id: str
    beam_length: Optional[float] = None
    beam_depth: Optional[float] = None
    beam_width: Optional[float] = None
    steel_kg: float = 0.0
    diameter_kg: Dict[int, float] = field(default_factory=dict)
    bars: List[BarRecord] = field(default_factory=list)
    source_sheet: str = ""
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "beam_length": self.beam_length,
            "beam_depth": self.beam_depth,
            "beam_width": self.beam_width,
            "steel_kg": self.steel_kg,
            "diameter_kg": {str(k): v for k, v in self.diameter_kg.items()},
            "bars": [b.to_dict() for b in self.bars],
            "source_sheet": self.source_sheet,
            "aliases": list(self.aliases),
            "bar_count": len(self.bars),
        }


@dataclass
class NormalizedWorkbook:
    source_path: str
    source_label: str  # "ESTIMATOR" | "MODEL"
    project_name: str = ""
    sheet_names: List[str] = field(default_factory=list)
    beams: List[BeamRecord] = field(default_factory=list)
    total_steel_kg: float = 0.0
    total_steel_mt: float = 0.0
    diameter_kg: Dict[int, float] = field(default_factory=dict)
    model_version: str = MODEL_VERSION

    def beam_map(self) -> Dict[str, BeamRecord]:
        return {b.beam_id: b for b in self.beams}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "source_path": self.source_path,
            "source_label": self.source_label,
            "project_name": self.project_name,
            "sheet_names": self.sheet_names,
            "beam_count": len(self.beams),
            "bar_count": sum(len(b.bars) for b in self.beams),
            "total_steel_kg": self.total_steel_kg,
            "total_steel_mt": self.total_steel_mt,
            "diameter_kg": {str(k): v for k, v in self.diameter_kg.items()},
            "beams": [b.to_dict() for b in self.beams],
        }
