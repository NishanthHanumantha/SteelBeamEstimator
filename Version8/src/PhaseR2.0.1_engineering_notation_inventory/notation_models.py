"""Data models for Phase R.2.0.1 Engineering Notation Semantic Inventory."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


CATEGORIES = (
    "REINFORCEMENT_ROLE",
    "GEOMETRY",
    "POSITION",
    "SPACING",
    "MODIFIER",
    "QUANTITY",
    "STRUCTURAL",
    "DRAWING",
    "TITLE",
    "GENERAL_NOTE",
    "DEVELOPMENT",
    "UNKNOWN",
)

SUPPORT_STATUSES = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "UNSUPPORTED",
    "UNKNOWN",
)


@dataclass
class RawTextEntity:
    entity_id: str
    entity_type: str
    layer: str
    x: float
    y: float
    raw_text: str
    recovered_text: str
    nearest_beam_id: str = ""
    drawing_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedNotation:
    entity_id: str
    raw_token: str
    source_text: str
    entity_type: str
    beam_id: str
    drawing_id: str
    x: float
    y: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedNotation:
    raw_token: str
    normalized: str
    entity_id: str
    beam_id: str
    drawing_id: str
    source_text: str
    entity_type: str
    x: float
    y: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NotationGroup:
    normalized_notation: str
    frequency: int
    beam_ids: List[str] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    drawing_ids: List[str] = field(default_factory=list)
    example_texts: List[str] = field(default_factory=list)
    locations: List[Dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VocabularyEntry:
    notation: str
    normalized_notation: str
    category: str
    frequency: int
    support_status: str
    support_reason: str
    example_text: str
    beam_ids: List[str]
    drawing_ids: List[str]
    entity_ids: List[str]
    first_seen: str
    recommendation: str
    is_engineering_symbol: bool = False
    impact: str = "LOW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PriorityItem:
    priority: int
    notation: str
    impact: str
    reason: str
    frequency: int
    category: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
