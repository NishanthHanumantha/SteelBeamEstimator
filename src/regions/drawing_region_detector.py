"""Orchestrate drawing region detection (Phase 3A.5)."""

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.regions.anchor_detector import AnchorDetector, DrawingAnchor
from src.regions.bounding_box import BoundingBox, empty_region_boxes
from src.regions.content_classifier import ContentClassifier
from src.regions.region_assigner import RegionAssigner
from src.regions.region_builder import RegionBuilder
from src.regions.region_report import RegionReportBuilder
from src.regions.region_validator import RegionValidator
from src.utils.entities_loader import load_entities_json

TEXT_ENTITY_TYPES = frozenset({"TEXT", "MTEXT"})


class DrawingRegionDetector:
    """Estimator-style drawing region detection pipeline."""

    def __init__(self) -> None:
        self._anchor_detector = AnchorDetector()
        self._classifier = ContentClassifier()
        self._region_builder = RegionBuilder()
        self._region_assigner = RegionAssigner(self._classifier)
        self._report_builder = RegionReportBuilder()
        self._validator = RegionValidator()

    def detect(self, entities_path: Path) -> dict[str, Any]:
        entities = self._prepare_entities(load_entities_json(entities_path))
        anchors = self._anchor_detector.detect(entities)

        content_assignments, content_confidences = self._content_only_assignments(
            entities
        )

        preliminary_boxes = self._boxes_from_assignments(
            entities, anchors, content_assignments, content_confidences
        )

        assignments, confidences = self._region_assigner.assign(
            entities, anchors, preliminary_boxes
        )

        regions = self._region_builder.build(
            entities,
            anchors,
            assignments,
            confidences,
        )

        final_boxes = RegionAssigner.boxes_from_regions(regions)
        assignments, confidences = self._region_assigner.assign(
            entities, anchors, final_boxes
        )

        regions = self._region_builder.build(
            entities,
            anchors,
            assignments,
            confidences,
        )

        entity_map = [
            {
                "handle": handle,
                "region": region,
                "confidence": round(confidences.get(handle, 0.0), 4),
            }
            for handle, region in sorted(assignments.items())
        ]

        report = self._report_builder.build(
            regions=regions,
            anchors=anchors,
            entities=entities,
            assignments=assignments,
        )
        validation = self._validator.validate(entities, assignments)

        return {
            "anchors": anchors,
            "regions": regions,
            "entity_region_map": entity_map,
            "report": report,
            "validation": validation,
        }

    def _prepare_entities(self, entities: List[dict[str, Any]]) -> List[dict[str, Any]]:
        prepared: List[dict[str, Any]] = []
        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue
            copy = dict(entity)
            copy["x"] = self._parse_coordinate(copy, "x", index)
            copy["y"] = self._parse_coordinate(copy, "y", index)
            prepared.append(copy)
        return prepared

    def _content_only_assignments(
        self, entities: List[dict[str, Any]]
    ) -> tuple[Dict[str, str], Dict[str, float]]:
        assignments: Dict[str, str] = {}
        confidences: Dict[str, float] = {}

        for entity in entities:
            handle = str(entity.get("handle", ""))
            if not handle:
                continue

            result = self._classifier.classify(entity)
            if result is None:
                continue

            region, confidence = result
            assignments[handle] = region
            confidences[handle] = confidence

        logger.info(
            "Content classifier pre-assigned {} entities",
            len(assignments),
        )
        return assignments, confidences

    def _boxes_from_assignments(
        self,
        entities: List[dict[str, Any]],
        anchors: List[DrawingAnchor],
        assignments: Dict[str, str],
        confidences: Dict[str, float],
    ) -> Dict[str, BoundingBox]:
        regions = self._region_builder.build(
            entities, anchors, assignments, confidences
        )
        if regions:
            return RegionAssigner.boxes_from_regions(regions)

        boxes = empty_region_boxes()
        seed_regions = self._region_builder.build(
            entities,
            anchors,
            {},
            {},
        )
        return RegionAssigner.boxes_from_regions(seed_regions)

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
