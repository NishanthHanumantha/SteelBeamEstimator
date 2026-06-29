"""Reusable engineering status model for framing intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

STATUS_KNOWN = "KNOWN"
STATUS_ESTIMATED = "ESTIMATED"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_DERIVED = "DERIVED"
STATUS_NOT_COMPUTED = "NOT_COMPUTED"

VALID_STATUSES = frozenset(
    {STATUS_KNOWN, STATUS_ESTIMATED, STATUS_UNKNOWN, STATUS_DERIVED, STATUS_NOT_COMPUTED}
)


@dataclass
class EngineeringStatus:
    """Standard status wrapper for engineering values."""

    value: Optional[float]
    status: str
    confidence: float
    source: str = ""
    unit: str = "mm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": round(self.value, 3) if self.value is not None else None,
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineeringStatus:
        status = str(data.get("status", STATUS_UNKNOWN))
        if status not in VALID_STATUSES:
            status = STATUS_UNKNOWN
        value = data.get("value")
        return cls(
            value=float(value) if value is not None else None,
            status=status,
            confidence=float(data.get("confidence", 0.0)),
            source=str(data.get("source", "")),
            unit=str(data.get("unit", "mm")),
        )


def infer_status_from_dict(data: dict[str, Any]) -> str:
    """Map legacy length/section dicts to EngineeringStatus."""
    if "status" in data and data["status"] in VALID_STATUSES:
        return str(data["status"])
    if data.get("value") is None:
        return STATUS_UNKNOWN
    source = str(data.get("source", "")).upper()
    if source in ("ENGINEERING_MODEL",):
        return STATUS_ESTIMATED
    if source in ("SUPPORT_FACE", "GEOMETRY", "LABEL", "CENTERLINE", "FRAMING_PLAN"):
        return STATUS_KNOWN
    return STATUS_DERIVED
