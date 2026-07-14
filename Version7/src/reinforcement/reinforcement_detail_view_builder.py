"""Build EngineeringDetailView geometry containers for reinforcement regions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.reinforcement.reinforcement_geometry_entity import (
    PREFIX_VIEW,
    format_geometry_id,
    geometry_entity,
)
from src.reinforcement.reinforcement_geometry_utils import bbox_center, point_in_bbox


class EngineeringDetailViewBuilder:
    """Create geometry-only detail views from classified regions."""

    def __init__(self, config: dict[str, Any]) -> None:
        g2 = config.get("reinforcement_geometry", {})
        self._detail_band_below_mm = float(g2.get("detail_band_below_mm", 4500.0))
        self._detail_band_above_mm = float(g2.get("detail_band_above_mm", 1500.0))

    def build(
        self,
        regions: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        views: List[dict[str, Any]] = []
        counter = 0

        for region in regions:
            region_id = region.get("geometry_id", "")
            view_specs = region.get("detection_debug", {}).get("view_seeds", [])
            if view_specs:
                for spec in view_specs:
                    counter += 1
                    view = self._build_view(
                        counter,
                        region,
                        region_id,
                        spec.get("beam_mark", ""),
                        spec.get("bbox", region.get("bbox", {})),
                        text_objects,
                        leaders,
                        blocks,
                        sketches,
                    )
                    views.append(view)
            else:
                counter += 1
                views.append(
                    self._build_view(
                        counter,
                        region,
                        region_id,
                        region.get("beam_marks", [""])[0],
                        region.get("bbox", {}),
                        text_objects,
                        leaders,
                        blocks,
                        sketches,
                    )
                )

        self._attach_view_ids_to_regions(regions, views)
        return views

    def _build_view(
        self,
        index: int,
        region: dict[str, Any],
        region_id: str,
        beam_mark: str,
        view_box: dict[str, float],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> dict[str, Any]:
        text_ids = [
            item["geometry_id"]
            for item in text_objects
            if self._item_in_box(item, view_box)
        ]
        leader_ids = [
            item["geometry_id"]
            for item in leaders
            if self._leader_in_box(item, view_box)
        ]
        block_ids = [
            item["geometry_id"]
            for item in blocks
            if self._item_in_box(item, view_box)
        ]
        sketch_ids = [
            item["geometry_id"]
            for item in sketches
            if item.get("region_id") == region_id and self._item_in_box(item, view_box)
        ]
        geometry_ids = list(sketch_ids)

        return geometry_entity(
            format_geometry_id(PREFIX_VIEW, index),
            view_id=format_geometry_id(PREFIX_VIEW, index),
            beam_mark=beam_mark,
            region_id=region_id,
            bbox=view_box,
            geometry_entities=geometry_ids,
            text_entities=text_ids,
            leader_entities=leader_ids,
            block_entities=block_ids,
        )

    def _attach_view_ids_to_regions(
        self,
        regions: List[dict[str, Any]],
        views: List[dict[str, Any]],
    ) -> None:
        by_region: Dict[str, List[str]] = {}
        for view in views:
            rid = view.get("region_id", "")
            by_region.setdefault(rid, []).append(view.get("view_id", view.get("geometry_id", "")))

        for region in regions:
            rid = region.get("geometry_id", "")
            view_ids = by_region.get(rid, [])
            region["views"] = view_ids
            region["view_count"] = len(view_ids)

    def _item_in_box(self, item: dict[str, Any], box: dict[str, float]) -> bool:
        bbox = item.get("bbox")
        if not bbox:
            return False
        cx, cy = bbox_center(bbox)
        return point_in_bbox(cx, cy, box)

    def _leader_in_box(self, leader: dict[str, Any], box: dict[str, float]) -> bool:
        start = leader.get("start", {})
        sx = start.get("x")
        sy = start.get("y")
        if sx is None or sy is None:
            return False
        return point_in_bbox(sx, sy, box)

    def view_bbox_for_seed(
        self,
        row_seeds: List[dict[str, Any]],
        seed_index: int,
        seed: dict[str, Any],
    ) -> dict[str, float]:
        xs = [float(s["x"]) for s in row_seeds]
        bounds: List[float] = []
        for idx in range(len(xs) - 1):
            bounds.append((xs[idx] + xs[idx + 1]) / 2.0)
        margin = 1500.0
        y = float(seed["y"])
        if seed_index == 0:
            x_min = xs[0] - margin
        else:
            x_min = bounds[seed_index - 1]
        if seed_index >= len(xs) - 1:
            x_max = xs[-1] + margin
        else:
            x_max = bounds[seed_index]
        return {
            "min_x": x_min,
            "max_x": x_max,
            "min_y": y - self._detail_band_below_mm,
            "max_y": y + self._detail_band_above_mm,
        }
