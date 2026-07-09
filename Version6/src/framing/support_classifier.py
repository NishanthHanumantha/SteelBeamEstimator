"""Engineering support type classification for beam endpoints."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from src.framing.beam_geometry import LineSegment, Point2D, point_to_segment_distance
from src.framing.beam_support_detector import BeamSupportRecord, SupportZone

SUPPORT_COLUMN = "COLUMN"
SUPPORT_WALL = "WALL"
SUPPORT_BEAM = "BEAM"
SUPPORT_SLAB_EDGE = "SLAB_EDGE"
SUPPORT_UNKNOWN = "UNKNOWN"
SUPPORT_FREE_END = "FREE_END"

SOURCE_GEOMETRY = "GEOMETRY"

VALID_SUPPORT_TYPES = frozenset(
    {
        SUPPORT_COLUMN,
        SUPPORT_WALL,
        SUPPORT_BEAM,
        SUPPORT_SLAB_EDGE,
        SUPPORT_UNKNOWN,
        SUPPORT_FREE_END,
    }
)


@dataclass(frozen=True)
class ClassifiedSupport:
    type: str
    id: Optional[str]
    distance_mm: float
    source: str
    confidence: float
    point: Point2D

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "id": self.id,
            "distance_mm": round(self.distance_mm, 3),
            "source": self.source,
            "confidence": round(self.confidence, 4),
        }


class SupportClassifier:
    """Classify beam endpoint supports from framing plan structural geometry."""

    def __init__(self, config: dict[str, Any]) -> None:
        sr = config.get("support_resolution", {})
        self._tolerance = float(
            sr.get("detection_tolerance_mm", config.get("support_detection_tolerance_mm", 350.0))
        )
        self._column_confidence = float(sr.get("column_confidence", 0.97))
        self._wall_confidence = float(sr.get("wall_confidence", 0.94))
        self._beam_confidence = float(sr.get("beam_confidence", 0.93))
        self._slab_confidence = float(sr.get("slab_edge_confidence", 0.91))
        self._free_end_confidence = float(sr.get("free_end_confidence", 0.85))
        self._unknown_confidence = float(sr.get("unknown_confidence", 0.0))
        self._slab_layers = set(self._layer_list(sr.get("slab_edge_layers", [])))

    def classify_endpoint(
        self,
        beam_id: str,
        point: Point2D,
        columns: List[SupportZone],
        walls: List[LineSegment],
        slab_edges: List[LineSegment],
        beam_endpoints: List[Tuple[str, str, Point2D]],
        f1_support: Optional[BeamSupportRecord] = None,
    ) -> ClassifiedSupport:
        column_hit = self._nearest_column(point, columns)
        if column_hit is not None:
            zone, distance = column_hit
            return ClassifiedSupport(
                type=SUPPORT_COLUMN,
                id=zone.support_id,
                distance_mm=distance,
                source=SOURCE_GEOMETRY,
                confidence=self._column_confidence,
                point=point,
            )

        wall_hit = self._nearest_wall(point, walls)
        if wall_hit is not None:
            wall_id, distance = wall_hit
            return ClassifiedSupport(
                type=SUPPORT_WALL,
                id=wall_id,
                distance_mm=distance,
                source=SOURCE_GEOMETRY,
                confidence=self._wall_confidence,
                point=point,
            )

        slab_hit = self._nearest_slab_edge(point, slab_edges)
        if slab_hit is not None:
            slab_id, distance = slab_hit
            return ClassifiedSupport(
                type=SUPPORT_SLAB_EDGE,
                id=slab_id,
                distance_mm=distance,
                source=SOURCE_GEOMETRY,
                confidence=self._slab_confidence,
                point=point,
            )

        beam_hit = self._nearest_beam_joint(beam_id, point, beam_endpoints)
        if beam_hit is not None:
            other_id, distance = beam_hit
            return ClassifiedSupport(
                type=SUPPORT_BEAM,
                id=other_id,
                distance_mm=distance,
                source=SOURCE_GEOMETRY,
                confidence=self._beam_confidence,
                point=point,
            )

        if f1_support is not None and f1_support.support_type == "free_end":
            return ClassifiedSupport(
                type=SUPPORT_FREE_END,
                id=None,
                distance_mm=f1_support.distance_mm,
                source=SOURCE_GEOMETRY,
                confidence=self._free_end_confidence,
                point=point,
            )

        if f1_support is not None and f1_support.support_type not in (
            "column",
            "wall",
            "beam",
            "free_end",
        ):
            return ClassifiedSupport(
                type=SUPPORT_UNKNOWN,
                id=f1_support.support_id,
                distance_mm=f1_support.distance_mm,
                source=SOURCE_GEOMETRY,
                confidence=self._unknown_confidence,
                point=point,
            )

        return ClassifiedSupport(
            type=SUPPORT_FREE_END,
            id=None,
            distance_mm=0.0,
            source=SOURCE_GEOMETRY,
            confidence=self._free_end_confidence,
            point=point,
        )

    def _nearest_column(
        self, point: Point2D, columns: List[SupportZone]
    ) -> Optional[Tuple[SupportZone, float]]:
        best: Optional[Tuple[SupportZone, float]] = None
        for zone in columns:
            distance = math.hypot(point.x - zone.centroid.x, point.y - zone.centroid.y)
            if distance > self._tolerance:
                continue
            if self._point_in_bbox(point, zone.bbox, pad=self._tolerance):
                if best is None or distance < best[1]:
                    best = (zone, distance)
        return best

    def _nearest_wall(
        self, point: Point2D, walls: List[LineSegment]
    ) -> Optional[Tuple[str, float]]:
        best_id: Optional[str] = None
        best_distance = self._tolerance
        for index, wall in enumerate(walls):
            distance = point_to_segment_distance(point.x, point.y, wall)
            if distance <= best_distance:
                best_distance = distance
                best_id = f"WALL_{index + 1}"
        if best_id is None:
            return None
        return best_id, best_distance

    def _nearest_slab_edge(
        self, point: Point2D, slab_edges: List[LineSegment]
    ) -> Optional[Tuple[str, float]]:
        if not slab_edges:
            return None
        best_id: Optional[str] = None
        best_distance = self._tolerance
        for index, edge in enumerate(slab_edges):
            distance = point_to_segment_distance(point.x, point.y, edge)
            if distance <= best_distance:
                best_distance = distance
                best_id = f"SLAB_EDGE_{index + 1}"
        if best_id is None:
            return None
        return best_id, best_distance

    def _nearest_beam_joint(
        self,
        beam_id: str,
        point: Point2D,
        beam_endpoints: List[Tuple[str, str, Point2D]],
    ) -> Optional[Tuple[str, float]]:
        best_id: Optional[str] = None
        best_distance = self._tolerance
        for other_id, _other_end, other_point in beam_endpoints:
            if other_id == beam_id:
                continue
            distance = math.hypot(point.x - other_point.x, point.y - other_point.y)
            if distance <= best_distance:
                best_distance = distance
                best_id = other_id
        return (best_id, best_distance) if best_id else None

    @staticmethod
    def _point_in_bbox(point: Point2D, bbox: dict[str, float], pad: float = 0.0) -> bool:
        return (
            bbox["min_x"] - pad <= point.x <= bbox["max_x"] + pad
            and bbox["min_y"] - pad <= point.y <= bbox["max_y"] + pad
        )

    @staticmethod
    def _layer_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            if "," in value:
                return [part.strip() for part in value.split(",") if part.strip()]
            return [value.strip()] if value.strip() else []
        return []
