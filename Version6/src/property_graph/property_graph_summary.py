"""Property graph summary — Phase G.5.2."""

from __future__ import annotations

from typing import Any, Dict, List

from src.property_graph.property_graph_types import CANDIDATE_UNKNOWN


class PropertyGraphSummary:
    """Build project-level property graph summary."""

    @staticmethod
    def build(
        contexts: List[dict[str, Any]],
        objects: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
        registry: dict[str, Any],
        graph: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_object: Dict[str, int] = {}
        by_erc: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        confidences: List[float] = []

        for cand in candidates:
            ctype = str(cand.get("candidate_type", CANDIDATE_UNKNOWN))
            by_type[ctype] = by_type.get(ctype, 0) + 1
            obj_id = str(cand.get("engineering_object_id", ""))
            by_object[obj_id] = by_object.get(obj_id, 0) + 1
            erc_id = str(cand.get("owner_context_id", ""))
            by_erc[erc_id] = by_erc.get(erc_id, 0) + 1
            entity = str(cand.get("source_entity_id", ""))
            source_counts[entity] = source_counts.get(entity, 0) + 1
            confidences.append(float(cand.get("confidence", 0.0)))

        total_objects = len(objects)
        total_candidates = len(candidates)
        avg_per_object = total_candidates / total_objects if total_objects else 0.0

        top_sources = sorted(
            source_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]

        return {
            "phase": "Phase G.5.2",
            "status": "PROPERTY_GRAPH_CREATED",
            "total_engineering_objects": total_objects,
            "total_candidates": total_candidates,
            "candidates_per_object": by_object,
            "candidates_per_erc": by_erc,
            "candidates_by_type": by_type,
            "average_candidates_per_object": round(avg_per_object, 2),
            "average_confidence": round(
                sum(confidences) / len(confidences) if confidences else 0.0, 4
            ),
            "graph_nodes": graph.get("node_count", 0),
            "graph_edges": graph.get("edge_count", 0),
            "top_candidate_sources": [
                {"source_entity_id": entity, "candidate_count": count}
                for entity, count in top_sources
            ],
            "registry_counts": {
                "candidate_count": registry.get("candidate_count", 0),
                "erc_registry_count": len(registry.get("erc_registries", [])),
            },
            "validation_result": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
