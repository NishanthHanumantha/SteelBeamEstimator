"""Calculation dependency summary — Phase I.4.6."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.calculation_dependency.dependency_types import (
    CREATED_PHASE,
    PHASE_LABEL,
)


class CalculationDependencySummary:
    """Build project-level dependency graph summary."""

    @staticmethod
    def build(
        graph: dict[str, Any],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        nodes = graph.get("nodes", {})
        return {
            "phase": PHASE_LABEL,
            "framework_phase": CREATED_PHASE,
            "node_count": len(nodes),
            "ordered_categories": graph.get("ordered_categories", []),
            "metadata_only": graph.get("metadata_only", True),
            "category_sequences": {
                category: node.get("sequence")
                for category, node in sorted(
                    nodes.items(),
                    key=lambda item: int(item[1].get("sequence", 0)),
                )
            },
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "node_count": registry.get("node_count", 0),
                "graph_id": registry.get("graph_id"),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
