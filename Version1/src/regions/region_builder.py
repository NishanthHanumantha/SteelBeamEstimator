"""Build drawing region bounding boxes from anchors and nearby geometry."""

import math
from typing import Any, Dict, List, Optional

from loguru import logger

from src.regions.anchor_detector import DrawingAnchor
from src.regions.bounding_box import BoundingBox, empty_region_boxes, merge_boxes
from src.regions.constants import GEOMETRY_ENTITY_TYPES, REGION_TYPES
from src.regions.content_classifier import ContentClassifier

DEFAULT_SHEET_MARGIN = 8000.0
DEFAULT_REGION_PADDING = 1500.0
OUTLIER_COORD_THRESHOLD = 1_000_000.0


class RegionBuilder:
    """Construct region bounding boxes using anchors, content, and geometry."""

    def __init__(
        self,
        sheet_margin: float = DEFAULT_SHEET_MARGIN,
        region_padding: float = DEFAULT_REGION_PADDING,
        classifier: Optional[ContentClassifier] = None,
    ) -> None:
        self._sheet_margin = sheet_margin
        self._region_padding = region_padding
        self._classifier = classifier or ContentClassifier()

    def build(
        self,
        entities: List[dict[str, Any]],
        anchors: List[DrawingAnchor],
        assignments: Dict[str, str],
        assignment_confidence: Dict[str, float],
    ) -> List[dict]:
        sane_entities = self._filter_sane_entities(entities, anchors)
        region_boxes = empty_region_boxes()

        for entity in sane_entities:
            handle = str(entity.get("handle", ""))
            region = assignments.get(handle, "unassigned")
            if region not in region_boxes:
                continue
            region_boxes[region].include(float(entity["x"]), float(entity["y"]))

        anchor_boxes = self._anchor_seed_boxes(anchors)
        for region_type, box in anchor_boxes.items():
            if box.is_valid():
                region_boxes[region_type] = merge_boxes([region_boxes[region_type], box])

        for region_type in REGION_TYPES:
            if region_type == "unassigned":
                continue
            box = region_boxes[region_type]
            if box.is_valid():
                box.pad(self._region_padding)

        regions: List[dict] = []
        for region_type in REGION_TYPES:
            if region_type == "unassigned":
                continue
            box = region_boxes[region_type]
            if not box.is_valid():
                logger.warning("No geometry found for region '{}'", region_type)
                continue

            confidence = self._region_confidence(
                region_type, anchors, assignment_confidence, assignments
            )
            regions.append(box.as_dict(region_type, confidence))

        logger.info("Built {} drawing region bounding box(es)", len(regions))
        return regions

    def _filter_sane_entities(
        self,
        entities: List[dict[str, Any]],
        anchors: List[DrawingAnchor],
    ) -> List[dict[str, Any]]:
        if not anchors:
            return [
                entity
                for entity in entities
                if self._is_sane_coordinate(entity)
            ]

        anchor_x = [anchor["x"] for anchor in anchors]
        anchor_y = [anchor["y"] for anchor in anchors]
        xmin = min(anchor_x) - self._sheet_margin
        xmax = max(anchor_x) + self._sheet_margin
        ymin = min(anchor_y) - self._sheet_margin
        ymax = max(anchor_y) + self._sheet_margin

        sane: List[dict[str, Any]] = []
        skipped = 0

        for entity in entities:
            if not self._is_sane_coordinate(entity):
                skipped += 1
                continue

            x = float(entity["x"])
            y = float(entity["y"])
            if xmin <= x <= xmax and ymin <= y <= ymax:
                sane.append(entity)
            else:
                skipped += 1

        logger.info(
            "Filtered to {} sheet entities ({} outliers excluded)",
            len(sane),
            skipped,
        )
        return sane

    def _anchor_seed_boxes(self, anchors: List[DrawingAnchor]) -> Dict[str, BoundingBox]:
        boxes = empty_region_boxes()
        seed_radius = self._sheet_margin * 0.55

        for anchor in anchors:
            region_type = anchor["anchor_type"]
            if region_type not in boxes:
                continue

            box = BoundingBox()
            for angle in range(0, 360, 45):
                radians = math.radians(angle)
                box.include(
                    anchor["x"] + seed_radius * math.cos(radians),
                    anchor["y"] + seed_radius * math.sin(radians),
                )
            box.include(anchor["x"], anchor["y"])
            boxes[region_type] = merge_boxes([boxes[region_type], box])

        return boxes

    def _region_confidence(
        self,
        region_type: str,
        anchors: List[DrawingAnchor],
        assignment_confidence: Dict[str, float],
        assignments: Dict[str, str],
    ) -> float:
        anchor_scores = [
            anchor["confidence"]
            for anchor in anchors
            if anchor["anchor_type"] == region_type
        ]
        anchor_conf = max(anchor_scores) if anchor_scores else 0.5

        region_handles = [
            handle
            for handle, region in assignments.items()
            if region == region_type
        ]
        if not region_handles:
            return round(anchor_conf, 4)

        content_conf = sum(assignment_confidence.get(handle, 0.5) for handle in region_handles)
        content_conf /= len(region_handles)
        return round(min(1.0, (anchor_conf * 0.4) + (content_conf * 0.6)), 4)

    def _is_sane_coordinate(self, entity: dict[str, Any]) -> bool:
        try:
            x = float(entity.get("x", 0))
            y = float(entity.get("y", 0))
        except (TypeError, ValueError):
            return False
        return abs(x) < OUTLIER_COORD_THRESHOLD and abs(y) < OUTLIER_COORD_THRESHOLD
