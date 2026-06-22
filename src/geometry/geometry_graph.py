"""Connected-component geometry graph for reinforcement detail sketches."""

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from ezdxf.document import Drawing
from loguru import logger

Point = Tuple[float, float]
Segment = Tuple[float, float, float, float, str, str]
Bbox = Tuple[float, float, float, float]

# Only these layers participate in flood-fill graph connectivity (Phase 3B.2).
GRAPH_LAYERS = frozenset(
    {
        "-STR-BEAM",
        "-STR-REINF",
    }
)

CONNECT_TOLERANCE_MM = 2.0
MAX_BRIDGE_LENGTH_MM = 6000.0
SEED_BBOX_DISTANCE_MM = 2500.0
MAX_LABEL_DISTANCE_MM = 2500.0
MAX_SEED_X_OFFSET_MM = 1200.0
MAX_DETAIL_SPAN_MM = 12000.0
X_COLUMN_PAD_LEFT_MM = 800.0
X_COLUMN_PAD_RIGHT_MM = 800.0

ANNOTATION_PAD_X_MM = 800.0
ANNOTATION_PAD_Y_MM = 1000.0


@dataclass(frozen=True)
class SketchComponent:
    """Connected reinforcement sketch geometry."""

    segments: Tuple[Segment, ...]
    bbox: Bbox
    seed_polyline_handle: str
    x_column: Bbox = (0.0, 0.0, 0.0, 0.0)


def expand_sketch_bbox(
    bbox: Bbox,
    pad_x: float = ANNOTATION_PAD_X_MM,
    pad_y: float = ANNOTATION_PAD_Y_MM,
) -> Bbox:
    """Expand isolated sketch bbox for annotation collection."""
    return (
        round(bbox[0] - pad_x, 6),
        round(bbox[1] - pad_y, 6),
        round(bbox[2] + pad_x, 6),
        round(bbox[3] + pad_y, 6),
    )


def _pt_key(x: float, y: float) -> Point:
    return (
        round(x / CONNECT_TOLERANCE_MM) * CONNECT_TOLERANCE_MM,
        round(y / CONNECT_TOLERANCE_MM) * CONNECT_TOLERANCE_MM,
    )


def _segment_length(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _distance_point_bbox(px: float, py: float, bbox: Bbox) -> float:
    xmin, ymin, xmax, ymax = bbox
    dx = max(xmin - px, 0, px - xmax)
    dy = max(ymin - py, 0, py - ymax)
    return math.hypot(dx, dy)


def _bbox_intersects(first: Bbox, second: Bbox) -> bool:
    return not (
        first[2] < second[0]
        or first[0] > second[2]
        or first[3] < second[1]
        or first[1] > second[3]
    )


def _segment_bbox(segment: Segment) -> Bbox:
    xs = (segment[0], segment[2])
    ys = (segment[1], segment[3])
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_from_segments(segments: Sequence[Segment]) -> Bbox:
    xmin = ymin = math.inf
    xmax = ymax = -math.inf
    for segment in segments:
        for x, y in ((segment[0], segment[1]), (segment[2], segment[3])):
            xmin = min(xmin, x)
            ymin = min(ymin, y)
            xmax = max(xmax, x)
            ymax = max(ymax, y)
    if xmin == math.inf:
        return (0.0, 0.0, 0.0, 0.0)
    return (round(xmin, 6), round(ymin, 6), round(xmax, 6), round(ymax, 6))


class GeometryGraphBuilder:
    """Build isolated reinforcement sketch components from beam/reinf geometry only."""

    def __init__(self, geometry_layers: frozenset[str] = GRAPH_LAYERS) -> None:
        self._geometry_layers = geometry_layers

    def _segment_in_x_column(self, segment: Segment, x_column: Bbox) -> bool:
        xmin, _, xmax, _ = x_column
        for x in (segment[0], segment[2]):
            if not xmin <= x <= xmax:
                return False
        return True

    def build_sketch(
        self,
        doc: Drawing,
        label_x: float,
        label_y: float,
    ) -> SketchComponent | None:
        segments, polyline_bboxes = self._extract_segments(doc)
        if not segments:
            logger.warning("No geometry segments found on target layers")
            return None

        segment_bboxes = [_segment_bbox(segment) for segment in segments]
        seed_polys = self._select_seed_polylines(polyline_bboxes, label_x, label_y)
        seed_poly = seed_polys[0] if seed_polys else None
        x_column = self._x_column_bbox(seed_polys, label_x)
        seed_indices = self._seed_indices(
            segments,
            segment_bboxes,
            seed_polys,
            label_x,
            label_y,
        )
        if not seed_indices:
            logger.warning(
                "No seed segments near label at ({}, {})",
                label_x,
                label_y,
            )
            return None

        component_indices = self._flood_fill(
            segments,
            seed_indices,
            label_x,
            label_y,
            x_column,
        )

        component_segments = tuple(segments[index] for index in component_indices)
        bbox = _bbox_from_segments(component_segments)
        seed_handle = seed_poly[4] if seed_poly else ""

        logger.debug(
            "Sketch at ({}, {}): {} segments, bbox={}",
            label_x,
            label_y,
            len(component_segments),
            bbox,
        )
        return SketchComponent(
            segments=component_segments,
            bbox=bbox,
            seed_polyline_handle=seed_handle,
            x_column=x_column,
        )

    def _extract_segments(self, doc: Drawing) -> Tuple[List[Segment], List[Tuple]]:
        msp = doc.modelspace()
        segments: List[Segment] = []
        polyline_bboxes: List[Tuple] = []

        for entity in msp.query("LINE"):
            if entity.dxf.layer not in self._geometry_layers:
                continue
            x1, y1 = float(entity.dxf.start.x), float(entity.dxf.start.y)
            x2, y2 = float(entity.dxf.end.x), float(entity.dxf.end.y)
            if _segment_length(x1, y1, x2, y2) > MAX_BRIDGE_LENGTH_MM:
                continue
            segments.append((x1, y1, x2, y2, str(entity.dxf.handle), entity.dxf.layer))

        for entity in msp.query("LWPOLYLINE"):
            if entity.dxf.layer not in self._geometry_layers:
                continue
            points = list(entity.get_points("xy"))
            if not points:
                continue
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            polyline_bboxes.append(
                (
                    min(xs),
                    min(ys),
                    max(xs),
                    max(ys),
                    str(entity.dxf.handle),
                )
            )
            for index in range(len(points) - 1):
                x1, y1 = points[index][0], points[index][1]
                x2, y2 = points[index + 1][0], points[index + 1][1]
                if _segment_length(x1, y1, x2, y2) > MAX_BRIDGE_LENGTH_MM:
                    continue
                segments.append((x1, y1, x2, y2, str(entity.dxf.handle), entity.dxf.layer))
            if len(points) > 2 and points[0] != points[-1]:
                x1, y1 = points[-1][0], points[-1][1]
                x2, y2 = points[0][0], points[0][1]
                if _segment_length(x1, y1, x2, y2) <= MAX_BRIDGE_LENGTH_MM:
                    segments.append((x1, y1, x2, y2, str(entity.dxf.handle), entity.dxf.layer))

        return segments, polyline_bboxes

    def _select_seed_polyline(
        self,
        polyline_bboxes: Sequence[Tuple],
        label_x: float,
        label_y: float,
    ) -> Tuple | None:
        seeds = self._select_seed_polylines(polyline_bboxes, label_x, label_y)
        return seeds[0] if seeds else None

    def _select_seed_polylines(
        self,
        polyline_bboxes: Sequence[Tuple],
        label_x: float,
        label_y: float,
    ) -> List[Tuple]:
        candidates: List[Tuple[float, Tuple]] = []

        for bbox in polyline_bboxes:
            xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
            width = xmax - xmin
            height = ymax - ymin
            if width > MAX_DETAIL_SPAN_MM or height > MAX_DETAIL_SPAN_MM:
                continue
            if width < 80.0 or height < 80.0:
                continue
            center_x = (xmin + xmax) / 2.0
            if abs(center_x - label_x) > MAX_SEED_X_OFFSET_MM:
                continue
            distance = _distance_point_bbox(label_x, label_y, (xmin, ymin, xmax, ymax))
            if distance <= SEED_BBOX_DISTANCE_MM:
                candidates.append((distance, bbox))

        if not candidates:
            return []

        return [bbox for _, bbox in sorted(candidates, key=lambda item: item[0])]

    def _x_column_bbox(self, seed_polys: Sequence[Tuple], label_x: float) -> Bbox:
        if seed_polys:
            xmin = min(poly[0] for poly in seed_polys) - X_COLUMN_PAD_LEFT_MM
            xmax = max(poly[2] for poly in seed_polys) + X_COLUMN_PAD_RIGHT_MM
        else:
            xmin = label_x - MAX_SEED_X_OFFSET_MM
            xmax = label_x + MAX_SEED_X_OFFSET_MM
        return (xmin, -math.inf, xmax, math.inf)

    def _seed_indices(
        self,
        segments: Sequence[Segment],
        segment_bboxes: Sequence[Bbox],
        seed_polys: Sequence[Tuple],
        label_x: float,
        label_y: float,
    ) -> List[int]:
        if seed_polys:
            indices: List[int] = []
            for seed_poly in seed_polys:
                seed_bbox = (
                    seed_poly[0] - 200.0,
                    seed_poly[1] - 200.0,
                    seed_poly[2] + 200.0,
                    seed_poly[3] + 200.0,
                )
                indices.extend(
                    [
                        index
                        for index, bbox in enumerate(segment_bboxes)
                        if _bbox_intersects(bbox, seed_bbox)
                    ]
                )
            return list(dict.fromkeys(indices))

        return [
            index
            for index, segment in enumerate(segments)
            if self._segment_near_label(segment, label_x, label_y)
            and abs(((segment[0] + segment[2]) / 2.0) - label_x) <= MAX_SEED_X_OFFSET_MM
        ]

    def _flood_fill(
        self,
        segments: Sequence[Segment],
        seed_indices: Iterable[int],
        label_x: float,
        label_y: float,
        x_column: Bbox,
    ) -> set[int]:
        node_segments: dict[Point, List[int]] = defaultdict(list)
        for index, segment in enumerate(segments):
            node_segments[_pt_key(segment[0], segment[1])].append(index)
            node_segments[_pt_key(segment[2], segment[3])].append(index)

        visited: set[int] = set()
        queue: deque[int] = deque(seed_indices)

        while queue:
            index = queue.popleft()
            if index in visited:
                continue
            segment = segments[index]
            if segment[5] not in self._geometry_layers:
                continue
            if not self._segment_near_label(segment, label_x, label_y):
                continue
            if not self._segment_in_x_column(segment, x_column):
                continue

            visited.add(index)
            segment_keys = (
                _pt_key(segment[0], segment[1]),
                _pt_key(segment[2], segment[3]),
            )
            for key in segment_keys:
                for neighbor in node_segments[key]:
                    if neighbor not in visited:
                        queue.append(neighbor)

        return visited

    def _segment_near_label(
        self, segment: Segment, label_x: float, label_y: float
    ) -> bool:
        return any(
            math.hypot(x - label_x, y - label_y) <= MAX_LABEL_DISTANCE_MM
            for x, y in ((segment[0], segment[1]), (segment[2], segment[3]))
        )
