"""Validate Phase F.5 knowledge graph and coordinate systems."""

from __future__ import annotations

from typing import Any, List

from src.framing.engineering_status import VALID_STATUSES
from src.framing.framing_knowledge_graph import PROJECT_RULES_ID


class EngineeringGraphValidator:
    """Verify knowledge graph completeness and reference integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])
        graph = model.get("framing_knowledge_graph", {})
        nodes_by_type = graph.get("nodes", {})

        checks.append(self._check_beam_graph_nodes(beams, nodes_by_type))
        checks.append(self._check_coordinate_systems(beams))
        checks.append(self._check_stationing(beams))
        checks.append(self._check_references(beams))
        checks.append(self._check_section_length_refs(beams, nodes_by_type))
        checks.append(self._check_engineering_rules(graph, nodes_by_type))
        checks.append(self._check_status_registry(model.get("engineering_status_registry", [])))
        checks.append(self._check_orphan_nodes(graph))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.5",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
            },
        }

    def _check_beam_graph_nodes(self, beams: list, nodes_by_type: dict) -> dict[str, Any]:
        beam_nodes = {n["id"] for n in nodes_by_type.get("BEAM", [])}
        missing = [b["beam_id"] for b in beams if b["beam_id"] not in beam_nodes]
        ok = len(missing) == 0
        return {
            "name": "Beam Graph Nodes",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_coordinate_systems(self, beams: list) -> dict[str, Any]:
        with_ecs = sum(1 for b in beams if b.get("local_coordinate_system"))
        ok = with_ecs == len(beams) and with_ecs > 0
        return {
            "name": "Coordinate Systems",
            "status": "PASS" if ok else "FAIL",
            "with_ecs": with_ecs,
            "total": len(beams),
        }

    def _check_stationing(self, beams: list) -> dict[str, Any]:
        with_st = sum(1 for b in beams if b.get("stationing", {}).get("stations"))
        ok = with_st == len(beams) and with_st > 0
        return {
            "name": "Station Models",
            "status": "PASS" if ok else "FAIL",
            "with_stationing": with_st,
        }

    def _check_references(self, beams: list) -> dict[str, Any]:
        required = ("section_id", "length_model_id", "coordinate_system_id", "engineering_rules_id")
        missing = 0
        for beam in beams:
            refs = beam.get("engineering_references", {})
            for key in required:
                if not refs.get(key):
                    missing += 1
        ok = missing == 0
        return {
            "name": "Engineering References",
            "status": "PASS" if ok else "FAIL",
            "missing_fields": missing,
        }

    def _check_section_length_refs(self, beams: list, nodes_by_type: dict) -> dict[str, Any]:
        section_ids = {n["id"] for n in nodes_by_type.get("BEAM_SECTION", [])}
        length_ids = {n["id"] for n in nodes_by_type.get("ENGINEERING_LENGTH", [])}
        invalid = 0
        for beam in beams:
            refs = beam.get("engineering_references", {})
            if refs.get("section_id") not in section_ids:
                invalid += 1
            if refs.get("length_model_id") not in length_ids:
                invalid += 1
        ok = invalid == 0
        return {
            "name": "Section/Length References",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_engineering_rules(self, graph: dict, nodes_by_type: dict) -> dict[str, Any]:
        rule_nodes = nodes_by_type.get("ENGINEERING_RULES", [])
        has_rule = any(n.get("id") == PROJECT_RULES_ID for n in rule_nodes)
        uses_rule_edges = sum(
            1 for e in graph.get("edges", []) if e.get("relationship") == "USES_RULE"
        )
        ok = has_rule and uses_rule_edges >= 1
        return {
            "name": "Engineering Rule Links",
            "status": "PASS" if ok else "FAIL",
            "rule_nodes": len(rule_nodes),
            "uses_rule_edges": uses_rule_edges,
        }

    def _check_status_registry(self, registry: list) -> dict[str, Any]:
        invalid = sum(1 for item in registry if item.get("status") not in VALID_STATUSES)
        ok = invalid == 0
        return {
            "name": "EngineeringStatus Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_orphan_nodes(self, graph: dict) -> dict[str, Any]:
        node_ids = set()
        referenced: set[str] = set()
        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                nid = node.get("id")
                if nid:
                    node_ids.add(nid)
                if node.get("type") == "BEAM":
                    for key in ("section", "length_model", "coordinate_system"):
                        ref = node.get(key)
                        if ref:
                            referenced.add(str(ref))
        connected = set()
        for edge in graph.get("edges", []):
            connected.add(edge.get("from"))
            connected.add(edge.get("to"))
        orphans = []
        for nid in node_ids:
            if nid in connected or nid in referenced:
                continue
            node_type = next(
                (
                    n.get("type")
                    for nl in graph.get("nodes", {}).values()
                    for n in nl
                    if n.get("id") == nid
                ),
                None,
            )
            if node_type in ("BEAM", "BEAM_SECTION", "ENGINEERING_LENGTH", "ENGINEERING_RULES"):
                orphans.append(nid)
        ok = len(orphans) == 0
        return {
            "name": "Orphan Nodes",
            "status": "PASS" if ok else "FAIL",
            "orphan_count": len(orphans),
            "orphans": orphans[:10],
        }
