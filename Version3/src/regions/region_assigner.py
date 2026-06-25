"""Assign entities to drawing regions."""

import math
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.regions.anchor_detector import DrawingAnchor
from src.regions.bounding_box import BoundingBox, distance_to_box
from src.regions.constants import GEOMETRY_ENTITY_TYPES, REGION_TYPES
from src.regions.content_classifier import ContentClassifier

Assignment = Tuple[str, float]


class RegionAssigner:
    """Assign every entity to a drawing region using content and spatial rules."""

    def __init__(self, classifier: Optional[ContentClassifier] = None) -> None:
        self._classifier = classifier or ContentClassifier()

    def assign(
        self,
        entities: List[dict[str, Any]],
        anchors: List[DrawingAnchor],
        region_boxes: Dict[str, BoundingBox],
    ) -> Tuple[Dict[str, str], Dict[str, float]]:
        assignments: Dict[str, str] = {}
        confidences: Dict[str, float] = {}

        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue

            handle = str(entity.get("handle", ""))
            if not handle:
                logger.warning("Entity at index {} has no handle — skipped", index)
                continue

            entity_type = str(entity.get("entity_type", ""))
            if entity_type not in GEOMETRY_ENTITY_TYPES:
                assignments[handle] = "unassigned"
                confidences[handle] = 0.0
                continue

            x = self._parse_coordinate(entity, "x", index)
            y = self._parse_coordinate(entity, "y", index)
            entity_copy = dict(entity)
            entity_copy["x"] = x
            entity_copy["y"] = y

            region, confidence = self._assign_entity(
                entity_copy, anchors, region_boxes
            )
            assignments[handle] = region
            confidences[handle] = confidence

        logger.info(
            "Assigned {} entities across {} region type(s)",
            len(assignments),
            len({value for value in assignments.values()}),
        )
        return assignments, confidences

    def _assign_entity(
        self,
        entity: dict[str, Any],
        anchors: List[DrawingAnchor],
        region_boxes: Dict[str, BoundingBox],
    ) -> Assignment:
        content = self._classifier.classify(entity)
        if content is not None:
            region, confidence = content
            if confidence >= 0.80:
                return region, confidence

        box_region, box_confidence = self._assign_by_boxes(
            float(entity["x"]),
            float(entity["y"]),
            region_boxes,
        )
        if box_region is not None:
            if content is not None and content[0] != box_region and content[1] > box_confidence:
                return content[0], content[1]
            return box_region, box_confidence

        anchor_region, anchor_confidence = self._assign_by_anchor(
            float(entity["x"]),
            float(entity["y"]),
            anchors,
        )
        if anchor_region is not None:
            if content is not None:
                return content[0], max(content[1], anchor_confidence * 0.8)
            return anchor_region, anchor_confidence

        if content is not None:
            return content[0], content[1]

        return "unassigned", 0.25

    def _assign_by_boxes(
        self,
        x: float,
        y: float,
        region_boxes: Dict[str, BoundingBox],
    ) -> Tuple[Optional[str], float]:
        containing: List[Tuple[str, float]] = []

        for region_type, box in region_boxes.items():
            if region_type == "unassigned" or not box.is_valid():
                continue
            if box.contains(x, y):
                distance = distance_to_box(x, y, box)
                confidence = max(0.55, 0.95 - (distance / 10000.0))
                containing.append((region_type, confidence))

        if not containing:
            return None, 0.0

        containing.sort(key=lambda item: item[1], reverse=True)
        return containing[0][0], containing[0][1]

    def _assign_by_anchor(
        self,
        x: float,
        y: float,
        anchors: List[DrawingAnchor],
    ) -> Tuple[Optional[str], float]:
        if not anchors:
            return None, 0.0

        nearest = min(
            anchors,
            key=lambda anchor: math.hypot(x - anchor["x"], y - anchor["y"]),
        )
        distance = math.hypot(x - nearest["x"], y - nearest["y"])
        confidence = max(0.35, nearest["confidence"] - (distance / 50000.0))
        return nearest["anchor_type"], round(confidence, 4)

    def _parse_coordinate(
        self, entity: dict[str, Any], field: str, index: int
    ) -> float:
        value = entity.get(field)
        if value is None:
            return 0.0
        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            logger.warning(
                "Entity at index {} has invalid '{}' — using 0.0",
                index,
                field,
            )
            return 0.0

    @staticmethod
    def boxes_from_regions(regions: List[dict]) -> Dict[str, BoundingBox]:
        boxes: Dict[str, BoundingBox] = {
            region: BoundingBox() for region in REGION_TYPES
        }
        for region in regions:
            region_type = region["region_type"]
            box = BoundingBox(
                xmin=region["xmin"],
                ymin=region["ymin"],
                xmax=region["xmax"],
                ymax=region["ymax"],
                entity_count=region.get("entity_count", 0),
            )
            boxes[region_type] = box
        return boxes
