"""Resolve support bearing faces along the beam axis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.framing.beam_geometry import LineSegment, Point2D
from src.framing.beam_length_model import SOURCE_GEOMETRY, SOURCE_SUPPORT_FACE


@dataclass
class ResolvedSupportFace:
    """Support face position measured along beam axis from start."""

    axis_position_mm: float
    point: Point2D
    source: str
    confidence: float
    derived_from: List[str]
    resolved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis_position_mm": round(self.axis_position_mm, 3),
            "point": self.point.as_dict(),
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "derived_from": list(self.derived_from),
            "resolved": self.resolved,
        }


class SupportFaceResolver:
    """Replace centroid-based supports with engineering support faces."""

    def __init__(self, config: dict[str, Any]) -> None:
        el = config.get("engineering_length", {})
        self._beam_half_width_fallback = float(el.get("beam_half_width_fallback_mm", 100.0))

    def resolve(
        self,
        beam: dict[str, Any],
        model: dict[str, Any],
        structural_context: dict[str, Any],
    ) -> Tuple[ResolvedSupportFace, ResolvedSupportFace]:
        geometry = beam.get("geometry", {})
        centerline = geometry.get("centerline") or {}
        start = centerline.get("start_point", {})
        end = centerline.get("end_point", {})
        origin = Point2D(float(start.get("x", 0)), float(start.get("y", 0)))
        end_pt = Point2D(float(end.get("x", 0)), float(end.get("y", 0)))
        axis_length = float(centerline.get("length_mm") or geometry.get("length_mm") or 0.0)
        unit = self._unit_vector(origin, end_pt)

        node_index = self._node_index(model.get("structural_nodes", []))
        columns = structural_context.get("columns", [])
        walls: List[LineSegment] = structural_context.get("walls", [])
        beam_index = self._beam_index(model.get("beams", []))

        left_support = beam.get("supports", {}).get("left", {})
        right_support = beam.get("supports", {}).get("right", {})

        left_face = self._resolve_end(
            support=left_support,
            end_side="left",
            origin=origin,
            unit=unit,
            axis_length=axis_length,
            endpoint=origin,
            node_index=node_index,
            columns=columns,
            walls=walls,
            beam_index=beam_index,
        )
        right_face = self._resolve_end(
            support=right_support,
            end_side="right",
            origin=origin,
            unit=unit,
            axis_length=axis_length,
            endpoint=end_pt,
            node_index=node_index,
            columns=columns,
            walls=walls,
            beam_index=beam_index,
        )
        left_face, right_face = self._reconcile_shared_wall(
            left_support, right_support, left_face, right_face,
            origin, unit, walls,
        )
        return left_face, right_face

    def _reconcile_shared_wall(
        self,
        left_support: dict[str, Any],
        right_support: dict[str, Any],
        left_face: ResolvedSupportFace,
        right_face: ResolvedSupportFace,
        origin: Point2D,
        unit: Tuple[float, float],
        walls: List[LineSegment],
    ) -> Tuple[ResolvedSupportFace, ResolvedSupportFace]:
        """When both ends reference the same wall, use the wall thickness along the axis."""
        if str(left_support.get("type", "")).upper() != "WALL":
            return left_face, right_face
        if str(right_support.get("type", "")).upper() != "WALL":
            return left_face, right_face
        left_id = left_support.get("id")
        right_id = right_support.get("id")
        if not left_id or left_id != right_id:
            return left_face, right_face

        wall_range = self._wall_axis_range(str(left_id), walls, origin, unit)
        if wall_range is None:
            return left_face, right_face
        t_min, t_max = wall_range
        if t_max <= t_min:
            return left_face, right_face

        derived = [str(left_id)]
        confidence = min(left_face.confidence, right_face.confidence)
        return (
            self._face_at(t_min, origin, unit, SOURCE_SUPPORT_FACE, confidence, derived),
            self._face_at(t_max, origin, unit, SOURCE_SUPPORT_FACE, confidence, derived),
        )

    def _wall_axis_range(
        self,
        support_id: str,
        walls: List[LineSegment],
        origin: Point2D,
        unit: Tuple[float, float],
    ) -> Optional[Tuple[float, float]]:
        if not support_id.startswith("WALL_"):
            return None
        try:
            index = int(support_id.split("_", 1)[1]) - 1
        except (IndexError, ValueError):
            return None
        if index < 0 or index >= len(walls):
            return None
        wall = walls[index]
        ts = [
            self._project(Point2D(wall.x1, wall.y1), origin, unit),
            self._project(Point2D(wall.x2, wall.y2), origin, unit),
        ]
        return min(ts), max(ts)

    def _resolve_end(
        self,
        support: dict[str, Any],
        end_side: str,
        origin: Point2D,
        unit: Tuple[float, float],
        axis_length: float,
        endpoint: Point2D,
        node_index: Dict[str, dict[str, Any]],
        columns: List[Any],
        walls: List[LineSegment],
        beam_index: Dict[str, dict[str, Any]],
    ) -> ResolvedSupportFace:
        support_type = str(support.get("type", "UNKNOWN")).upper()
        support_id = support.get("id")
        confidence = float(support.get("confidence", 0.0))
        derived = [str(support_id)] if support_id else []

        if support_type == "COLUMN":
            face_t = self._column_face(
                support_id, columns, node_index, origin, unit, end_side
            )
            if face_t is not None:
                return self._face_at(axis_position=face_t, origin=origin, unit=unit,
                    source=SOURCE_SUPPORT_FACE, confidence=min(confidence, 0.97),
                    derived_from=derived)

        if support_type == "WALL":
            face_t = self._wall_face(support_id, walls, origin, unit, end_side)
            if face_t is not None:
                return self._face_at(axis_position=face_t, origin=origin, unit=unit,
                    source=SOURCE_SUPPORT_FACE, confidence=min(confidence, 0.95),
                    derived_from=derived)

        if support_type == "BEAM" and support_id:
            face_t = self._beam_face(
                support_id, beam_index, origin, unit, axis_length, end_side
            )
            if face_t is not None:
                return self._face_at(axis_position=face_t, origin=origin, unit=unit,
                    source=SOURCE_SUPPORT_FACE, confidence=min(confidence, 0.93),
                    derived_from=derived)

        if support_type == "FREE_END":
            t = 0.0 if end_side == "left" else axis_length
            return self._face_at(
                axis_position=t,
                origin=origin,
                unit=unit,
                source=SOURCE_GEOMETRY,
                confidence=min(confidence, 0.85),
                derived_from=derived or ["FREE_END"],
                resolved=True,
            )

        endpoint_t = self._project(endpoint, origin, unit)
        return ResolvedSupportFace(
            axis_position_mm=endpoint_t,
            point=endpoint,
            source=SOURCE_GEOMETRY,
            confidence=0.0,
            derived_from=derived,
            resolved=False,
        )

    def _column_face(
        self,
        support_id: Optional[str],
        columns: List[Any],
        node_index: Dict[str, dict[str, Any]],
        origin: Point2D,
        unit: Tuple[float, float],
        end_side: str,
    ) -> Optional[float]:
        bbox = None
        if support_id:
            node = node_index.get(str(support_id))
            if node and node.get("bbox"):
                bbox = node["bbox"]
        if bbox is None and support_id:
            for col in columns:
                if col.support_id == support_id:
                    bbox = col.bbox
                    break
        if bbox is None:
            return None

        t_min, t_max = self._project_bbox(bbox, origin, unit)
        return t_max if end_side == "left" else t_min

    def _wall_face(
        self,
        support_id: Optional[str],
        walls: List[LineSegment],
        origin: Point2D,
        unit: Tuple[float, float],
        end_side: str,
    ) -> Optional[float]:
        if not support_id or not support_id.startswith("WALL_"):
            return None
        try:
            index = int(support_id.split("_", 1)[1]) - 1
        except (IndexError, ValueError):
            return None
        if index < 0 or index >= len(walls):
            return None
        wall = walls[index]
        ts = [
            self._project(Point2D(wall.x1, wall.y1), origin, unit),
            self._project(Point2D(wall.x2, wall.y2), origin, unit),
        ]
        return max(ts) if end_side == "left" else min(ts)

    def _beam_face(
        self,
        support_id: str,
        beam_index: Dict[str, dict[str, Any]],
        origin: Point2D,
        unit: Tuple[float, float],
        axis_length: float,
        end_side: str,
    ) -> Optional[float]:
        support_beam = beam_index.get(support_id)
        if not support_beam:
            return None
        geometry = support_beam.get("geometry", {})
        cl = geometry.get("centerline") or {}
        s = cl.get("start_point", {})
        e = cl.get("end_point", {})
        joint = Point2D(float(s.get("x", 0)), float(s.get("y", 0)))
        joint_t = self._project(joint, origin, unit)

        section = support_beam.get("beam_section", {})
        width = section.get("width", {}).get("value")
        half_width = float(width) / 2.0 if width else self._beam_half_width_fallback

        offset = half_width if end_side == "left" else -half_width
        return max(0.0, min(axis_length, joint_t + offset))

    def _face_at(
        self,
        axis_position: float,
        origin: Point2D,
        unit: Tuple[float, float],
        source: str,
        confidence: float,
        derived_from: List[str],
        resolved: bool = True,
    ) -> ResolvedSupportFace:
        point = Point2D(
            origin.x + unit[0] * axis_position,
            origin.y + unit[1] * axis_position,
        )
        return ResolvedSupportFace(
            axis_position_mm=axis_position,
            point=point,
            source=source,
            confidence=confidence,
            derived_from=derived_from,
            resolved=resolved,
        )

    @staticmethod
    def _unit_vector(start: Point2D, end: Point2D) -> Tuple[float, float]:
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.hypot(dx, dy)
        if length == 0:
            return (1.0, 0.0)
        return (dx / length, dy / length)

    @staticmethod
    def _project(point: Point2D, origin: Point2D, unit: Tuple[float, float]) -> float:
        return (point.x - origin.x) * unit[0] + (point.y - origin.y) * unit[1]

    def _project_bbox(
        self, bbox: dict[str, float], origin: Point2D, unit: Tuple[float, float]
    ) -> Tuple[float, float]:
        corners = [
            Point2D(bbox["min_x"], bbox["min_y"]),
            Point2D(bbox["max_x"], bbox["min_y"]),
            Point2D(bbox["max_x"], bbox["max_y"]),
            Point2D(bbox["min_x"], bbox["max_y"]),
        ]
        ts = [self._project(c, origin, unit) for c in corners]
        return min(ts), max(ts)

    @staticmethod
    def _node_index(nodes: List[dict[str, Any]]) -> Dict[str, dict[str, Any]]:
        return {str(n["id"]): n for n in nodes if n.get("id")}

    @staticmethod
    def _beam_index(beams: List[dict[str, Any]]) -> Dict[str, dict[str, Any]]:
        return {str(b["beam_id"]): b for b in beams}
