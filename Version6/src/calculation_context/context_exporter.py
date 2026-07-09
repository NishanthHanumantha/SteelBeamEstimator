"""Calculation context export helpers — Phase I.1."""

from __future__ import annotations

from typing import Any, List


class CalculationContextExporter:
    """Serialize calculation context artifacts for pipeline export."""

    @staticmethod
    def export_contexts(contexts: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.1",
            "context_count": len(contexts),
            "contexts": contexts,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry
