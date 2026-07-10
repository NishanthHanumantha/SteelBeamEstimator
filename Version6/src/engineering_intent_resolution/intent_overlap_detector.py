"""Detect overlapping and duplicate engineering intents."""

from __future__ import annotations

from typing import Any, Dict, List


class IntentOverlapDetector:
    """Deterministic overlap detection within a decision group."""

    def detect(self, context: dict[str, Any]) -> List[dict[str, Any]]:
        intents = list(context.get("intents") or [])
        overlaps: List[dict[str, Any]] = []

        by_type: Dict[str, List[dict[str, Any]]] = {}
        for intent in intents:
            intent_type = str(intent.get("intent_type") or "UNKNOWN")
            by_type.setdefault(intent_type, []).append(intent)

        for intent_type, group in sorted(by_type.items()):
            if len(group) < 2:
                continue
            ordered = sorted(group, key=lambda item: str(item.get("intent_id") or ""))
            overlaps.append(
                {
                    "overlap_type": "DUPLICATE_INTENT",
                    "intent_type": intent_type,
                    "intent_ids": [str(item.get("intent_id")) for item in ordered],
                    "decision_group_key": context.get("decision_group_key"),
                    "description": f"Multiple {intent_type} intents in the same decision group.",
                }
            )

        type_set = {str(item.get("intent_type") or "") for item in intents}
        if "SUPPLEMENTARY_DEVELOPMENT_LENGTH" in type_set and "SUPPLEMENTARY_ANCHORAGE" in type_set:
            overlaps.append(
                {
                    "overlap_type": "EQUIVALENT_OVERLAP",
                    "intent_type": "SUPPORT_REINFORCEMENT",
                    "intent_ids": [
                        str(item.get("intent_id"))
                        for item in intents
                        if item.get("intent_type")
                        in {"SUPPLEMENTARY_DEVELOPMENT_LENGTH", "SUPPLEMENTARY_ANCHORAGE"}
                    ],
                    "decision_group_key": context.get("decision_group_key"),
                    "description": "Development length and anchorage overlap as support reinforcement.",
                }
            )

        if "SUPPLEMENTARY_CONTINUATION" in type_set and "SUPPLEMENTARY_SUPPORT_BAR" in type_set:
            overlaps.append(
                {
                    "overlap_type": "EQUIVALENT_OVERLAP",
                    "intent_type": "CONTINUOUS_SUPPORT_REINFORCEMENT",
                    "intent_ids": [
                        str(item.get("intent_id"))
                        for item in intents
                        if item.get("intent_type")
                        in {"SUPPLEMENTARY_CONTINUATION", "SUPPLEMENTARY_SUPPORT_BAR"}
                    ],
                    "decision_group_key": context.get("decision_group_key"),
                    "description": "Continuation and support bar overlap as continuous support reinforcement.",
                }
            )

        if "SUPPLEMENTARY_TERMINATION" in type_set and (
            "SUPPLEMENTARY_CONTINUATION" in type_set or "SUPPLEMENTARY_ANCHORAGE" in type_set
        ):
            overlaps.append(
                {
                    "overlap_type": "CONFLICTING_TERMINATION_OVERLAP",
                    "intent_type": "SUPPLEMENTARY_TERMINATION",
                    "intent_ids": [
                        str(item.get("intent_id"))
                        for item in intents
                        if item.get("intent_type")
                        in {
                            "SUPPLEMENTARY_TERMINATION",
                            "SUPPLEMENTARY_CONTINUATION",
                            "SUPPLEMENTARY_ANCHORAGE",
                        }
                    ],
                    "decision_group_key": context.get("decision_group_key"),
                    "description": "Termination overlaps with continuation/anchorage in the same support zone.",
                }
            )

        return sorted(
            overlaps,
            key=lambda item: (str(item.get("overlap_type")), str(item.get("intent_type"))),
        )
