"""Build deterministic engineering intent graphs."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent_resolution.intent_priority_engine import IntentPriorityEngine


EDGE_TYPES = (
    "SUPPORTS",
    "DEPENDS_ON",
    "EQUIVALENT",
    "CONFLICTS_WITH",
    "OVERRIDES",
    "REQUIRES",
    "COMPLEMENTS",
)


class IntentGraphBuilder:
    """Create one deterministic intent graph per decision group."""

    def __init__(self, priority_engine: IntentPriorityEngine) -> None:
        self._priority = priority_engine

    def build_all(self, decision_contexts: List[dict[str, Any]]) -> List[dict[str, Any]]:
        graphs = [self.build_one(context) for context in decision_contexts]
        return sorted(graphs, key=lambda item: str(item.get("graph_id")))

    def build_one(self, context: dict[str, Any]) -> dict[str, Any]:
        intents = list(context.get("intents") or [])
        nodes = []
        for intent in self._priority.sort_intents(intents):
            nodes.append(
                {
                    "intent_id": intent.get("intent_id"),
                    "intent_key": intent.get("intent_key"),
                    "intent_type": intent.get("intent_type"),
                    "priority": self._priority.priority(str(intent.get("intent_type") or "")),
                    "source_bar_id": intent.get("source_bar_id"),
                    "beam_id": intent.get("beam_id"),
                    "support_zone": intent.get("support_zone"),
                }
            )

        type_to_ids: Dict[str, List[str]] = {}
        for node in nodes:
            intent_type = str(node.get("intent_type") or "")
            intent_id = str(node.get("intent_id") or "")
            type_to_ids.setdefault(intent_type, []).append(intent_id)

        edges: List[dict[str, str]] = []
        seen: Set[tuple[str, str, str]] = set()

        def add_edge(source_id: str, target_id: str, edge_type: str) -> None:
            key = (source_id, target_id, edge_type)
            if source_id == target_id or key in seen:
                return
            seen.add(key)
            edges.append(
                {
                    "source_intent_id": source_id,
                    "target_intent_id": target_id,
                    "edge_type": edge_type,
                }
            )

        for source_type, required_type in [
            (rule["source"], rule["requires"]) for rule in self._priority.require_rules
        ]:
            for source_id in type_to_ids.get(source_type, []):
                for target_id in type_to_ids.get(required_type, []):
                    add_edge(source_id, target_id, "REQUIRES")
                    add_edge(target_id, source_id, "SUPPORTS")

        for rule in self._priority.complement_rules:
            for source_id in type_to_ids.get(rule["source"], []):
                for target_id in type_to_ids.get(rule["complements"], []):
                    add_edge(source_id, target_id, "COMPLEMENTS")
                    add_edge(target_id, source_id, "SUPPORTS")

        for left, right in self._priority.equivalent_pairs:
            for left_id in type_to_ids.get(left, []):
                for right_id in type_to_ids.get(right, []):
                    add_edge(left_id, right_id, "EQUIVALENT")
                    add_edge(right_id, left_id, "EQUIVALENT")

        for rule in self._priority.override_rules:
            for dominant_id in type_to_ids.get(rule["dominant"], []):
                for suppressed_id in type_to_ids.get(rule["suppresses"], []):
                    add_edge(dominant_id, suppressed_id, "OVERRIDES")

        for left, right in self._priority.mutual_exclusions:
            for left_id in type_to_ids.get(left, []):
                for right_id in type_to_ids.get(right, []):
                    add_edge(left_id, right_id, "CONFLICTS_WITH")
                    add_edge(right_id, left_id, "CONFLICTS_WITH")

        # Same-type duplicates depend on each other for conflict detection.
        for intent_ids in type_to_ids.values():
            ordered = sorted(intent_ids)
            for index, left_id in enumerate(ordered):
                for right_id in ordered[index + 1 :]:
                    add_edge(left_id, right_id, "DEPENDS_ON")
                    add_edge(right_id, left_id, "DEPENDS_ON")

        edges = sorted(
            edges,
            key=lambda item: (
                item["edge_type"],
                item["source_intent_id"],
                item["target_intent_id"],
            ),
        )
        return {
            "graph_id": f"GRAPH::{context.get('decision_group_key')}",
            "decision_group_key": context.get("decision_group_key"),
            "beam_id": context.get("beam_id"),
            "source_bar_id": context.get("source_bar_id"),
            "support_zone": context.get("support_zone"),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
