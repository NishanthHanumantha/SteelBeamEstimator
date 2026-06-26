"""Locate longitudinal reinforcement geometry inside owner sketch regions."""

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Set, Tuple

from ezdxf.document import Drawing
from loguru import logger

from src.geometry.geometry_utils import (
    beam_axis_from_bbox,
    beam_span,
    expand_bbox,
    is_excluded_layer,
    is_reinforcement_layer,
    point_in_bbox,
    segment_intersects_bbox,
    segment_length,
    span_along_axis,
)
from src.parser.dxf_reader import DxfReader

_MAX_ENTITY_LENGTH_MM = 12000.0


@dataclass(frozen=True)
class RebarSegment:
    """Single drawable segment representing longitudinal reinforcement."""

    entity_id: str
    layer: str
    x1: float
    y1: float
    x2: float
    y2: float
    length: float
    span_axis: float
    span_perp: float
    mid_x: float
    mid_y: float
    is_axis_aligned: bool
    is_end_marker: bool
    source_type: str


class RebarLocator:
    """Extract candidate longitudinal reinforcement segments from reinforcement DXF."""

    def __init__(self, dxf_path: str) -> None:
        self._doc: Drawing = DxfReader(dxf_path).read()
        self._sketch_cache: Dict[str, List[RebarSegment]] = {}
        self._stirrup_handles: Set[str] = set()

    def find_longitudinal_segments(
        self,
        sketch_id: str,
        sketch_bbox: dict[str, float],
        config: dict[str, Any],
        reference_bbox: dict[str, float] | None = None,
    ) -> List[RebarSegment]:
        cache_key = f"{sketch_id}|{reference_bbox is not None}"
        if cache_key in self._sketch_cache:
            return self._sketch_cache[cache_key]

        margin = float(config.get("bbox_margin_mm", 80.0))
        bbox = expand_bbox(sketch_bbox, margin)
        ref_bbox = reference_bbox or sketch_bbox
        axis = beam_axis_from_bbox(ref_bbox)
        beam_length = beam_span(ref_bbox, axis)
        min_length = float(config.get("minimum_rebar_length", 120.0))
        min_span_ratio = float(config.get("minimum_span_ratio", 0.12))
        stirrup_leg_max = float(config.get("stirrup_leg_max_length", 900.0))
        end_marker_ratio = float(config.get("end_marker_max_axis_span_ratio", 0.15))

        stirrup_handles = self._identify_stirrup_polylines(bbox, beam_length, axis)
        self._stirrup_handles.update(stirrup_handles)

        segments: List[RebarSegment] = []
        msp = self._doc.modelspace()

        for entity in msp:
            dxftype = entity.dxftype()
            if dxftype not in ("LINE", "LWPOLYLINE", "POLYLINE"):
                continue
            layer = str(entity.dxf.layer)
            if is_excluded_layer(layer) or not is_reinforcement_layer(layer):
                continue
            handle = str(entity.dxf.handle)
            if handle in stirrup_handles:
                continue

            edges = self._entity_edges(entity)
            for x1, y1, x2, y2, source_type in edges:
                if not segment_intersects_bbox(x1, y1, x2, y2, bbox):
                    continue
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                length = segment_length(x1, y1, x2, y2)
                if length < min_length or length > _MAX_ENTITY_LENGTH_MM:
                    continue

                span_axis, span_perp = span_along_axis(x1, y1, x2, y2, axis)
                long_span = max(span_axis, span_perp)
                short_span = min(span_axis, span_perp)

                min_long_span = max(min_length, beam_length * min_span_ratio)
                is_axis_bar = long_span >= min_long_span and short_span <= stirrup_leg_max
                is_end_marker = (
                    long_span >= min_length
                    and long_span <= stirrup_leg_max
                    and short_span <= beam_length * end_marker_ratio
                )

                if not is_axis_bar and not is_end_marker:
                    continue

                is_axis_aligned = span_axis >= span_perp

                segments.append(
                    RebarSegment(
                        entity_id=handle,
                        layer=layer,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        length=length,
                        span_axis=span_axis,
                        span_perp=span_perp,
                        mid_x=mx,
                        mid_y=my,
                        is_axis_aligned=is_axis_bar,
                        is_end_marker=is_end_marker,
                        source_type=source_type,
                    )
                )

        logger.debug(
            "Sketch {} — {} longitudinal candidate segment(s) (axis={})",
            sketch_id,
            len(segments),
            axis,
        )
        self._sketch_cache[cache_key] = segments
        return segments

    def _identify_stirrup_polylines(
        self,
        bbox: dict[str, float],
        beam_length: float,
        axis: str,
    ) -> Set[str]:
        """Closed U-shaped polylines on reinforcement layers are stirrups, not bars."""
        handles: Set[str] = set()
        msp = self._doc.modelspace()
        for entity in msp.query("LWPOLYLINE"):
            layer = str(entity.dxf.layer)
            if not is_reinforcement_layer(layer):
                continue
            points = list(entity.get_points("xy"))
            if len(points) < 3 or len(points) > 6:
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            if not point_in_bbox(mx, my, bbox):
                continue
            span_x = max(xs) - min(xs)
            span_y = max(ys) - min(ys)
            if axis == "X":
                along, across = span_x, span_y
            else:
                along, across = span_y, span_x
            if along >= beam_length * 0.45 and across >= beam_length * 0.15:
                handles.add(str(entity.dxf.handle))
        return handles

    def _entity_edges(self, entity: Any) -> List[Tuple[float, float, float, float, str]]:
        dxftype = entity.dxftype()
        if dxftype == "LINE":
            return [
                (
                    float(entity.dxf.start.x),
                    float(entity.dxf.start.y),
                    float(entity.dxf.end.x),
                    float(entity.dxf.end.y),
                    "LINE",
                )
            ]

        if dxftype == "LWPOLYLINE":
            points = list(entity.get_points("xy"))
            source = "LWPOLYLINE"
        else:
            points = [
                (float(vertex.dxf.location.x), float(vertex.dxf.location.y))
                for vertex in entity.vertices
            ]
            source = "POLYLINE"

        edges: List[Tuple[float, float, float, float, str]] = []
        for index in range(len(points) - 1):
            x1, y1 = points[index][0], points[index][1]
            x2, y2 = points[index + 1][0], points[index + 1][1]
            edges.append((x1, y1, x2, y2, source))
        if len(points) > 2 and points[0] != points[-1]:
            x1, y1 = points[-1][0], points[-1][1]
            x2, y2 = points[0][0], points[0][1]
            edges.append((x1, y1, x2, y2, source))
        return edges

    def max_axis_span_at_elevation(
        self,
        segments: Sequence[RebarSegment],
        elevation: float,
        axis: str,
        band_mm: float,
    ) -> float:
        best = 0.0
        for segment in segments:
            if not segment.is_axis_aligned:
                continue
            if axis == "X":
                if abs(segment.mid_y - elevation) > band_mm:
                    continue
            else:
                if abs(segment.mid_x - elevation) > band_mm:
                    continue
            best = max(best, segment.span_axis)
        return best
