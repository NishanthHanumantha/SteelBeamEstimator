"""Assemble the Framing Knowledge Graph from the engineering model."""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from src.framing.beam_relationship_builder import BeamRelationshipBuilder
from src.framing.beam_stationing import BeamStationing
from src.framing.engineering_coordinate_system import EngineeringCoordinateSystemBuilder
from src.framing.engineering_status import infer_status_from_dict
from src.framing.framing_knowledge_graph import (
    EDGE_USES_RULE,
    FramingKnowledgeGraph,
    GraphEdge,
    GraphNode,
    NODE_BEAM,
    NODE_BEAM_SECTION,
    NODE_COLUMN,
    NODE_ENGINEERING_LENGTH,
    NODE_ENGINEERING_RULES,
    NODE_SUPPORT,
    NODE_WALL,
    PROJECT_RULES_ID,
)


class KnowledgeGraphBuilder:
    """Build project-wide framing knowledge graph and enrich beam model."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._enabled = bool(config.get("knowledge_graph", {}).get("enable", True))
        self._ecs_builder = EngineeringCoordinateSystemBuilder()
        self._relationship_builder = BeamRelationshipBuilder(config)
        self._phase_e_path = str(
            config.get("knowledge_graph", {}).get(
                "phase_e_rules_path",
                "data/output/phase_e/general_notes_engineering_rules.json",
            )
        )
        self._stats: Dict[str, int] = {}

    def build_model(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Knowledge graph disabled in config")
            return model

        graph = FramingKnowledgeGraph()
        beams = model.get("beams", [])
        ecs_map = self._ecs_builder.build_all(beams)

        rule_node = GraphNode(
            id=PROJECT_RULES_ID,
            type=NODE_ENGINEERING_RULES,
            properties={"source": "Phase E", "reference_path": self._phase_e_path},
        )
        graph.nodes.append(rule_node)

        stationing_export: List[dict[str, Any]] = []
        ecs_export: List[dict[str, Any]] = []
        status_registry: List[dict[str, Any]] = []

        for beam in beams:
            beam_id = beam["beam_id"]
            section_id = f"SECTION_{beam_id}"
            length_id = f"LM_{beam_id}"
            ecs_id = f"ECS_{beam_id}"

            ecs = ecs_map[beam_id]
            stationing = BeamStationing(ecs).build_station_model()
            ecs_dict = ecs.to_dict()
            ecs_dict["coordinate_system_id"] = ecs_id

            beam["engineering_references"] = {
                "section_id": section_id,
                "length_model_id": length_id,
                "support_model_id": f"SUPPORT_{beam_id}",
                "coordinate_system_id": ecs_id,
                "engineering_rules_id": PROJECT_RULES_ID,
            }
            beam["local_coordinate_system"] = ecs_dict["local_coordinate_system"]
            beam["global_coordinates"] = ecs_dict["global_coordinates"]
            beam["stationing"] = stationing

            stationing_export.append(stationing)
            ecs_export.append(ecs_dict)

            support_refs = self._support_refs(beam)
            graph.nodes.append(
                GraphNode(
                    id=beam_id,
                    type=NODE_BEAM,
                    properties={
                        "beam_mark": beam.get("beam_mark"),
                        "section": section_id,
                        "length_model": length_id,
                        "coordinate_system": ecs_id,
                        "supports": support_refs,
                    },
                )
            )
            graph.nodes.append(
                GraphNode(
                    id=section_id,
                    type=NODE_BEAM_SECTION,
                    properties={"beam": beam_id},
                )
            )
            graph.nodes.append(
                GraphNode(
                    id=length_id,
                    type=NODE_ENGINEERING_LENGTH,
                    properties={"beam": beam_id},
                )
            )
            graph.edges.append(
                GraphEdge(
                    from_id=beam_id,
                    to_id=section_id,
                    relationship="HAS_SECTION",
                    confidence=1.0,
                )
            )
            graph.edges.append(
                GraphEdge(
                    from_id=beam_id,
                    to_id=length_id,
                    relationship="HAS_LENGTH_MODEL",
                    confidence=1.0,
                )
            )
            graph.edges.append(
                GraphEdge(
                    from_id=beam_id,
                    to_id=ecs_id,
                    relationship="HAS_COORDINATE_SYSTEM",
                    confidence=1.0,
                )
            )
            graph.edges.append(
                GraphEdge(
                    from_id=beam_id,
                    to_id=PROJECT_RULES_ID,
                    relationship=EDGE_USES_RULE,
                    confidence=1.0,
                )
            )

            self._register_status(status_registry, beam_id, "governing_span", beam.get("length_model", {}).get("governing_span", {}))
            self._register_status(status_registry, beam_id, "clear_span", beam.get("length_model", {}).get("clear_span", {}))

        self._add_support_nodes(graph, model.get("structural_nodes", []))

        relationships = self._relationship_builder.build(model)
        for edge_data in relationships.get("edges", []):
            graph.edges.append(
                GraphEdge(
                    from_id=edge_data["from"],
                    to_id=edge_data["to"],
                    relationship=edge_data["relationship"],
                    confidence=float(edge_data.get("confidence", 0.0)),
                    properties={k: v for k, v in edge_data.items() if k not in ("from", "to", "relationship", "confidence")},
                )
            )

        stats = graph.statistics()
        self._stats = {
            "beam_nodes": stats["nodes"].get(NODE_BEAM, 0),
            "section_nodes": stats["nodes"].get(NODE_BEAM_SECTION, 0),
            "length_nodes": stats["nodes"].get(NODE_ENGINEERING_LENGTH, 0),
            "support_nodes": stats["nodes"].get(NODE_SUPPORT, 0) + stats["nodes"].get(NODE_COLUMN, 0) + stats["nodes"].get(NODE_WALL, 0),
            "engineering_rule_nodes": stats["nodes"].get(NODE_ENGINEERING_RULES, 0),
            "coordinate_systems": len(ecs_export),
            "station_models": len(stationing_export),
            **{f"rel_{k}": v for k, v in stats.get("relationships", {}).items()},
        }

        model["framing_knowledge_graph"] = graph.to_dict()
        model["knowledge_graph_statistics"] = stats
        model["engineering_coordinate_systems"] = ecs_export
        model["beam_stationing_export"] = stationing_export
        model["beam_relationships"] = relationships
        model["engineering_status_registry"] = status_registry
        model["phase"] = "Phase F.5"
        model["model_version"] = "1.4"
        model["knowledge_graph_summary"] = dict(self._stats)

        logger.info(
            "Knowledge graph — beams={}, sections={}, supports={}, edges={}",
            self._stats.get("beam_nodes", 0),
            self._stats.get("section_nodes", 0),
            self._stats.get("support_nodes", 0),
            graph.to_dict().get("edge_count", 0),
        )
        return model

    def _add_support_nodes(self, graph: FramingKnowledgeGraph, nodes: List[dict[str, Any]]) -> None:
        seen: set[str] = set()
        for node in nodes:
            node_id = str(node.get("id", ""))
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            node_type = str(node.get("type", "SUPPORT")).upper()
            if node_type == "COLUMN":
                gtype = NODE_COLUMN
            elif node_type == "WALL":
                gtype = NODE_WALL
            elif node_type == "BEAM":
                continue
            else:
                gtype = NODE_SUPPORT
            graph.nodes.append(
                GraphNode(
                    id=node_id,
                    type=gtype,
                    properties={
                        "location": node.get("location"),
                        "connected_beams": node.get("connected_beams", []),
                    },
                )
            )

    @staticmethod
    def _support_refs(beam: dict[str, Any]) -> List[str]:
        refs: List[str] = []
        supports = beam.get("supports", {})
        for end in ("left", "right"):
            sid = supports.get(end, {}).get("id")
            if sid:
                refs.append(str(sid))
        return refs

    @staticmethod
    def _register_status(
        registry: List[dict[str, Any]],
        beam_id: str,
        field: str,
        data: dict[str, Any],
    ) -> None:
        if not data:
            return
        registry.append(
            {
                "beam_id": beam_id,
                "field": field,
                "value": data.get("value"),
                "status": infer_status_from_dict(data),
                "confidence": data.get("confidence", 0.0),
                "source": data.get("source", ""),
            }
        )

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
