"""Detect deterministic conflicts among engineering intents."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent_resolution.intent_priority_engine import IntentPriorityEngine


class IntentConflictDetector:
    """Classify conflicts without heuristics."""

    def __init__(self, priority_engine: IntentPriorityEngine) -> None:
        self._priority = priority_engine

    def detect(self, context: dict[str, Any], overlaps: List[dict[str, Any]]) -> List[dict[str, Any]]:
        intents = list(context.get("intents") or [])
        conflicts: List[dict[str, Any]] = []
        by_type: Dict[str, List[dict[str, Any]]] = {}
        for intent in intents:
            by_type.setdefault(str(intent.get("intent_type") or "UNKNOWN"), []).append(intent)

        for intent_type, group in sorted(by_type.items()):
            if len(group) < 2:
                continue
            ordered = sorted(group, key=lambda item: str(item.get("intent_id") or ""))
            conflict_class = "DUPLICATE_HOOKS" if intent_type == "SUPPLEMENTARY_HOOK" else "DUPLICATE_INTENT"
            if intent_type == "SUPPLEMENTARY_ANCHORAGE":
                conflict_class = "MULTIPLE_ANCHORAGE"
            conflicts.append(
                {
                    "conflict_id": f"CONFLICT::{context.get('decision_group_key')}::{conflict_class}::{intent_type}",
                    "conflict_class": conflict_class,
                    "intent_ids": [str(item.get("intent_id")) for item in ordered],
                    "intent_types": [intent_type],
                    "decision_group_key": context.get("decision_group_key"),
                    "resolved": True,
                    "resolution": "KEEP_HIGHEST_PRIORITY_DETERMINISTIC_ORDER",
                    "description": f"{conflict_class} detected for {intent_type}.",
                }
            )

        present_types = set(by_type.keys())
        for left, right in self._priority.mutual_exclusions:
            if left in present_types and right in present_types:
                conflicts.append(
                    {
                        "conflict_id": (
                            f"CONFLICT::{context.get('decision_group_key')}::MUTUALLY_EXCLUSIVE::{left}::{right}"
                        ),
                        "conflict_class": "MUTUALLY_EXCLUSIVE",
                        "intent_ids": [
                            str(item.get("intent_id"))
                            for item in intents
                            if item.get("intent_type") in {left, right}
                        ],
                        "intent_types": sorted([left, right]),
                        "decision_group_key": context.get("decision_group_key"),
                        "resolved": True,
                        "resolution": "SUPPRESS_LOWER_PRIORITY",
                        "description": f"{left} and {right} are mutually exclusive.",
                    }
                )

        for rule in self._priority.override_rules:
            dominant = rule["dominant"]
            suppressed = rule["suppresses"]
            if dominant in present_types and suppressed in present_types:
                conflicts.append(
                    {
                        "conflict_id": (
                            f"CONFLICT::{context.get('decision_group_key')}::DOMINATED::{dominant}::{suppressed}"
                        ),
                        "conflict_class": "DOMINATED_INTENT",
                        "intent_ids": [
                            str(item.get("intent_id"))
                            for item in intents
                            if item.get("intent_type") in {dominant, suppressed}
                        ],
                        "intent_types": [dominant, suppressed],
                        "decision_group_key": context.get("decision_group_key"),
                        "resolved": True,
                        "resolution": "SUPPRESS_DOMINATED",
                        "description": f"{dominant} dominates {suppressed}.",
                    }
                )

        if "SUPPLEMENTARY_TERMINATION" in present_types and (
            "SUPPLEMENTARY_CONTINUATION" in present_types or "SUPPLEMENTARY_SUPPORT_BAR" in present_types
        ):
            conflicts.append(
                {
                    "conflict_id": f"CONFLICT::{context.get('decision_group_key')}::CONFLICTING_TERMINATION",
                    "conflict_class": "CONFLICTING_TERMINATION",
                    "intent_ids": [
                        str(item.get("intent_id"))
                        for item in intents
                        if item.get("intent_type")
                        in {
                            "SUPPLEMENTARY_TERMINATION",
                            "SUPPLEMENTARY_CONTINUATION",
                            "SUPPLEMENTARY_SUPPORT_BAR",
                        }
                    ],
                    "intent_types": sorted(
                        present_types
                        & {
                            "SUPPLEMENTARY_TERMINATION",
                            "SUPPLEMENTARY_CONTINUATION",
                            "SUPPLEMENTARY_SUPPORT_BAR",
                        }
                    ),
                    "decision_group_key": context.get("decision_group_key"),
                    "resolved": True,
                    "resolution": "SUPPRESS_TERMINATION",
                    "description": "Termination conflicts with continuation/support detailing.",
                }
            )

        if "SUPPLEMENTARY_CONTINUATION" in present_types and len(by_type.get("SUPPLEMENTARY_CONTINUATION", [])) > 1:
            conflicts.append(
                {
                    "conflict_id": f"CONFLICT::{context.get('decision_group_key')}::OVERLAPPING_CONTINUATION",
                    "conflict_class": "OVERLAPPING_CONTINUATION",
                    "intent_ids": [
                        str(item.get("intent_id"))
                        for item in by_type.get("SUPPLEMENTARY_CONTINUATION", [])
                    ],
                    "intent_types": ["SUPPLEMENTARY_CONTINUATION"],
                    "decision_group_key": context.get("decision_group_key"),
                    "resolved": True,
                    "resolution": "KEEP_FIRST_DETERMINISTIC",
                    "description": "Multiple continuation intents overlap in the same group.",
                }
            )

        # Preserve overlap-derived conflict visibility.
        for overlap in overlaps:
            if overlap.get("overlap_type") == "CONFLICTING_TERMINATION_OVERLAP":
                conflict_id = f"CONFLICT::{context.get('decision_group_key')}::OVERLAP_TERMINATION"
                if any(item.get("conflict_id") == conflict_id for item in conflicts):
                    continue
                conflicts.append(
                    {
                        "conflict_id": conflict_id,
                        "conflict_class": "CONFLICTING_TERMINATION",
                        "intent_ids": list(overlap.get("intent_ids") or []),
                        "intent_types": ["SUPPLEMENTARY_TERMINATION"],
                        "decision_group_key": context.get("decision_group_key"),
                        "resolved": True,
                        "resolution": "SUPPRESS_TERMINATION",
                        "description": overlap.get("description"),
                    }
                )

        return sorted(conflicts, key=lambda item: str(item.get("conflict_id")))

    @staticmethod
    def suppressed_ids(conflicts: List[dict[str, Any]], intents: List[dict[str, Any]], priority_engine: IntentPriorityEngine) -> Set[str]:
        suppressed: Set[str] = set()
        by_id = {str(item.get("intent_id")): item for item in intents if item.get("intent_id")}
        for conflict in conflicts:
            intent_ids = [str(item) for item in (conflict.get("intent_ids") or [])]
            conflict_class = str(conflict.get("conflict_class") or "")
            if conflict_class in {
                "DUPLICATE_INTENT",
                "DUPLICATE_HOOKS",
                "MULTIPLE_ANCHORAGE",
                "OVERLAPPING_CONTINUATION",
            }:
                ordered = priority_engine.sort_intents([by_id[item] for item in intent_ids if item in by_id])
                for item in ordered[1:]:
                    suppressed.add(str(item.get("intent_id")))
            elif conflict_class in {"DOMINATED_INTENT", "MUTUALLY_EXCLUSIVE", "CONFLICTING_TERMINATION"}:
                ordered = priority_engine.sort_intents([by_id[item] for item in intent_ids if item in by_id])
                if not ordered:
                    continue
                keep_type = str(ordered[0].get("intent_type") or "")
                for item in ordered[1:]:
                    if str(item.get("intent_type") or "") != keep_type:
                        suppressed.add(str(item.get("intent_id")))
                    elif conflict_class == "MUTUALLY_EXCLUSIVE":
                        suppressed.add(str(item.get("intent_id")))
        return suppressed
