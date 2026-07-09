"""Engineering length model — datatypes for beam span quantities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

SOURCE_FRAMING_PLAN = "FRAMING_PLAN"
SOURCE_CENTERLINE = "CENTERLINE"
SOURCE_SUPPORT_FACE = "SUPPORT_FACE"
SOURCE_GEOMETRY = "GEOMETRY"
SOURCE_ENGINEERING_MODEL = "ENGINEERING_MODEL"

STATUS_KNOWN = "KNOWN"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_ESTIMATED = "ESTIMATED"

GOVERNING_CLEAR_SPAN = "CLEAR_SPAN"
GOVERNING_EFFECTIVE_SPAN = "EFFECTIVE_SPAN"
GOVERNING_CENTERLINE = "CENTERLINE"


@dataclass
class EngineeringLength:
    """Single engineering length with full provenance."""

    value: Optional[float]
    unit: str
    source: str
    confidence: float
    derived_from: List[str] = field(default_factory=list)
    status: str = STATUS_KNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": round(self.value, 3) if self.value is not None else None,
            "unit": self.unit,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "derived_from": list(self.derived_from),
            "status": self.status,
        }

    @classmethod
    def unknown(cls, source: str = SOURCE_GEOMETRY) -> EngineeringLength:
        return cls(
            value=None,
            unit="mm",
            source=source,
            confidence=0.0,
            derived_from=[],
            status=STATUS_UNKNOWN,
        )


@dataclass
class GoverningSpan:
    value: Optional[float]
    unit: str
    selected_from: str
    confidence: float
    derived_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": round(self.value, 3) if self.value is not None else None,
            "unit": self.unit,
            "selected_from": self.selected_from,
            "confidence": round(self.confidence, 4),
            "derived_from": list(self.derived_from),
        }


@dataclass
class BeamLengthModel:
    """Complete engineering length model for one beam."""

    centerline_length: EngineeringLength
    support_face_length: EngineeringLength
    bearing_length_left: EngineeringLength
    bearing_length_right: EngineeringLength
    clear_span: EngineeringLength
    effective_span: EngineeringLength
    design_span: EngineeringLength
    governing_span: GoverningSpan
    source: str = SOURCE_FRAMING_PLAN
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "centerline_length": self.centerline_length.to_dict(),
            "support_face_length": self.support_face_length.to_dict(),
            "bearing_length_left": self.bearing_length_left.to_dict(),
            "bearing_length_right": self.bearing_length_right.to_dict(),
            "clear_span": self.clear_span.to_dict(),
            "effective_span": self.effective_span.to_dict(),
            "design_span": self.design_span.to_dict(),
            "governing_span": self.governing_span.to_dict(),
            "source": self.source,
            "confidence": round(self.confidence, 4),
        }
