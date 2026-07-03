"""Reinforcement calculation summary — Phase I.2."""

from __future__ import annotations

from typing import Any, Dict, List

from src.reinforcement_calculation.reinforcement_types import MODEL_VERSION, STATUS_NORMALIZED


class ReinforcementSummary:
    """Build project-level reinforcement normalization summary."""

    @staticmethod
    def build(
        specifications: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        role_distribution: Dict[str, int] = {}
        diameter_distribution: Dict[str, int] = {}
        steel_grade_distribution: Dict[str, int] = {}
        status_distribution: Dict[str, int] = {}

        for bar in bars:
            role = str(bar.get("role", "UNKNOWN"))
            role_distribution[role] = role_distribution.get(role, 0) + 1
            diameter = bar.get("diameter_mm")
            if diameter is not None:
                key = str(int(float(diameter)))
                diameter_distribution[key] = diameter_distribution.get(key, 0) + 1
            grade = str(bar.get("steel_grade") or "UNKNOWN")
            steel_grade_distribution[grade] = steel_grade_distribution.get(grade, 0) + 1
            status = str(bar.get("status", "UNKNOWN"))
            status_distribution[status] = status_distribution.get(status, 0) + 1

        normalized_count = status_distribution.get(STATUS_NORMALIZED, 0)
        coverage_rate = round(normalized_count / len(bars), 4) if bars else 0.0

        return {
            "phase": "Phase I.2",
            "model_version": MODEL_VERSION,
            "specifications_processed": len(specifications),
            "bars_created": len(bars),
            "groups_created": len(groups),
            "role_distribution": role_distribution,
            "diameter_distribution": diameter_distribution,
            "steel_grade_distribution": steel_grade_distribution,
            "status_distribution": status_distribution,
            "coverage": {
                "normalized_count": normalized_count,
                "total_bars": len(bars),
                "coverage_rate": coverage_rate,
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "bar_count": registry.get("bar_count", 0),
                "group_count": registry.get("group_count", 0),
                "bars_by_role": registry.get("bars_by_role", {}),
                "bars_by_diameter": registry.get("bars_by_diameter", {}),
                "bars_by_beam": registry.get("bars_by_beam", {}),
            },
        }
