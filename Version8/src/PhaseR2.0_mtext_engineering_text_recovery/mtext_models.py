"""Data models for Phase R.2.0 MTEXT engineering text recovery."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MtextEntity:
    entity_id: str
    layer: str
    x: float
    y: float
    raw_text: str
    nearest_beam_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FormattingToken:
    token_type: str      # "FORMAT_SEMI" | "FORMAT_NOSEMI" | "FORMAT_PARA" | "FORMAT_BS"
    raw_token: str
    position: int


@dataclass
class EngineeringToken:
    token_type: str      # "QUANTITY" | "GRADE" | "DIAMETER" | "SPACING" | "ABBREVIATION" | "TEXT"
    value: str
    position: int


@dataclass
class MtextTokenization:
    entity_id: str
    raw_text: str
    formatting_tokens: List[FormattingToken] = field(default_factory=list)
    engineering_tokens: List[EngineeringToken] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "raw_text": self.raw_text,
            "formatting_tokens": [
                {"type": t.token_type, "raw": t.raw_token, "pos": t.position}
                for t in self.formatting_tokens
            ],
            "engineering_tokens": [
                {"type": t.token_type, "value": t.value, "pos": t.position}
                for t in self.engineering_tokens
            ],
            "formatting_count": len(self.formatting_tokens),
            "engineering_count": len(self.engineering_tokens),
        }


@dataclass
class RecoveryRecord:
    entity_id: str
    raw_text: str
    old_clean_text: str
    new_clean_text: str
    old_status: str         # LOST | FORMAT_ONLY | OK
    new_status: str         # RECOVERED | UNCHANGED | STILL_LOST
    engineering_preserved: bool
    formatting_tokens_removed: int
    characters_recovered: int
    nearest_beam_id: str = ""
    regex_would_match_old: bool = False
    regex_would_match_new: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationRecord:
    entity_id: str
    clean_text: str
    contains_quantity: bool
    contains_diameter: bool
    contains_spacing: bool
    contains_abbreviation: bool
    contains_modifier: bool
    is_valid_engineering: bool
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
