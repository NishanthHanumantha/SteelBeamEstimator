"""Summary export for graph-instantiated Engineering Objects."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_objects.engineering_object_types import OBJECT_UNKNOWN


class EngineeringObjectSummary:
    """Build project-level engineering object summary."""

    @staticmethod
    def build(
        contexts: List[dict[str, Any]],
        objects: List[dict[str, Any]],
        registry: dict[str, Any],
        graph: dict[str, Any],
        validation: dict[str, Any],
        unknown_threshold: float = 0.15,
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_erc: Dict[str, int] = {}
        confidences: List[float] = []

        for obj in objects:
            otype = str(obj.get("object_type", OBJECT_UNKNOWN))
            by_type[otype] = by_type.get(otype, 0) + 1
            erc = str(obj.get("owner_context_id", ""))
            by_erc[erc] = by_erc.get(erc, 0) + 1
            confidences.append(float(obj.get("confidence", 0.0)))

        total = len(objects)
        unknown_count = by_type.get(OBJECT_UNKNOWN, 0)
        unknown_ratio = unknown_count / total if total else 0.0

        return {
            "phase": "Phase G.5.1",
            "status": "OBJECTS_CREATED",
            "context_count": len(contexts),
            "total_objects": total,
            "objects_by_type": by_type,
            "objects_by_erc": by_erc,
            "average_confidence": round(
                sum(confidences) / len(confidences) if confidences else 0.0, 4
            ),
            "unknown_count": unknown_count,
            "unknown_ratio": round(unknown_ratio, 4),
            "unknown_below_threshold": unknown_ratio <= unknown_threshold,
            "registry_counts": {
                "object_count": registry.get("object_count", 0),
                "erc_registry_count": len(registry.get("erc_registries", [])),
            },
            "graph_statistics": {
                "node_count": graph.get("node_count", 0),
                "edge_count": graph.get("edge_count", 0),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
