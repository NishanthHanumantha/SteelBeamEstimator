"""BeamSection engineering model — permanent cross-section representation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

SHAPE_RECTANGULAR = "RECTANGULAR"
SHAPE_UNKNOWN = "UNKNOWN"

CLASS_DEEP = "DEEP_SECTION"
CLASS_NORMAL = "NORMAL_SECTION"
CLASS_UNKNOWN = "UNKNOWN"

ORIENTATION_HORIZONTAL = "HORIZONTAL"
ORIENTATION_VERTICAL = "VERTICAL"
ORIENTATION_ANGLED = "ANGLED"
ORIENTATION_UNKNOWN = "UNKNOWN"

DEEP_SECTION_RATIO = 2.0


@dataclass
class MetricValue:
    value: Optional[float]
    unit: str

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "unit": self.unit}


@dataclass
class DimensionProperty:
    value: Optional[float]
    unit: str
    source: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class BeamSection:
    """Engineering cross-section identity for a beam."""

    designation: str
    shape: str
    classification: str
    width: DimensionProperty
    depth: DimensionProperty
    cross_section_area: MetricValue
    perimeter: MetricValue
    aspect_ratio: MetricValue
    orientation: str
    source: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "designation": self.designation,
            "shape": self.shape,
            "classification": self.classification,
            "width": self.width.to_dict(),
            "depth": self.depth.to_dict(),
            "cross_section_area": self.cross_section_area.to_dict(),
            "perimeter": self.perimeter.to_dict(),
            "aspect_ratio": self.aspect_ratio.to_dict(),
            "orientation": self.orientation,
            "source": self.source,
            "confidence": self.confidence,
        }

    @staticmethod
    def classify_section(depth: Optional[float], width: Optional[float]) -> str:
        if depth is None or width is None or width <= 0:
            return CLASS_UNKNOWN
        ratio = depth / width
        return CLASS_DEEP if ratio >= DEEP_SECTION_RATIO else CLASS_NORMAL

    @staticmethod
    def map_orientation(raw: Optional[str]) -> str:
        if not raw:
            return ORIENTATION_UNKNOWN
        mapping = {
            "horizontal": ORIENTATION_HORIZONTAL,
            "vertical": ORIENTATION_VERTICAL,
            "angled": ORIENTATION_ANGLED,
        }
        return mapping.get(str(raw).lower(), ORIENTATION_UNKNOWN)
