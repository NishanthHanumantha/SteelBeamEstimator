"""First-class engineering values with provenance metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EngineeringValue:
    """Traceable engineering value with source evidence."""

    value: Any
    unit: Optional[str] = None
    source: str = "UNKNOWN"
    table: Optional[str] = None
    sheet: Optional[str] = None
    confidence: float = 1.0
    notes: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
        }
        if self.unit is not None:
            payload["unit"] = self.unit
        if self.table is not None:
            payload["table"] = self.table
        if self.sheet is not None:
            payload["sheet"] = self.sheet
        if self.notes is not None:
            payload["notes"] = self.notes
        payload.update(self.extra)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EngineeringValue":
        known = {"value", "unit", "source", "table", "sheet", "confidence", "notes"}
        extra = {key: val for key, val in data.items() if key not in known}
        return cls(
            value=data.get("value"),
            unit=data.get("unit"),
            source=str(data.get("source", "UNKNOWN")),
            table=data.get("table"),
            sheet=data.get("sheet"),
            confidence=float(data.get("confidence", 1.0)),
            notes=data.get("notes"),
            extra=extra,
        )

    def to_number(self) -> Optional[float]:
        if self.value is None:
            return None
        if isinstance(self.value, (int, float)):
            return float(self.value)
        if isinstance(self.value, str):
            cleaned = self.value.strip().replace("²", "2").replace("³", "3")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def __int__(self) -> int:
        number = self.to_number()
        if number is None:
            raise ValueError(f"Cannot convert EngineeringValue to int: {self.value!r}")
        return int(number)

    def __float__(self) -> float:
        number = self.to_number()
        if number is None:
            raise ValueError(f"Cannot convert EngineeringValue to float: {self.value!r}")
        return number

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like access for backward compatibility."""
        if key == "value_mm" and self.unit == "mm":
            return self.value
        if key == "value":
            return self.value
        if key == "unit":
            return self.unit
        if key == "source":
            return self.source
        if key == "table":
            return self.table
        if key == "sheet":
            return self.sheet
        if key == "confidence":
            return self.confidence
        if key == "notes":
            return self.notes
        return self.extra.get(key, default)

    def __getitem__(self, key: str) -> Any:
        value = self.get(key)
        if value is None and key not in self.to_dict() and key not in self.extra:
            raise KeyError(key)
        return value


def is_engineering_value(data: Any) -> bool:
    return (
        isinstance(data, EngineeringValue)
        or (
            isinstance(data, dict)
            and "value" in data
            and "source" in data
            and "confidence" in data
        )
    )


def engineering_value_numeric(data: Any) -> Any:
    """Resolve a plain numeric or scalar from EngineeringValue, dict, or raw."""
    if data is None:
        return None
    if isinstance(data, EngineeringValue):
        return data.value if data.unit != "mm" else (data.to_number() or data.value)
    if isinstance(data, dict):
        if "value" in data:
            return data["value"]
        if "value_mm" in data:
            return data["value_mm"]
        if "grade" in data:
            return data["grade"]
    return data


def engineering_value_to_dict(data: Any) -> Any:
    if isinstance(data, EngineeringValue):
        return data.to_dict()
    return data


def coerce_engineering_value(data: Any) -> Optional[EngineeringValue]:
    if data is None:
        return None
    if isinstance(data, EngineeringValue):
        return data
    if is_engineering_value(data):
        return EngineeringValue.from_dict(data)
    return None
