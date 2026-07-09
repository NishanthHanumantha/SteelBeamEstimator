"""Classify reinforcement drawing callouts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.estimator_validation.drawing_interpretation.drawing_callout_extractor import BAR_PATTERN


BEAM_HEADER_PATTERN = re.compile(r"^B\d+\(", re.IGNORECASE)


@dataclass
class CalloutClassification:
    is_reinforcement: bool
    classification: str
    role: str
    diameter_mm: Optional[float] = None
    quantity: Optional[float] = None
    spacing_mm: Optional[float] = None
    confidence: float = 0.0
    ambiguous: bool = False
    unknown: bool = False
    multiple_interpretations: bool = False
    interpretations: List[dict[str, Any]] = field(default_factory=list)
    failure_reason: Optional[str] = None


class CalloutClassifier:
    """Deterministic reinforcement callout classification."""

    def classify_text(self, text: str) -> CalloutClassification:
        cleaned = re.sub(r"\\A\d+;", "", str(text or "")).strip()
        if not cleaned:
            return CalloutClassification(
                is_reinforcement=False,
                classification="EMPTY",
                role="UNKNOWN",
                unknown=True,
                confidence=0.0,
                failure_reason="Empty text",
            )
        if BEAM_HEADER_PATTERN.match(cleaned):
            return CalloutClassification(
                is_reinforcement=False,
                classification="BEAM_SECTION",
                role="ANNOTATION",
                confidence=1.0,
            )

        interpretations: List[dict[str, Any]] = []
        normalized = cleaned.replace("-", "")
        for match in BAR_PATTERN.finditer(normalized):
            qty = float(match.group("qty")) if match.group("qty") else None
            dia_text = match.group("dia").upper().replace("Y", "")
            diameter = float(dia_text) if dia_text.isdigit() else None
            spacing = float(match.group("spacing")) if match.group("spacing") else None
            role = self._infer_role(cleaned, spacing)
            interpretations.append(
                {
                    "role": role,
                    "diameter_mm": diameter,
                    "quantity": qty,
                    "spacing_mm": spacing,
                    "pattern": match.group(0),
                }
            )

        if not interpretations:
            return CalloutClassification(
                is_reinforcement=True,
                classification="UNKNOWN",
                role="UNKNOWN",
                unknown=True,
                confidence=0.2,
                failure_reason="Unsupported notation",
            )

        primary = interpretations[0]
        ambiguous = len(interpretations) > 1
        unknown_diameter = primary.get("diameter_mm") is None
        return CalloutClassification(
            is_reinforcement=True,
            classification=primary["role"] if not unknown_diameter else "UNKNOWN",
            role=primary["role"],
            diameter_mm=primary.get("diameter_mm"),
            quantity=primary.get("quantity"),
            spacing_mm=primary.get("spacing_mm"),
            confidence=0.95 if not ambiguous and not unknown_diameter else 0.6,
            ambiguous=ambiguous,
            unknown=unknown_diameter,
            multiple_interpretations=ambiguous,
            interpretations=interpretations,
            failure_reason="Ambiguous notation" if ambiguous else ("Unknown diameter" if unknown_diameter else None),
        )

    @staticmethod
    def _infer_role(text: str, spacing: Optional[float]) -> str:
        upper = text.upper()
        if spacing is not None or "@" in upper or "C/C" in upper:
            return "STIRRUP"
        if "SPACER" in upper:
            return "SPACER_BAR"
        if "SFR" in upper:
            return "SFR"
        if "EXTRA" in upper:
            return "TOP_EXTRA"
        if "BOTTOM" in upper:
            return "BOTTOM_MAIN"
        if "SIDE" in upper:
            return "SIDE_BAR"
        return "TOP_MAIN"

    def analyze(self, inventory: List[dict[str, Any]]) -> dict[str, Any]:
        total = len(inventory)
        classified = sum(1 for item in inventory if item.get("classified"))
        unknown = sum(1 for item in inventory if item.get("classification") == "UNKNOWN")
        ambiguous = sum(1 for item in inventory if item.get("ambiguous"))
        multiple = sum(1 for item in inventory if item.get("multiple_interpretations"))
        confidences = [float(item.get("callout_confidence") or 0.0) for item in inventory if item.get("classified")]
        average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        unknown_patterns: Dict[str, dict[str, Any]] = {}
        ambiguous_patterns: Dict[str, dict[str, Any]] = {}
        for item in inventory:
            text = str(item.get("original_text") or "")
            if item.get("classification") == "UNKNOWN":
                bucket = unknown_patterns.setdefault(
                    text,
                    {"pattern": text, "count": 0, "examples": []},
                )
                bucket["count"] += 1
                if len(bucket["examples"]) < 3:
                    bucket["examples"].append(
                        {
                            "discovery_id": item.get("discovery_id"),
                            "beam": item.get("beam_association"),
                            "coordinates": item.get("coordinates"),
                        }
                    )
            if item.get("ambiguous"):
                bucket = ambiguous_patterns.setdefault(
                    text,
                    {"pattern": text, "count": 0, "examples": []},
                )
                bucket["count"] += 1
                if len(bucket["examples"]) < 3:
                    bucket["examples"].append(
                        {
                            "discovery_id": item.get("discovery_id"),
                            "interpretations": item.get("interpretations", []),
                        }
                    )

        return {
            "total_callouts": total,
            "successfully_classified": classified,
            "unknown": unknown,
            "ambiguous": ambiguous,
            "multiple_interpretations": multiple,
            "classification_success_percent": round((classified / total) * 100.0, 2) if total else 0.0,
            "average_confidence": average_confidence,
            "top_unknown_patterns": sorted(unknown_patterns.values(), key=lambda x: x["count"], reverse=True)[:20],
            "top_ambiguous_patterns": sorted(ambiguous_patterns.values(), key=lambda x: x["count"], reverse=True)[:20],
        }
