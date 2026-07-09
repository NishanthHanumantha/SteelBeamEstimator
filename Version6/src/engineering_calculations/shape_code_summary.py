"""Shape code summary — Phase I.7."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, List

from src.engineering_calculations.shape_code_types import CREATED_PHASE, ShapeCodeState


class ShapeCodeSummary:
    """Build project-level shape code determination summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        shape_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
        ]
        shape_code_dist = Counter(
            str(item.get("shape_code"))
            for item in calculated
            if item.get("shape_code")
        )
        shape_family_dist = Counter(
            str(item.get("shape_family"))
            for item in calculated
            if item.get("shape_family")
        )
        role_dist = Counter(
            str(item.get("reinforcement_role"))
            for item in calculated
            if item.get("reinforcement_role")
        )
        diameter_dist = Counter(
            str(item.get("bar_diameter_mm"))
            for item in calculated
            if item.get("bar_diameter_mm") is not None
        )
        beam_dist = Counter(
            str(item.get("beam_id"))
            for item in calculated
            if item.get("beam_id")
        )
        source_dist = Counter(
            str(item.get("shape_rule_source"))
            for item in calculated
            if item.get("shape_rule_source")
        )

        cut_by_shape: dict[str, list[float]] = defaultdict(list)
        for item in calculated:
            shape_code = str(item.get("shape_code", ""))
            cut_length = item.get("cut_length_mm")
            if shape_code and cut_length is not None:
                cut_by_shape[shape_code].append(float(cut_length))

        average_cut_length_by_shape = {
            shape: round(sum(values) / len(values), 2)
            for shape, values in sorted(cut_by_shape.items())
            if values
        }

        return {
            "phase": "Phase I.7",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "determination_count": len(shape_records),
            "results_calculated": len(calculated),
            "deferred_results": sum(
                1
                for item in shape_records
                if item.get("determination_state") == ShapeCodeState.DEFERRED.value
            ),
            "blocked_results": sum(
                1
                for item in shape_records
                if item.get("determination_state") == ShapeCodeState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in shape_records
                if item.get("determination_state") == ShapeCodeState.FAILED.value
            ),
            "shape_code_distribution": dict(shape_code_dist),
            "shape_family_distribution": dict(shape_family_dist),
            "role_distribution": dict(role_dist),
            "diameter_distribution": dict(sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))),
            "beam_distribution": dict(beam_dist),
            "rule_source_distribution": dict(source_dist),
            "average_cut_length_by_shape": average_cut_length_by_shape,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_shape_code": registry.get("results_by_shape_code", {}),
                "results_by_shape_family": registry.get("results_by_shape_family", {}),
                "results_by_role": registry.get("results_by_role", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "metadata_enabled": True,
        }
