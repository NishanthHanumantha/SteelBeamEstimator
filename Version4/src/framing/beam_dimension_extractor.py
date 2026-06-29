"""Extract beam width and depth from framing plan geometry and labels."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, List, Optional

from src.framing.beam_centerline_extractor import BeamCenterlineRecord
from src.framing.beam_geometry import LineSegment


@dataclass
class DimensionValue:
    value: Optional[float]
    unit: str
    confidence: float
    source: str
    status: str = "KNOWN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "source": self.source,
            "status": self.status,
        }


class BeamDimensionExtractor:
    """Width from framing geometry; depth from beam designation text."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._parallel_min = float(config.get("parallel_width_min_mm", 80.0))
        self._parallel_max = float(config.get("parallel_width_max_mm", 800.0))
        self._angle_tol = float(config.get("orthogonal_tolerance_deg", 5.0))

    def extract_depth(self, record: BeamCenterlineRecord) -> DimensionValue:
        label = record.label
        if label.depth_mm > 0:
            return DimensionValue(
                value=float(label.depth_mm),
                unit="mm",
                confidence=0.98,
                source="FRAMING_LABEL",
                status="KNOWN",
            )
        return DimensionValue(
            value=None,
            unit="mm",
            confidence=0.0,
            source="FRAMING_LABEL",
            status="UNKNOWN",
        )

    def extract_width(
        self,
        record: BeamCenterlineRecord,
        all_segments: List[LineSegment],
    ) -> DimensionValue:
        if record.segment is None:
            return DimensionValue(
                value=None,
                unit="mm",
                confidence=0.0,
                source="FRAMING_GEOMETRY",
                status="UNKNOWN",
            )

        width = self._width_from_parallel_segments(record.segment, all_segments)
        if width is not None:
            return DimensionValue(
                value=width,
                unit="mm",
                confidence=0.9,
                source="FRAMING_GEOMETRY",
                status="KNOWN",
            )

        return DimensionValue(
            value=None,
            unit="mm",
            confidence=0.0,
            source="FRAMING_GEOMETRY",
            status="UNKNOWN",
        )

    def _width_from_parallel_segments(
        self,
        target: LineSegment,
        segments: List[LineSegment],
    ) -> Optional[float]:
        best_distance: Optional[float] = None
        for candidate in segments:
            if candidate.handle == target.handle:
                continue
            if not self._segments_parallel(target, candidate):
                continue
            distance = self._parallel_distance(target, candidate)
            if distance is None:
                continue
            if not (self._parallel_min <= distance <= self._parallel_max):
                continue
            if not self._projections_overlap(target, candidate):
                continue
            if best_distance is None or abs(distance - 200.0) < abs(best_distance - 200.0):
                best_distance = distance
        return round(best_distance, 1) if best_distance is not None else None

    def _segments_parallel(self, a: LineSegment, b: LineSegment) -> bool:
        angle_diff = abs(a.angle_deg - b.angle_deg)
        angle_diff = min(angle_diff, 180.0 - angle_diff)
        return angle_diff <= self._angle_tol

    def _parallel_distance(self, a: LineSegment, b: LineSegment) -> Optional[float]:
        dx = a.x2 - a.x1
        dy = a.y2 - a.y1
        length = math.hypot(dx, dy)
        if length == 0:
            return None
        nx = -dy / length
        ny = dx / length
        distances = [
            abs(nx * (b.x1 - a.x1) + ny * (b.y1 - a.y1)),
            abs(nx * (b.x2 - a.x1) + ny * (b.y2 - a.y1)),
        ]
        return sum(distances) / len(distances)

    def _projections_overlap(self, a: LineSegment, b: LineSegment) -> bool:
        dx = a.x2 - a.x1
        dy = a.y2 - a.y1
        length = math.hypot(dx, dy)
        if length == 0:
            return False
        ux, uy = dx / length, dy / length

        def proj(x: float, y: float) -> float:
            return (x - a.x1) * ux + (y - a.y1) * uy

        a_min, a_max = 0.0, length
        b_points = (proj(b.x1, b.y1), proj(b.x2, b.y2))
        b_min, b_max = min(b_points), max(b_points)
        overlap = min(a_max, b_max) - max(a_min, b_min)
        return overlap >= min(length, b_max - b_min) * 0.35
