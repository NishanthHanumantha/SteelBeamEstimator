"""Detect curved beam geometry from reinforcement drawing entities."""

import math
from typing import Any, Dict, Optional, Tuple

from ezdxf.document import Drawing
from loguru import logger

from src.parser.dxf_reader import DxfReader

_BBOX_MARGIN_MM = 200.0


class BeamGeometryClassifier:
    """Classify whether a sketch region contains curved beam geometry."""

    def __init__(self, dxf_path: str) -> None:
        self._doc: Drawing = DxfReader(dxf_path).read()
        self._curved_cache: Dict[str, bool] = {}

    def is_curved_beam(self, sketch_id: str, bbox: dict[str, float]) -> bool:
        if sketch_id in self._curved_cache:
            return self._curved_cache[sketch_id]

        xmin = float(bbox["xmin"]) - _BBOX_MARGIN_MM
        ymin = float(bbox["ymin"]) - _BBOX_MARGIN_MM
        xmax = float(bbox["xmax"]) + _BBOX_MARGIN_MM
        ymax = float(bbox["ymax"]) + _BBOX_MARGIN_MM

        curved = False
        msp = self._doc.modelspace()

        for entity in msp:
            dxftype = entity.dxftype()
            if dxftype == "ARC":
                if self._point_in_box(entity.dxf.center.x, entity.dxf.center.y, xmin, ymin, xmax, ymax):
                    curved = True
                    break
            elif dxftype == "SPLINE":
                if self._entity_in_box(entity, xmin, ymin, xmax, ymax):
                    curved = True
                    break
            elif dxftype in ("LWPOLYLINE", "POLYLINE"):
                if self._polyline_curved(entity, xmin, ymin, xmax, ymax):
                    curved = True
                    break

        self._curved_cache[sketch_id] = curved
        return curved

    @staticmethod
    def _point_in_box(
        x: float, y: float, xmin: float, ymin: float, xmax: float, ymax: float
    ) -> bool:
        return xmin <= x <= xmax and ymin <= y <= ymax

    def _entity_in_box(
        self, entity: Any, xmin: float, ymin: float, xmax: float, ymax: float
    ) -> bool:
        try:
            for x, y, *_ in entity.control_points:
                if self._point_in_box(x, y, xmin, ymin, xmax, ymax):
                    return True
        except Exception:
            pass
        return False

    def _polyline_curved(
        self, entity: Any, xmin: float, ymin: float, xmax: float, ymax: float
    ) -> bool:
        try:
            if entity.dxftype() == "LWPOLYLINE":
                points = list(entity.get_points(format="xyb"))
                for x, y, bulge in points:
                    if not self._point_in_box(x, y, xmin, ymin, xmax, ymax):
                        continue
                    if abs(bulge) > 1e-6:
                        return True
                return False

            for vertex in entity.vertices:
                x = float(vertex.dxf.location.x)
                y = float(vertex.dxf.location.y)
                if not self._point_in_box(x, y, xmin, ymin, xmax, ymax):
                    continue
                bulge = float(vertex.dxf.bulge) if vertex.dxf.hasattr("bulge") else 0.0
                if abs(bulge) > 1e-6:
                    return True
        except Exception as exc:
            logger.debug("Polyline curved check skipped: {}", exc)
        return False

    def find_leader_target(
        self, ax: float, ay: float, max_length_mm: float = 8000.0
    ) -> Optional[Tuple[float, float]]:
        """Return far endpoint of nearest leader-like line from annotation point."""
        msp = self._doc.modelspace()
        best_dist = float("inf")
        best_point: Optional[Tuple[float, float]] = None

        for entity in msp:
            if entity.dxftype() != "LINE":
                continue
            x1, y1 = float(entity.dxf.start.x), float(entity.dxf.start.y)
            x2, y2 = float(entity.dxf.end.x), float(entity.dxf.end.y)
            for near_x, near_y, far_x, far_y in (
                (x1, y1, x2, y2),
                (x2, y2, x1, y1),
            ):
                dist = math.hypot(near_x - ax, near_y - ay)
                if dist > 500.0:
                    continue
                seg_len = math.hypot(far_x - near_x, far_y - near_y)
                if seg_len > max_length_mm:
                    continue
                if dist < best_dist:
                    best_dist = dist
                    best_point = (far_x, far_y)

        return best_point
