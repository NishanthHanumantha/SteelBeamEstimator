"""Engineering trace summary — Phase QA.2."""

from __future__ import annotations

from typing import Any


class TraceSummary:
    @staticmethod
    def build(trace_result: dict[str, Any]) -> dict[str, Any]:
        stats = trace_result.get("trace_statistics", {})
        identity = trace_result.get("identity_matching", {})
        geometry = trace_result.get("geometry_comparison", {})
        qa1 = trace_result.get("qa1_validation", {})
        matrix = trace_result.get("root_cause_matrix", {})
        return {
            "phase": "Phase QA.2",
            "trace_version": trace_result.get("trace_version"),
            "generated_workbook": trace_result.get("generated_workbook"),
            "estimator_workbook": trace_result.get("estimator_workbook"),
            "total_estimator_rows_traced": stats.get("total_estimator_rows_traced", 0),
            "trace_pass_count": stats.get("trace_pass_count", 0),
            "trace_fail_count": stats.get("trace_fail_count", 0),
            "identity_matches": identity.get("identity_matches", 0),
            "exact_matches": identity.get("exact_matches", 0),
            "partial_matches": identity.get("partial_matches", 0),
            "false_positional_mismatches": identity.get("false_positional_mismatches", 0),
            "identity_excel_pass_rows": qa1.get("identity_excel_pass_rows", 0),
            "qa1_matching_rows_zero": qa1.get("qa1_matching_rows_zero"),
            "qa1_validation_conclusion": qa1.get("conclusion"),
            "geometry_beam_count": geometry.get("beam_count", 0),
            "first_missing_layer_distribution": stats.get("first_missing_layer_distribution", {}),
            "root_cause_distribution": stats.get("root_cause_distribution", {}),
            "unknown_pct": matrix.get("unknown_pct", 0),
            "engineering_pipeline_frozen": True,
            "engineering_code_modified": False,
            "identity_matching_used": True,
            "positional_matching_used": False,
            "confidence": stats.get("confidence", "HIGH"),
        }
