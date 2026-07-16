"""Forensic trace data models."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class AnnotationInventoryItem:
    annotation_id: str
    beam_id: str
    raw_text: str
    normalized_text: str
    entity_type: str = "TEXT"
    x: float = 0.0
    y: float = 0.0
    layer: str = ""
    regex_pattern: str = ""
    semantic_role: str = ""
    diameter_mm: float = 0.0
    quantity: int = 0
    spacing_mm: Optional[float] = None
    zone: str = ""
    classification: str = ""
    is_reinforcement: bool = False
    source: str = "R.1_DISCOVERED"
    nearest_beam_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnnotationTraceRecord:
    annotation_id: str
    beam_id: str
    normalized_text: str
    diameter_mm: float
    role: str
    group_id: str = ""
    group_merged: bool = False
    group_expanded: bool = False
    engineering_bar_ids: List[str] = field(default_factory=list)
    steel_consumed: bool = False
    bbs_consumed: bool = False
    diameter_bucket: str = ""
    beam_total: bool = False
    excel_reached: bool = False
    first_loss_stage: str = ""
    root_cause: str = ""
    status: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
