"""Validate Phase F.6 engineering context assembly."""

from __future__ import annotations

import re
from typing import Any, List

from src.framing.engineering_ids import NS_SEPARATOR
from src.framing.engineering_state_machine import VALID_COMPUTATION_STATES
from src.framing.engineering_status import VALID_STATUSES


NAMESPACE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*(?:::[A-Za-z0-9_]+)+$")


class EngineeringContextValidator:
    """Verify F.6 engineering context completeness and integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])
        contexts = model.get("beam_engineering_contexts", [])
        registry = model.get("engineering_context_registry", {})
        project_graph = model.get("project_engineering_graph", {})
        dep_graph = model.get("engineering_dependency_graph", {})

        checks.append(self._check_project_node(project_graph))
        checks.append(self._check_contexts_exist(contexts, beams))
        checks.append(self._check_one_context_per_beam(contexts, beams, registry))
        checks.append(self._check_unique_ids(model))
        checks.append(self._check_namespace_rules(model))
        checks.append(self._check_status_values(model))
        checks.append(self._check_dependency_graph(dep_graph))
        checks.append(self._check_provenance_sources(model))
        checks.append(self._check_knowledge_references(model))
        checks.append(self._check_placeholders(beams))
        checks.append(self._check_no_orphan_project_nodes(project_graph))
        checks.append(self._check_no_reference_paths(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.6",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
                "context_count": len(contexts),
            },
        }

    def _check_project_node(self, project_graph: dict[str, Any]) -> dict[str, Any]:
        root = project_graph.get("root", {})
        nodes = project_graph.get("nodes", [])
        has_project = any(n.get("type") == "PROJECT" for n in nodes)
        ok = root.get("type") == "PROJECT" and has_project
        return {
            "name": "Project Root Node",
            "status": "PASS" if ok else "FAIL",
            "project_id": root.get("id"),
        }

    def _check_contexts_exist(self, contexts: list, beams: list) -> dict[str, Any]:
        ok = len(contexts) == len(beams) and len(contexts) > 0
        return {
            "name": "BeamEngineeringContext Exists",
            "status": "PASS" if ok else "FAIL",
            "contexts": len(contexts),
            "beams": len(beams),
        }

    def _check_one_context_per_beam(
        self,
        contexts: list,
        beams: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        entries = registry.get("entries", [])
        beam_ids = {c.get("beam_id") for c in contexts}
        registry_beams = {e.get("beam_id") for e in entries}
        missing = [b["beam_mark"] for b in beams if not any(
            c.get("beam_mark") == b["beam_mark"] for c in contexts
        )]
        ok = len(missing) == 0 and beam_ids == registry_beams
        return {
            "name": "One Context Per Beam",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_unique_ids(self, model: dict[str, Any]) -> dict[str, Any]:
        graph_duplicates: List[str] = []
        context_duplicates: List[str] = []
        graph_seen: set[str] = set()
        context_seen: set[str] = set()

        graph = model.get("framing_knowledge_graph", {})
        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                nid = node.get("id")
                if nid in graph_seen:
                    graph_duplicates.append(nid)
                graph_seen.add(nid)

        for ctx in model.get("beam_engineering_contexts", []):
            cid = ctx.get("context_id")
            if cid in context_seen:
                context_duplicates.append(cid)
            context_seen.add(cid)

        ok = len(graph_duplicates) == 0 and len(context_duplicates) == 0
        return {
            "name": "Globally Unique IDs",
            "status": "PASS" if ok else "FAIL",
            "graph_duplicates": graph_duplicates[:10],
            "context_duplicates": context_duplicates[:10],
        }

    def _check_namespace_rules(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid: List[str] = []
        for ctx in model.get("beam_engineering_contexts", []):
            for key in ("context_id", "beam_id"):
                val = ctx.get(key, "")
                if NS_SEPARATOR not in val:
                    invalid.append(val)
        for entry in model.get("engineering_context_registry", {}).get("entries", []):
            if NS_SEPARATOR not in entry.get("context_id", ""):
                invalid.append(entry.get("context_id", ""))
        ok = len(invalid) == 0
        return {
            "name": "Namespace Rules Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_status_values(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid: List[str] = []
        for entry in model.get("engineering_status_registry", []):
            if entry.get("status") not in VALID_STATUSES:
                invalid.append(f"registry:{entry.get('field')}")
        for beam in model.get("beams", []):
            for key, val in beam.get("lifecycle", {}).items():
                if not isinstance(val, dict):
                    continue
                st = val.get("status")
                if key in ("reinforcement", "quantities", "boq"):
                    if st not in VALID_COMPUTATION_STATES:
                        invalid.append(f"lifecycle:{beam['beam_mark']}:{key}")
                elif st not in VALID_STATUSES:
                    invalid.append(f"lifecycle:{beam['beam_mark']}:{key}")
        ok = len(invalid) == 0
        return {
            "name": "Status Values Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_dependency_graph(self, dep_graph: dict[str, Any]) -> dict[str, Any]:
        computations = dep_graph.get("computations", [])
        edges = dep_graph.get("edges", [])
        ok = len(computations) > 0 and len(edges) > 0
        return {
            "name": "Dependency Graph Valid",
            "status": "PASS" if ok else "FAIL",
            "computations": len(computations),
            "edges": len(edges),
        }

    def _check_provenance_sources(self, model: dict[str, Any]) -> dict[str, Any]:
        empty: List[str] = []
        for entry in model.get("engineering_status_registry", []):
            if entry.get("status") == "DERIVED" and not entry.get("source"):
                empty.append(f"{entry.get('beam_id')}:{entry.get('field')}")
        for beam in model.get("beams", []):
            gs = beam.get("length_model", {}).get("governing_span", {})
            if gs.get("status") == "DERIVED" and not gs.get("source"):
                empty.append(f"{beam['beam_mark']}:governing_span")
        ok = len(empty) == 0
        return {
            "name": "No Empty Provenance Source",
            "status": "PASS" if ok else "FAIL",
            "empty": empty[:10],
        }

    def _check_knowledge_references(self, model: dict[str, Any]) -> dict[str, Any]:
        missing = 0
        for ctx in model.get("beam_engineering_contexts", []):
            ref = ctx.get("rule_reference") or ctx.get("project_engineering_rules", {})
            if not ref.get("knowledge_id") and not ref.get("rule_id"):
                missing += 1
        graph = model.get("framing_knowledge_graph", {})
        has_path = False
        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                if node.get("properties", {}).get("reference_path"):
                    has_path = True
        ok = missing == 0 and not has_path
        return {
            "name": "Knowledge References Valid",
            "status": "PASS" if ok else "FAIL",
            "missing_knowledge_id": missing,
            "has_reference_path": has_path,
        }

    def _check_placeholders(self, beams: list) -> dict[str, Any]:
        missing = 0
        for beam in beams:
            for key in ("reinforcement", "quantities", "boq"):
                val = beam.get(key, {})
                if val.get("status") not in VALID_COMPUTATION_STATES:
                    missing += 1
        ok = missing == 0
        return {
            "name": "Placeholder Objects Exist",
            "status": "PASS" if ok else "FAIL",
            "invalid": missing,
        }

    def _check_no_orphan_project_nodes(self, project_graph: dict[str, Any]) -> dict[str, Any]:
        nodes = {n["id"] for n in project_graph.get("nodes", [])}
        connected: set[str] = set()
        root_id = project_graph.get("root", {}).get("id")
        connected.add(root_id)
        for edge in project_graph.get("edges", []):
            connected.add(edge.get("from"))
            connected.add(edge.get("to"))
        orphans = [nid for nid in nodes if nid not in connected]
        ok = len(orphans) == 0
        return {
            "name": "No Orphan Project Nodes",
            "status": "PASS" if ok else "FAIL",
            "orphans": orphans[:10],
        }

    def _check_no_reference_paths(self, model: dict[str, Any]) -> dict[str, Any]:
        paths: List[str] = []
        graph = model.get("framing_knowledge_graph", {})
        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                rp = node.get("properties", {}).get("reference_path")
                if rp:
                    paths.append(str(rp))
        ok = len(paths) == 0
        return {
            "name": "No Filesystem Path Coupling",
            "status": "PASS" if ok else "FAIL",
            "paths": paths[:5],
        }
