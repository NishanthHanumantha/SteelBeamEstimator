"""Build BeamEngineeringContext and enrich model for Phase F.6."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.framing.beam_engineering_context import BeamEngineeringContext
from src.framing.engineering_dependency_graph import EngineeringDependencyGraph
from src.framing.engineering_ids import (
    GENERAL_NOTES_ID,
    KNOWLEDGE_PROJECT_DEFAULTS,
    RULE_ESTIMATOR,
    RULE_PROJECT,
    SERVICES_ID,
    alias_map_for_beam,
    beam_id,
    column_id,
    context_id,
    ecs_id,
    length_id,
    legacy_project_rules_id,
    project_id,
    section_id,
    slug_from_project_name,
    support_beam_id,
    to_namespaced,
    wall_id,
)
from src.framing.engineering_state_machine import EngineeringStateMachine
from src.framing.provenance_normalizer import (
    normalize_beam_engineering_values,
    normalize_status_registry_entry,
)
from src.framing.framing_knowledge_graph import PROJECT_RULES_ID


class EngineeringContextBuilder:
    """Assemble engineering context, project graph, and namespaced IDs."""

    def __init__(self, config: dict[str, Any], output_root: Optional[Path] = None) -> None:
        ec = config.get("engineering_context", {})
        self._enabled = bool(ec.get("enable", True))
        self._output_root = Path(output_root or "data/output")
        self._phase_e_dir = self._output_root / "phase_e"
        self._knowledge_version = str(ec.get("knowledge_version", "1.0"))
        self._stats: Dict[str, int] = {}
        self._project_slug = slug_from_project_name("Sobha Galera Clubhouse")

    def build_model(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Engineering context disabled in config")
            return model

        self._load_project_metadata()
        self._normalize_all_beams(model)
        self._enrich_graph(model)
        self._add_lifecycle(model)
        contexts = self._build_contexts(model)
        registry = self._build_context_registry(contexts)
        dep_graph = EngineeringDependencyGraph().build()
        dep_registry = EngineeringDependencyGraph().build_registry()
        project_graph = self._build_project_graph(model, contexts)

        model["beam_engineering_contexts"] = [c.to_dict() for c in contexts]
        model["engineering_context_registry"] = registry
        model["engineering_dependency_graph"] = dep_graph
        model["engineering_dependency_registry"] = dep_registry
        model["project_engineering_graph"] = project_graph
        model["engineering_context_summary"] = dict(self._stats)
        model["phase"] = "Phase F.6"
        model["model_version"] = "1.5"

        logger.info(
            "Engineering context — project={}, contexts={}, dependencies={}",
            project_id(self._project_slug),
            len(contexts),
            dep_graph.get("computation_count", 0),
        )
        return model

    def _load_project_metadata(self) -> None:
        meta_path = self._phase_e_dir / "project_metadata.json"
        rules_path = self._phase_e_dir / "general_notes_engineering_rules.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            name = (
                meta.get("project_information", {})
                .get("project_name", {})
                .get("value", "Sobha Galera Clubhouse")
            )
            self._project_slug = slug_from_project_name(name)
        if rules_path.exists():
            rules = json.loads(rules_path.read_text(encoding="utf-8"))
            self._knowledge_version = str(
                rules.get("knowledge_version", rules.get("version", self._knowledge_version))
            )

    def _normalize_all_beams(self, model: dict[str, Any]) -> None:
        registry = model.get("engineering_status_registry", [])
        beam_by_mark = {b["beam_mark"]: b for b in model.get("beams", [])}
        for beam in model.get("beams", []):
            normalize_beam_engineering_values(beam)
        normalized_registry: List[dict[str, Any]] = []
        for entry in registry:
            field = str(entry.get("field", ""))
            legacy_mark = entry.get("beam_id", "")
            beam = beam_by_mark.get(legacy_mark)
            enrich = {}
            if beam and field in beam.get("length_model", {}):
                enrich = dict(beam["length_model"][field])
            normalized_registry.append(
                normalize_status_registry_entry({**entry, **enrich})
            )
        model["engineering_status_registry"] = normalized_registry

    def _enrich_graph(self, model: dict[str, Any]) -> None:
        graph = model.get("framing_knowledge_graph", {})
        id_map: Dict[str, str] = {}

        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                legacy = node.get("id", "")
                ns = to_namespaced(legacy)
                id_map[legacy] = ns
                node["legacy_id"] = legacy
                node["id"] = ns

        for edge in graph.get("edges", []):
            edge["from"] = id_map.get(edge.get("from"), edge.get("from"))
            edge["to"] = id_map.get(edge.get("to"), edge.get("to"))
            if edge.get("from_id"):
                edge["from_id"] = id_map.get(edge["from_id"], edge["from_id"])
            if edge.get("to_id"):
                edge["to_id"] = id_map.get(edge["to_id"], edge["to_id"])

        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                for prop_key in ("section", "length_model", "coordinate_system", "beam"):
                    if prop_key in node.get("properties", {}):
                        val = node["properties"][prop_key]
                        node["properties"][prop_key] = id_map.get(val, val)
                    if prop_key in node:
                        node[prop_key] = id_map.get(node[prop_key], node[prop_key])
                supports = node.get("properties", {}).get("supports", [])
                if supports:
                    node["properties"]["supports"] = [
                        id_map.get(s, to_namespaced(s)) for s in supports
                    ]

        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                if node.get("type") == "ENGINEERING_RULES":
                    props = node.setdefault("properties", {})
                    props.pop("reference_path", None)
                    props["knowledge_id"] = RULE_PROJECT
                    props["version"] = self._knowledge_version
                    props["knowledge_version"] = self._knowledge_version
                    props["legacy_knowledge_id"] = legacy_project_rules_id()

        for beam in model.get("beams", []):
            mark = beam["beam_mark"]
            aliases = alias_map_for_beam(mark)
            beam["beam_id_ns"] = aliases["beam_id"]
            beam["legacy_beam_id"] = mark
            refs = beam.setdefault("engineering_references", {})
            refs.update(
                {
                    "section_id": aliases["section_id"],
                    "length_model_id": aliases["length_id"],
                    "coordinate_system_id": aliases["ecs_id"],
                    "engineering_rules_id": RULE_PROJECT,
                    "context_id": aliases["context_id"],
                    "support_model_id": support_beam_id(mark),
                    "legacy_section_id": aliases["legacy_section_id"],
                    "legacy_length_model_id": aliases["legacy_length_id"],
                    "legacy_coordinate_system_id": aliases["legacy_ecs_id"],
                    "legacy_engineering_rules_id": PROJECT_RULES_ID,
                }
            )

        rels = model.get("beam_relationships", {})
        for edge in rels.get("edges", []):
            legacy_from = edge.get("from")
            legacy_to = edge.get("to")
            edge["from"] = id_map.get(legacy_from, to_namespaced(legacy_from or ""))
            edge["to"] = id_map.get(legacy_to, to_namespaced(legacy_to or ""))
            edge["legacy_from"] = legacy_from
            edge["legacy_to"] = legacy_to

        for entry in model.get("engineering_status_registry", []):
            bid = entry.get("beam_id", "")
            entry["beam_id"] = id_map.get(bid, beam_id(bid) if bid.startswith("B") else bid)
            entry["legacy_beam_id"] = bid

        model["framing_knowledge_graph"] = graph
        model["project_id"] = project_id(self._project_slug)

    def _add_lifecycle(self, model: dict[str, Any]) -> None:
        placeholder = EngineeringStateMachine.placeholder()
        for beam in model.get("beams", []):
            beam["lifecycle"] = {
                "geometry": {"status": "KNOWN"},
                "section": {"status": "KNOWN"},
                "supports": {"status": "KNOWN"},
                "length_model": {"status": "KNOWN"},
                "coordinate_system": {"status": "KNOWN"},
                "relationships": {"status": "KNOWN"},
                "engineering_context": {"status": "KNOWN"},
                "reinforcement": dict(placeholder),
                "quantities": dict(placeholder),
                "boq": dict(placeholder),
            }
            beam["reinforcement"] = dict(placeholder)
            beam["quantities"] = dict(placeholder)
            beam["boq"] = dict(placeholder)

    def _load_phase_e_json(self, filename: str) -> dict[str, Any]:
        path = self._phase_e_dir / filename
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_contexts(self, model: dict[str, Any]) -> List[BeamEngineeringContext]:
        graph = model.get("framing_knowledge_graph", {})
        nodes_by_id: Dict[str, dict[str, Any]] = {}
        for node_list in graph.get("nodes", {}).values():
            for node in node_list:
                nodes_by_id[node["id"]] = node

        rules_ref = {
            "rule_id": RULE_PROJECT,
            "knowledge_id": RULE_PROJECT,
            "version": self._knowledge_version,
            "knowledge_version": self._knowledge_version,
            "legacy_knowledge_id": legacy_project_rules_id(),
        }
        estimator_ref = {
            "rule_id": RULE_ESTIMATOR,
            "knowledge_id": RULE_ESTIMATOR,
            "version": self._knowledge_version,
        }
        defaults_ref = {
            "knowledge_id": KNOWLEDGE_PROJECT_DEFAULTS,
            "version": self._knowledge_version,
        }
        pid = project_id(self._project_slug)
        rel_edges = model.get("beam_relationships", {}).get("edges", [])

        contexts: List[BeamEngineeringContext] = []
        for beam in model.get("beams", []):
            mark = beam["beam_mark"]
            ns_beam = beam_id(mark)
            beam_rels = [
                e for e in rel_edges
                if e.get("from") == ns_beam or e.get("to") == ns_beam
            ]
            ecs = {
                "coordinate_system_id": ecs_id(mark),
                "local_coordinate_system": beam.get("local_coordinate_system", {}),
                "global_coordinates": beam.get("global_coordinates", {}),
            }
            stationing = beam.get("stationing", {})
            station_api = {
                "beam_id": ns_beam,
                "span_mm": stationing.get("span_mm"),
                "origin": ecs.get("global_coordinates", {}).get("origin"),
                "origin_label": ecs.get("local_coordinate_system", {}).get("origin"),
                "unit_vector": ecs.get("local_coordinate_system", {}).get("unit_vector"),
                "stations": stationing.get("stations", []),
                "methods": [
                    "station_to_global",
                    "global_to_station",
                    "station_fraction",
                ],
            }
            ctx = BeamEngineeringContext(
                context_id=context_id(mark),
                beam_id=ns_beam,
                beam_mark=mark,
                beam_section=beam.get("beam_section", {}),
                engineering_length_model=beam.get("length_model", {}),
                engineering_coordinate_system=ecs,
                support_model=beam.get("supports", {}),
                knowledge_graph_node=nodes_by_id.get(ns_beam, {}),
                station_api=station_api,
                relationships=beam_rels,
                project_id=pid,
                floor_id="",
                rule_reference=rules_ref,
                estimator_rules_reference=estimator_ref,
                project_defaults_reference=defaults_ref,
                services=SERVICES_ID,
                metadata={
                    "project_id": pid,
                    "phase": "Phase F.6",
                    "knowledge_references": [
                        RULE_PROJECT,
                        RULE_ESTIMATOR,
                        KNOWLEDGE_PROJECT_DEFAULTS,
                        GENERAL_NOTES_ID,
                    ],
                },
                legacy_ids=alias_map_for_beam(mark),
                status="READY",
            )
            beam["engineering_context"] = {
                "context_id": ctx.context_id,
                "status": ctx.status,
            }
            contexts.append(ctx)

        self._stats = {
            "beam_contexts": len(contexts),
            "knowledge_references": len(contexts),
            "placeholder_reinforcement": len(contexts),
            "placeholder_quantities": len(contexts),
            "placeholder_boq": len(contexts),
        }
        return contexts

    def _build_context_registry(self, contexts: List[BeamEngineeringContext]) -> dict[str, Any]:
        entries = [
            {
                "context_id": ctx.context_id,
                "beam_id": ctx.beam_id,
                "beam_mark": ctx.beam_mark,
                "status": ctx.status,
                "legacy_ids": ctx.legacy_ids,
            }
            for ctx in contexts
        ]
        return {
            "phase": "Phase F.6",
            "context_count": len(entries),
            "entries": entries,
        }

    def _build_project_graph(
        self,
        model: dict[str, Any],
        contexts: List[BeamEngineeringContext],
    ) -> dict[str, Any]:
        pid = project_id(self._project_slug)
        beams = model.get("beams", [])
        graph_nodes: List[dict[str, Any]] = [
            {
                "id": pid,
                "type": "PROJECT",
                "name": self._project_slug.replace("_", " "),
                "children": [
                    GENERAL_NOTES_ID,
                    RULE_PROJECT,
                    "BEAMS",
                    "SUPPORTS",
                    "SECTIONS",
                    "LENGTHS",
                    "COORDINATE_SYSTEMS",
                ],
            },
            {
                "id": GENERAL_NOTES_ID,
                "type": "GENERAL_NOTES",
                "parent": pid,
                "knowledge_id": GENERAL_NOTES_ID,
            },
            {
                "id": RULE_PROJECT,
                "type": "PROJECT_RULES",
                "parent": pid,
                "knowledge_id": RULE_PROJECT,
                "version": self._knowledge_version,
            },
        ]

        beam_ids = []
        support_ids: set[str] = set()
        section_ids = []
        length_ids = []
        ecs_ids = []
        ctx_ids = []

        for beam in beams:
            mark = beam["beam_mark"]
            bid = beam_id(mark)
            beam_ids.append(bid)
            section_ids.append(section_id(mark))
            length_ids.append(length_id(mark))
            ecs_ids.append(ecs_id(mark))
            ctx_ids.append(context_id(mark))
            for end in ("left", "right"):
                sid = beam.get("supports", {}).get(end, {}).get("id")
                if sid:
                    support_ids.add(to_namespaced(sid))

        graph_nodes.append({"id": "BEAMS", "type": "BEAM_COLLECTION", "parent": pid, "member_ids": beam_ids})
        graph_nodes.append(
            {
                "id": "SUPPORTS",
                "type": "SUPPORT_COLLECTION",
                "parent": pid,
                "member_ids": sorted(support_ids),
            }
        )
        graph_nodes.append(
            {"id": "SECTIONS", "type": "SECTION_COLLECTION", "parent": pid, "member_ids": section_ids}
        )
        graph_nodes.append(
            {"id": "LENGTHS", "type": "LENGTH_COLLECTION", "parent": pid, "member_ids": length_ids}
        )
        graph_nodes.append(
            {
                "id": "COORDINATE_SYSTEMS",
                "type": "ECS_COLLECTION",
                "parent": pid,
                "member_ids": ecs_ids,
            }
        )
        graph_nodes.append(
            {
                "id": "CONTEXTS",
                "type": "CONTEXT_COLLECTION",
                "parent": pid,
                "member_ids": ctx_ids,
            }
        )

        for ctx in contexts:
            graph_nodes.append(
                {
                    "id": ctx.context_id,
                    "type": "ENGINEERING_CONTEXT",
                    "parent": "CONTEXTS",
                    "beam_id": ctx.beam_id,
                }
            )

        edges: List[dict[str, Any]] = [
            {"from": pid, "to": GENERAL_NOTES_ID, "relationship": "HAS_GENERAL_NOTES"},
            {"from": pid, "to": RULE_PROJECT, "relationship": "HAS_RULES"},
            {"from": pid, "to": "BEAMS", "relationship": "HAS_BEAMS"},
            {"from": pid, "to": "SUPPORTS", "relationship": "HAS_SUPPORTS"},
            {"from": pid, "to": "SECTIONS", "relationship": "HAS_SECTIONS"},
            {"from": pid, "to": "LENGTHS", "relationship": "HAS_LENGTHS"},
            {"from": pid, "to": "COORDINATE_SYSTEMS", "relationship": "HAS_COORDINATE_SYSTEMS"},
            {"from": pid, "to": "CONTEXTS", "relationship": "HAS_CONTEXTS"},
        ]
        for bid in beam_ids:
            edges.append({"from": "BEAMS", "to": bid, "relationship": "MEMBER"})
        for cid in ctx_ids:
            edges.append({"from": "CONTEXTS", "to": cid, "relationship": "MEMBER"})

        self._stats["project_nodes"] = len(graph_nodes)
        return {
            "phase": "Phase F.6",
            "project_id": pid,
            "root": {"id": pid, "type": "PROJECT"},
            "node_count": len(graph_nodes),
            "edge_count": len(edges),
            "nodes": graph_nodes,
            "edges": edges,
        }

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
