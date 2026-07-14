"""Reinforcement calculation export helpers — Phase I.2."""

from __future__ import annotations

from typing import Any, List


class ReinforcementExporter:
    """Serialize reinforcement calculation artifacts for pipeline export."""

    @staticmethod
    def export_objects(
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.2",
            "bar_count": len(bars),
            "group_count": len(groups),
            "bars": bars,
            "groups": groups,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_readiness(
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.2.1",
            "bar_count": len(bars),
            "group_count": len(groups),
            "bars": [
                {
                    "bar_id": bar.get("bar_id"),
                    "specification_id": bar.get("specification_id"),
                    "context_id": bar.get("context_id"),
                    "calculation_readiness": bar.get("calculation_readiness", {}),
                }
                for bar in bars
            ],
            "groups": [
                {
                    "group_id": group.get("group_id"),
                    "specification_id": group.get("specification_id"),
                    "context_id": group.get("context_id"),
                    "calculation_readiness": group.get("calculation_readiness", {}),
                }
                for group in groups
            ],
        }
