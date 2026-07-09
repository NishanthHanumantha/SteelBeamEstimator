"""Phase F registry index for deterministic geometry lookup — Phase H.2."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.framing.engineering_ids import beam_id, ecs_id, length_id, section_id, to_namespaced


class PhaseFRegistryIndex:
    """Build once — O(1) registry lookups for geometry association."""

    def __init__(self, model: dict[str, Any]) -> None:
        self._beam_marks: Set[str] = set()
        self._beam_records: Dict[str, dict[str, Any]] = {}
        self._contexts_by_mark: Dict[str, dict[str, Any]] = {}
        self._graph_node_ids: Set[str] = set()
        self._graph_beam_nodes: Dict[str, dict[str, Any]] = {}
        self._section_ids: Set[str] = set()
        self._length_ids: Set[str] = set()
        self._ecs_ids: Set[str] = set()
        self._clear_span_marks: Set[str] = set()
        self._effective_span_marks: Set[str] = set()
        self._stationing_marks: Set[str] = set()
        self._support_graph_ids: Set[str] = set()

        self._index_beams(model.get("beams", []))
        self._index_contexts(model.get("beam_engineering_contexts", []))
        self._index_knowledge_graph(model.get("framing_knowledge_graph", {}))
        self._index_coordinate_systems(model.get("engineering_coordinate_systems", []))
        self._index_stationing(model.get("beam_stationing_export", []))
        self._index_support_graph(model.get("support_graph", {}))

    def _index_beams(self, beams: List[dict[str, Any]]) -> None:
        for beam in beams:
            mark = str(beam.get("beam_mark") or beam.get("beam_id") or "")
            if not mark:
                continue
            self._beam_marks.add(mark)
            self._beam_records.setdefault(mark, beam)
            if beam.get("stationing"):
                self._stationing_marks.add(mark)
            if beam.get("length_model"):
                self._clear_span_marks.add(mark)
                self._effective_span_marks.add(mark)

    def _index_contexts(self, contexts: List[dict[str, Any]]) -> None:
        for ctx in contexts:
            mark = str(ctx.get("beam_mark") or "")
            if mark:
                self._contexts_by_mark[mark] = ctx

    def _index_knowledge_graph(self, graph: dict[str, Any]) -> None:
        nodes = graph.get("nodes", {})
        for group in nodes.values():
            if not isinstance(group, list):
                continue
            for node in group:
                node_id = str(node.get("id", ""))
                if node_id:
                    self._graph_node_ids.add(node_id)
                node_type = str(node.get("type", ""))
                if node_type == "BEAM":
                    mark = str(node.get("beam_mark") or node.get("legacy_id") or "")
                    if mark:
                        self._graph_beam_nodes[mark] = node
                if node_type == "BEAM_SECTION":
                    self._section_ids.add(node_id)
                if node_type == "ENGINEERING_LENGTH":
                    self._length_ids.add(node_id)

    def _index_coordinate_systems(self, systems: List[dict[str, Any]]) -> None:
        for system in systems:
            ecs = str(
                system.get("coordinate_system_id")
                or system.get("engineering_references", {}).get("coordinate_system_id")
                or ""
            )
            if ecs:
                self._ecs_ids.add(ecs)
                self._ecs_ids.add(to_namespaced(ecs))
            mark = str(system.get("beam_id") or system.get("beam_mark") or "")
            if mark:
                self._ecs_ids.add(ecs_id(mark))

    def _index_stationing(self, stationing_rows: List[dict[str, Any]]) -> None:
        for row in stationing_rows:
            mark = str(row.get("beam_id") or row.get("beam_mark") or "")
            if mark:
                self._stationing_marks.add(mark)

    def _index_support_graph(self, support_graph: dict[str, Any]) -> None:
        nodes = support_graph.get("nodes", {})
        for group in ("beams", "supports"):
            for node in nodes.get(group, []):
                node_id = str(node.get("id") or node.get("node_id") or "")
                if node_id:
                    self._support_graph_ids.add(node_id)
                    self._support_graph_ids.add(to_namespaced(node_id))
        for edge in support_graph.get("edges", []):
            for key in ("from", "to"):
                value = str(edge.get(key) or "")
                if value:
                    self._support_graph_ids.add(value)
                    self._support_graph_ids.add(to_namespaced(value, edge.get("beam_mark")))

    @property
    def beam_marks(self) -> Set[str]:
        return set(self._beam_marks)

    def beam_record(self, beam_mark: str) -> dict[str, Any] | None:
        return self._beam_records.get(beam_mark)

    def context(self, beam_mark: str) -> dict[str, Any] | None:
        return self._contexts_by_mark.get(beam_mark)

    def graph_beam_node(self, beam_mark: str) -> dict[str, Any] | None:
        return self._graph_beam_nodes.get(beam_mark)

    def has_beam_mark(self, beam_mark: str) -> bool:
        return beam_mark in self._beam_marks

    def validate_reference(self, ref_id: str, category: str, beam_mark: str = "") -> bool:
        if not ref_id:
            return False
        if category == "beam_geometry":
            return ref_id in self._graph_node_ids and ref_id == beam_id(beam_mark)
        if category == "section":
            return ref_id in self._section_ids or ref_id == section_id(beam_mark)
        if category == "clear_span":
            return beam_mark in self._clear_span_marks and ref_id == f"CLEAR_SPAN::{beam_mark.upper()}"
        if category == "effective_span":
            return (
                beam_mark in self._effective_span_marks
                and ref_id == f"EFF_SPAN::{beam_mark.upper()}"
            )
        if category == "stationing":
            return beam_mark in self._stationing_marks and ref_id == f"STATION::{beam_mark.upper()}"
        if category == "coordinate_system":
            return ref_id in self._ecs_ids or ref_id == ecs_id(beam_mark)
        if category == "length":
            return ref_id in self._length_ids or ref_id == length_id(beam_mark)
        if category == "knowledge_graph":
            return ref_id in self._graph_node_ids
        if category == "support":
            return bool(ref_id)
        return ref_id in self._graph_node_ids
