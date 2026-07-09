"""Calculation result export helpers — Phase I.2.2."""

from __future__ import annotations

from typing import Any, List


class CalculationResultExporter:
    """Serialize calculation result artifacts for pipeline export."""

    @staticmethod
    def export_results(results: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.2.2",
            "result_count": len(results),
            "results": results,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry
