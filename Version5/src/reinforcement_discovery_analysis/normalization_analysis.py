"""Analyse normalization from detected callouts to engineering bars."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


class NormalizationAnalyzer:
    """Aggregate normalization losses and reasons."""

    REASON_MAP = {
        "Unsupported notation": "Unknown notation",
        "Engineering bar not created": "Multiple bars unresolved",
        "Unknown diameter": "Unknown diameter",
        "Unknown beam": "Missing geometry",
        "Calculation deferred": "Unknown bar type",
        "Partial calculation context.": "Missing specification",
        "Missing specification": "Missing specification",
    }

    def analyze(self, inventory: List[dict[str, Any]]) -> dict[str, Any]:
        detected = sum(1 for item in inventory if item.get("pipeline_trace", {}).get("text_detected"))
        normalized = sum(1 for item in inventory if item.get("normalized_bar_id"))
        lost = max(detected - normalized, 0)
        reasons: Counter[str] = Counter()
        examples: Dict[str, List[dict[str, Any]]] = {}

        for item in inventory:
            if item.get("normalized_bar_id"):
                continue
            if not item.get("classified") or not item.get("associated"):
                continue
            raw_reason = str(item.get("failure_reason") or "Engineering bar not created")
            reason = self._normalize_reason(raw_reason)
            reasons[reason] += 1
            examples.setdefault(reason, [])
            if len(examples[reason]) < 5:
                examples[reason].append(
                    {
                        "discovery_id": item.get("discovery_id"),
                        "original_text": item.get("original_text"),
                        "beam": item.get("beam_association"),
                    }
                )

        return {
            "detected": detected,
            "normalized": normalized,
            "lost": lost,
            "normalization_success_percent": round((normalized / detected) * 100.0, 2) if detected else 0.0,
            "reasons": [
                {"reason": reason, "count": count, "examples": examples.get(reason, [])}
                for reason, count in reasons.most_common()
            ],
        }

    def _normalize_reason(self, value: str) -> str:
        lowered = value.lower()
        for key, label in self.REASON_MAP.items():
            if key.lower() in lowered:
                return label
        if "spacing" in lowered:
            return "Unknown spacing"
        if "notation" in lowered:
            return "Unknown notation"
        if "diameter" in lowered:
            return "Unknown diameter"
        return value or "Unknown notation"
