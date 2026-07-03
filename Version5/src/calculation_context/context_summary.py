"""Calculation context summary — Phase I.1."""

from __future__ import annotations

from typing import Any, Dict, List

from src.calculation_context.calculation_context_types import (
    CONTEXT_VERSION,
    MATERIAL_FIELDS,
    SCALAR_GEOMETRY_FIELDS,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    STATUS_PARTIAL,
)


class CalculationContextSummary:
    """Build project-level calculation context summary."""

    @staticmethod
    def build(
        specifications: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        by_status: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}
        completeness_scores: List[float] = []

        geometry_resolved = 0
        material_resolved = 0
        rule_resolved = 0

        for context in contexts:
            status = str(context.get("calculation_status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1
            beam = str(context.get("beam_id", ""))
            if beam:
                by_beam[beam] = by_beam.get(beam, 0) + 1

            completeness_scores.append(
                CalculationContextSummary._completeness_score(context)
            )

            if all(context.get(field) is not None for field in SCALAR_GEOMETRY_FIELDS):
                geometry_resolved += 1
            if all(context.get(field) is not None for field in MATERIAL_FIELDS):
                material_resolved += 1
            if (context.get("development_length_table") or {}).get("reference_id"):
                rule_resolved += 1

        avg_completeness = (
            round(sum(completeness_scores) / len(completeness_scores), 4)
            if completeness_scores
            else 0.0
        )
        missing_count = max(len(specifications) - len(contexts), 0)

        return {
            "phase": "Phase I.1",
            "context_version": CONTEXT_VERSION,
            "total_specifications": len(specifications),
            "contexts_created": len(contexts),
            "contexts_missing": missing_count,
            "context_status": by_status,
            "contexts_by_beam": by_beam,
            "material_coverage": {
                "resolved_count": material_resolved,
                "total_contexts": len(contexts),
                "coverage_rate": round(material_resolved / len(contexts), 4)
                if contexts
                else 0.0,
            },
            "geometry_coverage": {
                "resolved_count": geometry_resolved,
                "total_contexts": len(contexts),
                "coverage_rate": round(geometry_resolved / len(contexts), 4)
                if contexts
                else 0.0,
            },
            "rule_coverage": {
                "resolved_count": rule_resolved,
                "total_contexts": len(contexts),
                "coverage_rate": round(rule_resolved / len(contexts), 4) if contexts else 0.0,
            },
            "average_context_completeness": avg_completeness,
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "context_count": registry.get("context_count", 0),
                "processed_specification_count": len(
                    registry.get("processed_specification_ids", [])
                ),
                "contexts_by_status": registry.get("contexts_by_status", {}),
            },
            "status_breakdown": {
                STATUS_COMPLETE: by_status.get(STATUS_COMPLETE, 0),
                STATUS_PARTIAL: by_status.get(STATUS_PARTIAL, 0),
                STATUS_INCOMPLETE: by_status.get(STATUS_INCOMPLETE, 0),
            },
        }

    @staticmethod
    def _completeness_score(context: dict[str, Any]) -> float:
        tracked_fields = list(SCALAR_GEOMETRY_FIELDS | MATERIAL_FIELDS) + [
            "development_length_table",
            "hook_rule",
            "estimator_rules",
        ]
        populated = 0
        for field in tracked_fields:
            value = context.get(field)
            if field in {"development_length_table", "hook_rule", "estimator_rules"}:
                if isinstance(value, dict) and value.get("reference_id"):
                    populated += 1
            elif value is not None:
                populated += 1
        return round(populated / len(tracked_fields), 4) if tracked_fields else 0.0
