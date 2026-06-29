"""Detect beam supports from framing plan structural elements."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.framing.beam_centerline_extractor import BeamCenterlineRecord
from src.framing.beam_geometry import LineSegment, Point2D, point_to_segment_distance
from src.parser.dxf_flattener import flatten_entities
from src.parser.dxf_reader import DxfReader


@dataclass
class SupportZone:
    support_id: str
    support_type: str
    layer: str
    centroid: Point2D
    bbox: dict[str, float]
    handles: List[str] = field(default_factory=list)


@dataclass
class BeamSupportRecord:
    beam_id: str
    end: str
    point: Point2D
    support_type: str
    support_id: Optional[str]
    confidence: float
    distance_mm: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "end": self.end,
            "point": self.point.as_dict(),
            "support_type": self.support_type,
            "support_id": self.support_id,
            "confidence": self.confidence,
            "distance_mm": round(self.distance_mm, 3),
        }


class BeamSupportDetector:
    """Identify column, wall, beam, or free-end supports at beam endpoints."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._tolerance = float(config.get("support_detection_tolerance_mm", 350.0))
        self._column_layers = set(self._layer_list(config.get("column_layers", ["S-COLUMN", "S-COL HATCH"])))
        self._wall_layers = set(self._layer_list(config.get("wall_layers", ["Wall", "STR-RC WALL"])))

    def load_structural_context(self, dxf_path) -> dict[str, Any]:
        reader = DxfReader(dxf_path)
        doc = reader.read()
        layout = reader.get_modelspace(doc)
        flat = flatten_entities(layout) if layout is not None else []
        columns = self._extract_column_zones(flat)
        walls = self._extract_wall_segments(flat)
        logger.info(
            "Structural context: {} column zone(s), {} wall segment(s)",
            len(columns),
            len(walls),
        )
        return {"columns": columns, "walls": walls, "entities": flat}

    def detect_supports(
        self,
        records: List[BeamCenterlineRecord],
        structural_context: dict[str, Any],
        all_segments: List[LineSegment],
    ) -> List[BeamSupportRecord]:
        supports: List[BeamSupportRecord] = []
        columns: List[SupportZone] = structural_context.get("columns", [])
        walls: List[LineSegment] = structural_context.get("walls", [])
        beam_endpoints = self._beam_endpoints(records)

        for record in records:
            if record.segment is None:
                supports.extend(
                    self._free_end_supports(record.beam_id, record.label.x, record.label.y)
                )
                continue
            for end_name, point in (
                ("start", record.segment.start),
                ("end", record.segment.end),
            ):
                support = self._classify_endpoint(
                    record.beam_id,
                    end_name,
                    point,
                    columns,
                    walls,
                    beam_endpoints,
                    all_segments,
                )
                supports.append(support)
        return supports

    def _classify_endpoint(
        self,
        beam_id: str,
        end_name: str,
        point: Point2D,
        columns: List[SupportZone],
        walls: List[LineSegment],
        beam_endpoints: List[Tuple[str, str, Point2D]],
        all_segments: List[LineSegment],
    ) -> BeamSupportRecord:
        column_hit = self._nearest_column(point, columns)
        if column_hit is not None:
            zone, distance = column_hit
            return BeamSupportRecord(
                beam_id=beam_id,
                end=end_name,
                point=point,
                support_type="column",
                support_id=zone.support_id,
                confidence=0.95,
                distance_mm=distance,
            )

        wall_hit = self._nearest_wall(point, walls)
        if wall_hit is not None:
            wall_id, distance = wall_hit
            return BeamSupportRecord(
                beam_id=beam_id,
                end=end_name,
                point=point,
                support_type="wall",
                support_id=wall_id,
                confidence=0.9,
                distance_mm=distance,
            )

        beam_hit = self._nearest_beam_joint(
            beam_id, end_name, point, beam_endpoints, all_segments
        )
        if beam_hit is not None:
            other_id, distance = beam_hit
            return BeamSupportRecord(
                beam_id=beam_id,
                end=end_name,
                point=point,
                support_type="beam",
                support_id=other_id,
                confidence=0.88,
                distance_mm=distance,
            )

        return BeamSupportRecord(
            beam_id=beam_id,
            end=end_name,
            point=point,
            support_type="free_end",
            support_id=None,
            confidence=0.8,
            distance_mm=0.0,
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

    def _nearest_beam_joint(
        self,
        beam_id: str,
        end_name: str,
        point: Point2D,
        beam_endpoints: List[Tuple[str, str, Point2D]],
        all_segments: List[LineSegment],
    ) -> Optional[Tuple[str, float]]:
        best_id: Optional[str] = None
        best_distance = self._tolerance
        for other_id, other_end, other_point in beam_endpoints:
            if other_id == beam_id:
                continue
            distance = math.hypot(point.x - other_point.x, point.y - other_point.y)
            if distance <= best_distance:
                best_distance = distance
                best_id = other_id
        return (best_id, best_distance) if best_id else None

    def _beam_endpoints(
        self, records: List[BeamCenterlineRecord]
    ) -> List[Tuple[str, str, Point2D]]:
        endpoints: List[Tuple[str, str, Point2D]] = []
        for record in records:
            if record.segment is None:
                continue
            endpoints.append((record.beam_id, "start", record.segment.start))
            endpoints.append((record.beam_id, "end", record.segment.end))
        return endpoints

    def _free_end_supports(
        self, beam_id: str, x: float, y: float
    ) -> List[BeamSupportRecord]:
        point = Point2D(x, y)
        return [
            BeamSupportRecord(
                beam_id=beam_id,
                end="start",
                point=point,
                support_type="free_end",
                support_id=None,
                confidence=0.3,
                distance_mm=0.0,
            ),
            BeamSupportRecord(
                beam_id=beam_id,
                end="end",
                point=point,
                support_type="free_end",
                support_id=None,
                confidence=0.3,
                distance_mm=0.0,
            ),
        ]

    def _extract_column_zones(self, entities: List[DXFGraphic]) -> List[SupportZone]:
        zones: List[SupportZone] = []
        index = 0
        for entity in entities:
            layer = str(entity.dxf.layer)
            if layer not in self._column_layers:
                continue
            if entity.dxftype() != "LWPOLYLINE":
                continue
            points = [(float(x), float(y)) for x, y in entity.get_points(format="xy")]
            if len(points) < 3:
                continue
            index += 1
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            centroid = Point2D(sum(xs) / len(xs), sum(ys) / len(ys))
            zones.append(
                SupportZone(
                    support_id=f"COLUMN_{index}",
                    support_type="column",
                    layer=layer,
                    centroid=centroid,
                    bbox={
                        "min_x": min(xs),
                        "min_y": min(ys),
                        "max_x": max(xs),
                        "max_y": max(ys),
                    },
                    handles=[str(entity.dxf.handle)],
                )
            )
        return zones

    def _extract_wall_segments(self, entities: List[DXFGraphic]) -> List[LineSegment]:
        walls: List[LineSegment] = []
        for entity in entities:
            layer = str(entity.dxf.layer)
            if layer not in self._wall_layers:
                continue
            handle = str(entity.dxf.handle)
            if entity.dxftype() == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                walls.append(
                    LineSegment(
                        x1=float(start.x),
                        y1=float(start.y),
                        x2=float(end.x),
                        y2=float(end.y),
                        layer=layer,
                        handle=handle,
                        entity_ids=(handle,),
                    )
                )
            elif entity.dxftype() == "LWPOLYLINE":
                points = [(float(x), float(y)) for x, y in entity.get_points(format="xy")]
                for idx in range(len(points) - 1):
                    x1, y1 = points[idx]
                    x2, y2 = points[idx + 1]
                    walls.append(
                        LineSegment(
                            x1=x1,
                            y1=y1,
                            x2=x2,
                            y2=y2,
                            layer=layer,
                            handle=handle,
                            entity_ids=(handle,),
                        )
                    )
        return walls

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
            return [value.strip()]
        return []
