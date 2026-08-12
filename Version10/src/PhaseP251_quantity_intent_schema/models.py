"""Quantity Intent data model — raw / normalized / validated separation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .config import (
    ROLE_UNKNOWN,
    SEM_UNKNOWN,
    SOURCE_UNRESOLVED,
    STATUS_UNRESOLVED,
    VALIDATION_PASS,
)


@dataclass
class QuantityComponent:
    """One part of a composite expression (e.g. 4-Y20 within 4-Y20+2-Y16)."""

    quantity_expression: str
    quantity_value: Optional[int] = None
    diameter_expression: Optional[str] = None
    diameter_value_mm: Optional[float] = None
    parse_ok: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceLinks:
    beam_id: str
    annotation_id: Optional[str] = None
    leader_id: Optional[str] = None
    ownership_id: Optional[str] = None
    source_handle: Optional[str] = None
    evidence_id: Optional[str] = None
    chain_semantic_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def has_provenance(self) -> bool:
        return bool(self.beam_id and self.annotation_id)


@dataclass
class QuantityIntent:
    """
    Structured quantity intent for one accepted reinforcement annotation.

    RAW: raw_text, quantity_expression, diameter_expression, ...
    NORMALIZED: quantity_value, diameter_value_mm, ...
    INTERPRETED: semantic_type, reinforcement_role, quantity_status
    VALIDATED: validation_status, validation_reasons
    """

    intent_id: str
    beam_id: str
    annotation_id: str
    raw_text: str
    normalized_text: str
    semantic_type: str = SEM_UNKNOWN
    reinforcement_role: str = ROLE_UNKNOWN
    quantity_expression: Optional[str] = None
    quantity_value: Optional[int] = None
    quantity_status: str = STATUS_UNRESOLVED
    quantity_source: str = SOURCE_UNRESOLVED
    diameter_expression: Optional[str] = None
    diameter_value_mm: Optional[float] = None
    spacing_expression: Optional[str] = None
    spacing_value_mm: Optional[float] = None
    spacing_values_mm: List[float] = field(default_factory=list)
    leg_expression: Optional[str] = None
    leg_count: Optional[int] = None
    unit: str = "COUNT"
    components: List[QuantityComponent] = field(default_factory=list)
    evidence_links: Optional[EvidenceLinks] = None
    confidence: float = 0.0
    validation_status: str = VALIDATION_PASS
    validation_reasons: List[str] = field(default_factory=list)
    accepted: bool = True
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["components"] = [c.to_dict() if hasattr(c, "to_dict") else c for c in self.components]
        if self.evidence_links is not None:
            d["evidence_links"] = self.evidence_links.to_dict()
        return d

    def to_row(self) -> Dict[str, Any]:
        links = self.evidence_links.to_dict() if self.evidence_links else {}
        return {
            "intent_id": self.intent_id,
            "beam_id": self.beam_id,
            "annotation_id": self.annotation_id,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "semantic_type": self.semantic_type,
            "reinforcement_role": self.reinforcement_role,
            "quantity_expression": self.quantity_expression,
            "quantity_value": self.quantity_value,
            "quantity_status": self.quantity_status,
            "quantity_source": self.quantity_source,
            "diameter_expression": self.diameter_expression,
            "diameter_value_mm": self.diameter_value_mm,
            "spacing_expression": self.spacing_expression,
            "spacing_value_mm": self.spacing_value_mm,
            "spacing_values_mm": "|".join(str(int(x)) for x in self.spacing_values_mm)
            if self.spacing_values_mm
            else "",
            "leg_expression": self.leg_expression,
            "leg_count": self.leg_count,
            "unit": self.unit,
            "component_count": len(self.components),
            "components_json": str(
                [
                    {
                        "q": c.quantity_value,
                        "d": c.diameter_value_mm,
                        "expr": c.quantity_expression,
                    }
                    for c in self.components
                ]
            ),
            "confidence": self.confidence,
            "validation_status": self.validation_status,
            "validation_reasons": "|".join(self.validation_reasons),
            "accepted": self.accepted,
            "leader_id": links.get("leader_id"),
            "ownership_id": links.get("ownership_id"),
            "source_handle": links.get("source_handle"),
            "evidence_id": links.get("evidence_id"),
            "chain_semantic_type": links.get("chain_semantic_type"),
        }
