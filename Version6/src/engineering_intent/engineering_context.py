"""Construct deterministic engineering context for intent evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from src.engineering_intent.intent_rules import extract_general_note_rules, lookup_development_length


class EngineeringContext:
    """Deterministic engineering context for a source reinforcement bar."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot
        self._note_rules = extract_general_note_rules(snapshot.get("engineering_rules") or {})
        self._adjacency = self._build_adjacency(snapshot.get("support_graph") or {})
        self._associations_by_spec = self._index_associations(snapshot.get("geometry_associations") or [])

    def build_for_bar(self, bar: dict[str, Any]) -> dict[str, Any]:
        context = self._snapshot.get("context_by_id", {}).get(str(bar.get("context_id")), {})
        spec = self._snapshot.get("spec_by_id", {}).get(str(bar.get("specification_id")), {})
        trace = bar.get("traceability") or {}
        beam_id = str(bar.get("beam_id") or context.get("beam_id") or "")
        support_refs = self._support_refs(beam_id)
        ld_entry = lookup_development_length(
            self._snapshot.get("development_length_table") or {},
            str(bar.get("steel_grade") or context.get("steel_grade") or ""),
            str(context.get("concrete_grade") or ""),
            float(bar.get("diameter_mm") or 0.0),
        )
        geometry_assoc = self._associations_by_spec.get(str(bar.get("specification_id")))
        continuity_beams = self._continuity_beams(beam_id)

        return {
            "bar_id": bar.get("bar_id"),
            "beam_id": beam_id,
            "role": bar.get("role"),
            "bar_type": bar.get("bar_type"),
            "diameter_mm": bar.get("diameter_mm"),
            "quantity": bar.get("quantity"),
            "steel_grade": bar.get("steel_grade") or context.get("steel_grade"),
            "concrete_grade": context.get("concrete_grade"),
            "support_refs": support_refs,
            "continuity_beams": continuity_beams,
            "clear_span_mm": context.get("clear_span_mm"),
            "effective_span_mm": context.get("effective_span_mm"),
            "cover_top_mm": context.get("cover_top_mm"),
            "cover_bottom_mm": context.get("cover_bottom_mm"),
            "calculation_context": context,
            "calculation_context_id": context.get("context_id"),
            "calculation_status": context.get("calculation_status"),
            "specification": spec,
            "specification_id": spec.get("specification_id"),
            "engineering_object_id": trace.get("engineering_object_id") or spec.get("engineering_object_id"),
            "geometry_association": geometry_assoc,
            "geometry_reference": geometry_assoc.get("association_id") if geometry_assoc else context.get("geometry_association_id"),
            "engineering_graph_node": context.get("knowledge_graph_node_id") or f"BEAM::{beam_id}",
            "general_notes": self._snapshot.get("engineering_rules") or {},
            "general_note_rules": self._note_rules,
            "development_length_entry": ld_entry,
            "development_length_mm": (ld_entry or {}).get("value"),
            "development_length_rule": (ld_entry or {}).get("table"),
            "hook_rule": context.get("hook_rule") or {},
            "anchorage_rule": context.get("anchorage_rule") or {},
            "lap_rule": context.get("lap_rule") or {},
            "support_zones": ["LEFT_SUPPORT", "RIGHT_SUPPORT"],
            "traceability": trace,
        }

    def _support_refs(self, beam_id: str) -> List[str]:
        beam_supports = self._snapshot.get("beam_supports") or {}
        if isinstance(beam_supports, list):
            for entry in beam_supports:
                if str(entry.get("beam_id")) != beam_id:
                    continue
                supports = entry.get("supports") or {}
                refs: List[str] = []
                for side in ("left", "right"):
                    support = supports.get(side) or {}
                    support_id = support.get("id")
                    if support_id:
                        refs.append(str(support_id))
                if refs:
                    return refs
        supports = {}
        if isinstance(beam_supports, dict):
            supports = beam_supports.get("beam_supports") or beam_supports.get("supports") or {}
        if isinstance(supports, dict):
            refs = supports.get(beam_id) or []
            if refs:
                return [str(item) for item in refs]
        adjacency = self._adjacency.get(beam_id, set())
        return sorted(adjacency) if adjacency else [f"SUPPORT::{beam_id}"]

    def _continuity_beams(self, beam_id: str) -> List[str]:
        adjacent = self._adjacency.get(beam_id, set())
        return sorted(item for item in adjacent if item.startswith("B") and item != beam_id)

    @staticmethod
    def _build_adjacency(support_graph: dict[str, Any]) -> Dict[str, Set[str]]:
        adjacency: Dict[str, Set[str]] = {}
        graph = support_graph.get("adjacency") or support_graph.get("connections") or support_graph
        if not isinstance(graph, dict):
            return adjacency
        for node, neighbors in graph.items():
            node_id = str(node)
            if not node_id.startswith("B"):
                continue
            adjacency.setdefault(node_id, set())
            for neighbor in neighbors or []:
                neighbor_id = str(neighbor)
                if neighbor_id.startswith("B"):
                    adjacency[node_id].add(neighbor_id)
                    adjacency.setdefault(neighbor_id, set()).add(node_id)
        return adjacency

    @staticmethod
    def _index_associations(associations: List[dict[str, Any]]) -> Dict[str, dict[str, Any]]:
        index: Dict[str, dict[str, Any]] = {}
        for assoc in associations:
            spec_id = str(assoc.get("specification_id") or "")
            if spec_id:
                index[spec_id] = assoc
        return index
