"""Data models for Phase R.1.5.2 regex validation audit."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RawTextEntity:
    entity_id: str
    entity_type: str
    layer: str
    x: float
    y: float
    raw_text: str
    nearest_beam_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MtextCleaningRecord:
    entity_id: str
    entity_type: str
    raw_text: str
    cleaned_text: str
    characters_removed: int
    loss_pct: float
    status: str
    formatting_removed: bool = False
    engineering_text_removed: bool = False
    entire_annotation_removed: bool = False
    nearest_beam_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PatternRecord:
    pattern: str
    frequency: int
    examples: List[str] = field(default_factory=list)
    category: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegexMatchResult:
    entity_id: str
    text: str
    matched: bool
    regex_name: str
    captured_groups: Dict[str, Any]
    parsed_quantity: Optional[int] = None
    parsed_diameter: Optional[float] = None
    parsed_spacing: Optional[str] = None
    parsed_modifier: Optional[str] = None
    failure_reason: str = ""
    classification: str = "UNKNOWN"
    root_cause: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EngineeringNotationRecord:
    entity_id: str
    raw_text: str
    cleaned_text: str
    engineering_meaning: str
    parser_status: str
    preserved: bool
    root_cause: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
