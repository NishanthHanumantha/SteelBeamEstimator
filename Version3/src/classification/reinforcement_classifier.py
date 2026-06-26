"""Phase D.4.1 — classify normalized engineering objects."""

from typing import Any, Dict, List

from loguru import logger

from src.classification.longitudinal_bar_classifier import LongitudinalBarClassifier
from src.classification.reinforcement_geometry_classifier import (
    ReinforcementGeometryClassifier,
)

_ESTIMATOR_MAP = {
    "STIRRUP": "STIRRUP",
    "SIDE_FACE_REINFORCEMENT": "SIDE_FACE_REINFORCEMENT",
    "ANCHORAGE": "ANCHORAGE",
    "HOOK": "HOOK",
    "LAP": "LAP",
    "SPACER_BAR": "SPACER_BAR",
    "DIMENSION_ENGINEERING": "DIMENSION_ENGINEERING",
    "UNKNOWN": "UNCLASSIFIED",
}


class ReinforcementClassifier:
    """Convert engineering objects into estimator-style categories."""

    def __init__(self) -> None:
        self._geometry = ReinforcementGeometryClassifier()
        self._longitudinal = LongitudinalBarClassifier()

    def classify_all(
        self, engineering_objects: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        classified: List[dict[str, Any]] = []
        for obj in engineering_objects:
            if obj.get("parser_status") != "SUCCESS":
                classified.append(self._skipped(obj))
                continue
            classified.append(self._classify_one(obj))

        logger.info("Classified {} engineering object(s)", len(classified))
        return classified

    def _classify_one(self, obj: dict[str, Any]) -> dict[str, Any]:
        eng_type = obj.get("engineering_type", "UNKNOWN")
        entry = {
            "object_id": obj.get("object_id"),
            "source_annotation_id": obj.get("source_annotation_id"),
            "engineering_type": eng_type,
            "clean_text": obj.get("clean_text"),
            "detail_region_id": obj.get("detail_region_id"),
            "beam_group_id": obj.get("beam_group_id"),
            "resolved_beam_mark": obj.get("resolved_beam_mark"),
            "owner_sketch_id": obj.get("owner_sketch_id"),
            "coordinates": obj.get("coordinates"),
            "leader_endpoint": obj.get("leader_endpoint"),
        }

        if eng_type == "LONGITUDINAL_BAR":
            position, continuity, geo = self._geometry.classify_longitudinal(obj)
            category, cat_score = self._longitudinal.classify(position, continuity)
            entry.update(
                {
                    "position": position,
                    "continuity": continuity,
                    "estimator_category": category,
                    "classification_confidence": int(
                        round((cat_score + geo.get("geometry_confidence", 0)) / 2)
                    ),
                    "quantity": obj.get("quantity"),
                    "diameter_mm": obj.get("diameter_mm"),
                }
            )
            return entry

        category = _ESTIMATOR_MAP.get(eng_type, "UNCLASSIFIED")
        entry.update(
            {
                "position": None,
                "continuity": None,
                "estimator_category": category,
                "classification_confidence": 80,
                "parsed_fields": {
                    k: v
                    for k, v in obj.items()
                    if k not in (
                        "sketch_bbox",
                        "coordinates",
                        "leader_endpoint",
                        "expanded_beams",
                    )
                },
            }
        )
        return entry

    def _skipped(self, obj: dict[str, Any]) -> dict[str, Any]:
        return {
            "object_id": obj.get("object_id"),
            "source_annotation_id": obj.get("source_annotation_id"),
            "engineering_type": obj.get("engineering_type", "UNKNOWN"),
            "clean_text": obj.get("clean_text"),
            "estimator_category": "UNCLASSIFIED",
            "classification_confidence": 0,
            "classification_status": "SKIPPED",
            "parser_status": obj.get("parser_status"),
        }
