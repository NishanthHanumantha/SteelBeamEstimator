"""Content-based classification of entities into drawing regions."""

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Pattern, Tuple

from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN
from src.regions.constants import (
    FRAMING_LAYER_HINTS,
    REINFORCEMENT_LAYER_HINTS,
)
from src.regions.text_normalizer import normalize_drawing_text

Classification = Tuple[str, float]

REINFORCEMENT_TEXT_RULES: List[Tuple[Pattern[str], float]] = [
    (re.compile(r"\d+-Y\d+", re.IGNORECASE), 0.97),
    (re.compile(r"\d+L-Y\d+", re.IGNORECASE), 0.97),
    (re.compile(r"^Ld$", re.IGNORECASE), 0.97),
    (re.compile(r"C/C", re.IGNORECASE), 0.90),
    (re.compile(r"^\d{3,4}$"), 0.75),
    (re.compile(r"^\d{3,4}\.\d+$"), 0.70),
]

STIRRUP_TEXT_RULES: List[Tuple[Pattern[str], float]] = [
    (re.compile(r"TYPICAL\s+STIRRUP", re.IGNORECASE), 0.98),
    (re.compile(r"STIRRUP\s+DETAIL", re.IGNORECASE), 0.95),
]

GENERAL_NOTES_RULES: List[Tuple[Pattern[str], float]] = [
    (re.compile(r"GENERAL\s+NOTES", re.IGNORECASE), 0.98),
    (re.compile(r"^NOTE:", re.IGNORECASE), 0.80),
]


@dataclass(frozen=True)
class ContentClassifier:
    """Assign region labels from structural drawing text and layer hints."""

    def classify(self, entity: dict[str, Any]) -> Optional[Classification]:
        entity_type = str(entity.get("entity_type", ""))
        layer = str(entity.get("layer", ""))

        layer_result = self._classify_layer(entity_type, layer)
        if layer_result is not None:
            return layer_result

        clean_text = normalize_drawing_text(str(entity.get("clean_text", "")))
        text_result = self._classify_text(clean_text)
        if text_result is not None:
            return text_result

        if entity_type in {"LINE", "LWPOLYLINE", "POLYLINE"}:
            if layer in FRAMING_LAYER_HINTS:
                return ("framing_plan", 0.65)
            if layer in REINFORCEMENT_LAYER_HINTS:
                return ("beam_reinforcement", 0.60)

        return None

    def _classify_text(self, clean_text: str) -> Optional[Classification]:
        if not clean_text:
            return None

        if BEAM_LABEL_PATTERN.match(clean_text):
            return ("framing_plan", 0.99)

        for pattern, confidence in STIRRUP_TEXT_RULES:
            if pattern.search(clean_text):
                return ("typical_stirrup", confidence)

        for pattern, confidence in GENERAL_NOTES_RULES:
            if pattern.search(clean_text):
                return ("general_notes", confidence)

        for pattern, confidence in REINFORCEMENT_TEXT_RULES:
            if pattern.search(clean_text):
                return ("beam_reinforcement", confidence)

        if re.search(r"FRAMING\s+PLAN", clean_text, re.IGNORECASE):
            return ("framing_plan", 0.95)

        return None

    def _classify_layer(
        self, entity_type: str, layer: str
    ) -> Optional[Classification]:
        if entity_type == "DIMENSION":
            if layer in {"-S-DIM", "-S-STIRUP"}:
                return ("beam_reinforcement", 0.93)
            if layer == "-STR-RF-DIM":
                return ("beam_reinforcement", 0.88)

        if entity_type not in {"TEXT", "MTEXT", "DIMENSION"}:
            return None

        if layer == "SEC TEXT":
            return ("framing_plan", 0.85)

        if layer in {"-STR-TEXT", "-S-STIRUP", "-S-DIM"}:
            return ("beam_reinforcement", 0.82)

        if layer == "G-ANNO-TEXT" and entity_type in {"TEXT", "MTEXT"}:
            return None

        return None
