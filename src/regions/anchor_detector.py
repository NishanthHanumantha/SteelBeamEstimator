"""Detect drawing title anchors from TEXT / MTEXT entities."""

from typing import Any, List, Optional, TypedDict

from loguru import logger

from src.regions.constants import ANCHOR_RULES, AnchorRule
from src.regions.text_normalizer import normalize_drawing_text

TEXT_ENTITY_TYPES = frozenset({"TEXT", "MTEXT"})


class DrawingAnchor(TypedDict):
    anchor_type: str
    text: str
    x: float
    y: float
    confidence: float
    handle: str


class AnchorDetector:
    """Find sheet title anchors that define drawing regions."""

    def detect(self, entities: List[dict[str, Any]]) -> List[DrawingAnchor]:
        anchors: List[DrawingAnchor] = []

        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue

            if entity.get("entity_type") not in TEXT_ENTITY_TYPES:
                continue

            clean_text = entity.get("clean_text")
            if clean_text is None:
                continue

            normalized = normalize_drawing_text(clean_text)
            if not normalized:
                continue

            match = self._match_anchor(normalized)
            if match is None:
                continue

            anchor_type, confidence = match
            x = self._parse_coordinate(entity, "x", index)
            y = self._parse_coordinate(entity, "y", index)

            anchor = DrawingAnchor(
                anchor_type=anchor_type,
                text=normalized,
                x=x,
                y=y,
                confidence=confidence,
                handle=str(entity.get("handle", "")),
            )
            anchors.append(anchor)
            logger.info(
                "Anchor detected: type={} confidence={:.2f} at ({}, {}) — '{}'",
                anchor_type,
                confidence,
                x,
                y,
                normalized[:80],
            )

        anchors.sort(key=lambda item: (-item["y"], item["x"]))
        logger.info("Detected {} drawing anchor(s)", len(anchors))
        return anchors

    def _match_anchor(self, normalized_text: str) -> Optional[tuple[str, float]]:
        best_type: Optional[str] = None
        best_confidence = 0.0

        for rule in ANCHOR_RULES:
            if rule.pattern.search(normalized_text):
                if rule.confidence > best_confidence:
                    best_type = rule.anchor_type
                    best_confidence = rule.confidence

        if best_type is None:
            return None
        return best_type, best_confidence

    def _parse_coordinate(
        self, entity: dict[str, Any], field: str, index: int
    ) -> float:
        value = entity.get(field)
        if value is None:
            logger.warning(
                "Entity at index {} missing '{}' — using 0.0",
                index,
                field,
            )
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
