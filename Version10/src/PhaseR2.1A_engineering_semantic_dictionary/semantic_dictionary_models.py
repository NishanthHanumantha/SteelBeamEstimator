"""Data models for Phase R.2.1A Engineering Semantic Dictionary."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


ENGINEERING_MEANINGS = (
    "SIDE_FACE_REINFORCEMENT",
    "ONE_EACH_FACE",
    "BOTH_FACE",
    "NEAR_FACE",
    "FAR_FACE",
    "TOP",
    "BOTTOM",
    "TOP_EXTRA",
    "BOTTOM_EXTRA",
    "TOP_MAIN",
    "BOTTOM_MAIN",
    "U_BAR",
    "STIRRUP",
    "SPACER",
    "CONTINUOUS",
    "TYPICAL",
    "DEVELOPMENT_LENGTH",
    "LAP",
    "HOOK",
    "ANCHORAGE",
    "CRANK",
    "T_AND_B",
    "FACE",
    "UNKNOWN",
)


@dataclass
class InventoryItem:
    notation: str
    normalized_notation: str
    category: str
    frequency: int
    support_status: str
    support_reason: str = ""
    example_text: str = ""
    beam_ids: List[str] = field(default_factory=list)
    drawing_ids: List[str] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    impact: str = "LOW"
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DictionaryEntry:
    notation: str
    normalized_notation: str
    category: str
    engineering_meaning: str
    engineering_role: Optional[str]
    position: Optional[str]
    quantity_multiplier: float
    support_status: str
    priority: str
    confidence: str
    description: str
    examples: List[str]
    future_phase: str
    source: str
    frequency: int = 0
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DictionaryVersion:
    model_version: str
    dictionary_version: str
    created_time: str
    generated_from: str
    inventory_hash: str
    entry_count: int
    supported_count: int
    unsupported_count: int
    unknown_count: int
    partially_supported_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticDictionary:
    version: DictionaryVersion
    entries: Dict[str, DictionaryEntry]
    vocabulary_map: Dict[str, str]  # alias -> engineering_meaning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version.to_dict(),
            "entry_count": len(self.entries),
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "vocabulary_map": self.vocabulary_map,
        }
