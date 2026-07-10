"""Merge compatible engineering intents into coherent detailing decisions."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent_resolution.intent_priority_engine import IntentPriorityEngine


class IntentMerger:
    """Merge compatible intents; never merge conflicting intents."""

    def __init__(self, priority_engine: IntentPriorityEngine) -> None:
        self._priority = priority_engine

    def merge(
        self,
        context: dict[str, Any],
        suppressed_ids: Set[str],
        conflicts: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        intents = [
            intent
            for intent in (context.get("intents") or [])
            if str(intent.get("intent_id")) not in suppressed_ids
        ]
        active_types = {str(item.get("intent_type") or "") for item in intents}
        merges: List[dict[str, Any]] = []
        consumed: Set[str] = set()

        conflicted_pairs: Set[tuple[str, str]] = set()
        for conflict in conflicts:
            if conflict.get("conflict_class") == "MUTUALLY_EXCLUSIVE":
                types = list(conflict.get("intent_types") or [])
                if len(types) == 2:
                    conflicted_pairs.add((types[0], types[1]))
                    conflicted_pairs.add((types[1], types[0]))

        for group in self._priority.merge_groups:
            members = [str(item) for item in (group.get("members") or [])]
            if any((left, right) in conflicted_pairs for left in members for right in members if left != right):
                continue
            if not all(member in active_types for member in members):
                continue
            member_intents = [
                intent
                for intent in intents
                if str(intent.get("intent_type") or "") in set(members)
                and str(intent.get("intent_id")) not in consumed
            ]
            if len({str(item.get("intent_type")) for item in member_intents}) < len(members):
                continue
            ordered = self._priority.sort_intents(member_intents)
            intent_ids = [str(item.get("intent_id")) for item in ordered]
            consumed.update(intent_ids)
            merges.append(
                {
                    "merge_id": f"MERGE::{context.get('decision_group_key')}::{group.get('name')}",
                    "merge_name": group.get("name"),
                    "result_category": group.get("result_category"),
                    "resolution_rule": group.get("resolution_rule"),
                    "member_intent_ids": intent_ids,
                    "member_intent_types": [str(item.get("intent_type")) for item in ordered],
                    "primary_intent_id": intent_ids[0] if intent_ids else None,
                    "decision_group_key": context.get("decision_group_key"),
                    "compatible": True,
                }
            )

        return sorted(merges, key=lambda item: str(item.get("merge_id")))
