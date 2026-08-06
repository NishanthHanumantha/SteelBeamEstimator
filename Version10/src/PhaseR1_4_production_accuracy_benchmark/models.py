"""
Official / production benchmark models for Phase R.1.4.
MODEL_VERSION: 8.6.0

Benchmarking always uses these objects — never raw Excel cells.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.6.0"
DIAMETER_MM = (8, 10, 12, 16, 20, 25, 32)

INTERNAL_ROLES = (
    "TOP_MAIN",
    "TOP_EXTRA",
    "BOTTOM_MAIN",
    "BOTTOM_EXTRA",
    "STIRRUP",
    "STIRRUP_HOOK",
    "SPACER_BAR",
    "SIDE_FACE_REINFORCEMENT",
    "UNKNOWN",
)


@dataclass
class OfficialSteelSummary:
    diameter_summary: Dict[int, float] = field(default_factory=dict)  # MT
    total_mt: float = 0.0
    total_kg: float = 0.0
    project_name: str = ""
    floor: str = ""
    block: str = ""
    concrete_m3: float = 0.0
    shuttering_m2: float = 0.0
    source_sheet: str = ""
    source_header_row: int = 0
    source_data_row: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["diameter_summary"] = {str(k): v for k, v in self.diameter_summary.items()}
        return d


@dataclass
class OfficialReinforcementRow:
    beam_id: str
    description: str
    role: str = "UNKNOWN"
    diameter: Optional[float] = None
    spacing: Optional[float] = None
    number_of_bars: Optional[float] = None
    development_length: Optional[float] = None
    cut_length: Optional[float] = None
    total_length: Optional[float] = None
    steel: float = 0.0
    diameter_column: Optional[int] = None
    diameter_kg: Dict[int, float] = field(default_factory=dict)
    source_row: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["diameter_kg"] = {str(k): v for k, v in self.diameter_kg.items()}
        return d


@dataclass
class OfficialBeam:
    beam_id: str
    floor: str = ""
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    depth_m: Optional[float] = None
    concrete_m3: float = 0.0
    shuttering_m2: float = 0.0
    total_steel_kg: float = 0.0
    diameter_kg: Dict[int, float] = field(default_factory=dict)
    reinforcement_rows: List[OfficialReinforcementRow] = field(default_factory=list)
    source_start_row: int = 0
    source_end_row: int = 0
    source_sheet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "floor": self.floor,
            "length_m": self.length_m,
            "width_m": self.width_m,
            "depth_m": self.depth_m,
            "concrete_m3": self.concrete_m3,
            "shuttering_m2": self.shuttering_m2,
            "total_steel_kg": self.total_steel_kg,
            "diameter_kg": {str(k): v for k, v in self.diameter_kg.items()},
            "reinforcement_rows": [r.to_dict() for r in self.reinforcement_rows],
            "source_start_row": self.source_start_row,
            "source_end_row": self.source_end_row,
            "source_sheet": self.source_sheet,
            "row_count": len(self.reinforcement_rows),
        }


@dataclass
class OfficialProject:
    project_name: str = ""
    block: str = ""
    floor: str = ""
    workbook_path: str = ""
    sheet_names: List[str] = field(default_factory=list)


@dataclass
class OfficialWorkbookModel:
    project: OfficialProject
    steel_summary: OfficialSteelSummary
    beams: List[OfficialBeam] = field(default_factory=list)
    interpretation: Dict[str, Any] = field(default_factory=dict)
    model_version: str = MODEL_VERSION

    @property
    def reinforcement_rows(self) -> List[OfficialReinforcementRow]:
        rows: List[OfficialReinforcementRow] = []
        for b in self.beams:
            rows.extend(b.reinforcement_rows)
        return rows

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "project": asdict(self.project),
            "steel_summary": self.steel_summary.to_dict(),
            "beam_count": len(self.beams),
            "reinforcement_row_count": len(self.reinforcement_rows),
            "beams": [b.to_dict() for b in self.beams],
            "interpretation": self.interpretation,
        }


@dataclass
class ProductionBeamSnapshot:
    beam_id: str
    geometry: Dict[str, Any] = field(default_factory=dict)
    intents: List[Dict[str, Any]] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)
    pieces: List[Dict[str, Any]] = field(default_factory=list)
    engineering_bars: List[Dict[str, Any]] = field(default_factory=list)
    steel_kg: float = 0.0
    diameter_kg: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "geometry": self.geometry,
            "intent_count": len(self.intents),
            "detail_count": len(self.details),
            "piece_count": len(self.pieces),
            "engineering_bar_count": len(self.engineering_bars),
            "steel_kg": self.steel_kg,
            "diameter_kg": {str(k): v for k, v in self.diameter_kg.items()},
            "intents": self.intents,
            "details": self.details,
            "pieces": self.pieces,
            "engineering_bars": self.engineering_bars,
        }


@dataclass
class ProductionSnapshot:
    intents: List[Dict[str, Any]] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)
    pieces: List[Dict[str, Any]] = field(default_factory=list)
    engineering_bars: List[Dict[str, Any]] = field(default_factory=list)
    beams: List[ProductionBeamSnapshot] = field(default_factory=list)
    steel_summary: Dict[str, Any] = field(default_factory=dict)
    bbs: Dict[str, Any] = field(default_factory=dict)
    workbook: Dict[str, Any] = field(default_factory=dict)
    sources: Dict[str, Any] = field(default_factory=dict)
    model_version: str = MODEL_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "intent_count": len(self.intents),
            "detail_count": len(self.details),
            "piece_count": len(self.pieces),
            "engineering_bar_count": len(self.engineering_bars),
            "beam_count": len(self.beams),
            "steel_summary": self.steel_summary,
            "bbs": self.bbs,
            "workbook": self.workbook,
            "sources": self.sources,
            "beams": [b.to_dict() for b in self.beams],
        }


@dataclass
class DetectedTable:
    table_type: str
    sheet_name: str
    anchor_row: int
    anchor_col: int
    header_text: str
    score: float
    column_map: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
