"""Detect reinforcement sketch geometry clusters inside regions."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from ezdxf.entities import DXFEntity

from src.reinforcement.reinforcement_geometry_entity import (
    PREFIX_SKETCH,
    format_geometry_id,
    geometry_entity,
)
from src.reinforcement.reinforcement_geometry_utils import (
    bbox_aspect_ratio,
    bbox_center,
    entity_bbox,
    entity_center,
    layer_name,
    merge_bboxes,
    normalize_layers,
    point_in_bbox,
)

SKETCH_LONGITUDINAL = "LONGITUDINAL"
SKETCH_CROSS_SECTION = "CROSS_SECTION"
SKETCH_TYPICAL_DETAIL = "TYPICAL_DETAIL"
SKETCH_STIRRUP = "STIRRUP"

GEOMETRY_TYPES = frozenset(
    {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "SPLINE", "CIRCLE", "ELLIPSE"}
)


class ReinforcementSketchDetector:
    """Detect reinforcement sketches from geometry clusters within regions."""

    def __init__(self, config: dict[str, Any]) -> None:
        g2 = config.get("reinforcement_geometry", {})
        self._reinf_layers = set(normalize_layers(g2.get("reinforcement_layers", "-STR-REINF")))
        self._stirrup_layers = set(normalize_layers(g2.get("stirrup_layers", "-S-STIRUP")))
        self._beam_layers = set(normalize_layers(g2.get("beam_layers", "-STR-BEAM")))
        self._cluster_tolerance_mm = float(g2.get("sketch_cluster_tolerance_mm", 1200.0))
        self._min_geometry_count = int(g2.get("sketch_min_geometry_count", 2))

    def detect(
        self,
        entities: List[DXFEntity],
        regions: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        sketches: List[dict[str, Any]] = []
        counter = 0

        for region in regions:
            region_box = region.get("bbox", {})
            if not region_box:
                continue

            clusters = self._cluster_entities(entities, region_box)
            if not clusters:
                counter += 1
                sketches.append(
                    geometry_entity(
                        format_geometry_id(PREFIX_SKETCH, counter),
                        region_id=region["geometry_id"],
                        type=SKETCH_LONGITUDINAL,
                        bbox=region_box,
                        geometry_count=0,
                        layers=[],
                    )
                )
                continue

            for cluster in clusters:
                counter += 1
                box = merge_bboxes(cluster["boxes"]) or region_box
                sketch_type = self._classify_cluster(cluster, region)
                sketches.append(
                    geometry_entity(
                        format_geometry_id(PREFIX_SKETCH, counter),
                        region_id=region["geometry_id"],
                        type=sketch_type,
                        bbox=box,
                        geometry_count=cluster["count"],
                        layers=sorted(cluster["layers"]),
                    )
                )

        return sketches

    def _cluster_entities(
        self,
        entities: List[DXFEntity],
        region_box: dict[str, float],
    ) -> List[dict[str, Any]]:
        points: List[dict[str, Any]] = []
        for entity in entities:
            if entity.dxftype() not in GEOMETRY_TYPES:
                continue
            center = entity_center(entity)
            box = entity_bbox(entity)
            if not center or not box:
                continue
            if not point_in_bbox(center[0], center[1], region_box):
                continue
            points.append(
                {
                    "center": center,
                    "box": box,
                    "layer": layer_name(entity),
                }
            )

        clusters: List[dict[str, Any]] = []
        used: Set[int] = set()

        for idx, point in enumerate(points):
            if idx in used:
                continue
            cluster_points = [idx]
            used.add(idx)
            queue = [idx]
            while queue:
                current = queue.pop()
                cx, cy = points[current]["center"]
                for jdx, other in enumerate(points):
                    if jdx in used:
                        continue
                    ox, oy = other["center"]
                    if abs(cx - ox) <= self._cluster_tolerance_mm and abs(cy - oy) <= self._cluster_tolerance_mm:
                        used.add(jdx)
                        cluster_points.append(jdx)
                        queue.append(jdx)

            if len(cluster_points) < self._min_geometry_count:
                continue

            layers: Set[str] = set()
            boxes = []
            for jdx in cluster_points:
                layers.add(points[jdx]["layer"])
                boxes.append(points[jdx]["box"])

            clusters.append(
                {
                    "count": len(cluster_points),
                    "layers": layers,
                    "boxes": boxes,
                }
            )

        return clusters

    def _classify_cluster(
        self,
        cluster: dict[str, Any],
        region: dict[str, Any],
    ) -> str:
        layers = cluster["layers"]
        box = merge_bboxes(cluster["boxes"]) or region.get("bbox", {})
        aspect = bbox_aspect_ratio(box)

        if layers & self._stirrup_layers:
            return SKETCH_STIRRUP
        if layers & self._beam_layers and aspect >= 1.8:
            return SKETCH_LONGITUDINAL
        if layers & self._reinf_layers and aspect >= 1.5:
            return SKETCH_LONGITUDINAL

        header = region.get("header_bbox")
        if header:
            cx, cy = bbox_center(box)
            hx, hy = bbox_center(header)
            if abs(cx - hx) < 4000 and abs(cy - hy) < 4000 and aspect < 2.0:
                return SKETCH_CROSS_SECTION

        if aspect >= 2.0:
            return SKETCH_LONGITUDINAL
        return SKETCH_TYPICAL_DETAIL
