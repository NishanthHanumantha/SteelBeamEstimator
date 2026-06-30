"""Build geometric containment relationships for reinforcement entities."""

from __future__ import annotations

from typing import Any, Dict, List

from src.reinforcement.reinforcement_geometry_utils import bbox_center, point_in_bbox


class DrawingRelationshipBuilder:
    """Build geometric containment relationships only."""

    REL_CONTAINS = "CONTAINS"

    def build(
        self,
        regions: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        relationships: List[dict[str, Any]] = []

        for region in regions:
            region_id = region["geometry_id"]
            region_box = region.get("bbox", {})

            for sketch in sketches:
                if sketch.get("region_id") != region_id:
                    continue
                relationships.append(self._rel(region_id, sketch["geometry_id"], "REGION_CONTAINS_SKETCH"))

            for text in text_objects:
                if self._item_in_region(text, region_box):
                    relationships.append(self._rel(region_id, text["geometry_id"], "REGION_CONTAINS_TEXT"))

            for leader in leaders:
                if self._leader_in_region(leader, region_box):
                    relationships.append(self._rel(region_id, leader["geometry_id"], "REGION_CONTAINS_LEADER"))

            for block in blocks:
                if self._item_in_region(block, region_box):
                    relationships.append(self._rel(region_id, block["geometry_id"], "REGION_CONTAINS_BLOCK"))

        for sketch in sketches:
            sketch_box = sketch.get("bbox", {})
            for text in text_objects:
                if self._item_in_region(text, sketch_box):
                    relationships.append(
                        self._rel(sketch["geometry_id"], text["geometry_id"], "SKETCH_CONTAINS_TEXT")
                    )
            for leader in leaders:
                if self._leader_in_region(leader, sketch_box):
                    relationships.append(
                        self._rel(sketch["geometry_id"], leader["geometry_id"], "SKETCH_CONTAINS_LEADER")
                    )

        return relationships

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "GEOMETRIC",
        }

    def _item_in_region(self, item: dict[str, Any], region_box: dict[str, float]) -> bool:
        box = item.get("bbox")
        if not box:
            insertion = item.get("insertion")
            if insertion:
                return point_in_bbox(insertion["x"], insertion["y"], region_box)
            return False
        cx, cy = bbox_center(box)
        return point_in_bbox(cx, cy, region_box)

    def _leader_in_region(self, leader: dict[str, Any], region_box: dict[str, float]) -> bool:
        start = leader.get("start", {})
        end = leader.get("end", {})
        sx, sy = start.get("x"), start.get("y")
        ex, ey = end.get("x"), end.get("y")
        if sx is None or sy is None:
            return False
        if point_in_bbox(sx, sy, region_box):
            return True
        if ex is not None and ey is not None and point_in_bbox(ex, ey, region_box):
            return True
        return False
