"""Interpretation audit summary — Phase QA.3."""

from __future__ import annotations

from typing import Any


class InterpretationSummary:
    @staticmethod
    def build(result: dict[str, Any]) -> dict[str, Any]:
        stats = result.get("interpretation_statistics", {})
        matrix = result.get("root_cause_matrix", {})
        return {
            "phase": "Phase QA.3",
            "interpretation_version": result.get("interpretation_version"),
            "estimator_workbook": result.get("estimator_workbook"),
            "generated_workbook": result.get("generated_workbook"),
            "beam_count": len(result.get("beam_marks", [])),
            "concept_count": stats.get("concept_count", 0),
            "interpretation_difference_count": stats.get("interpretation_difference_count", 0),
            "engineering_decision_count": stats.get("engineering_decision_count", 0),
            "trace_count": stats.get("trace_count", 0),
            "classification_distribution": stats.get("classification_distribution", {}),
            "root_cause_distribution": stats.get("root_cause_distribution", {}),
            "unknown_pct": matrix.get("unknown_pct", 0),
            "engineering_pipeline_frozen": True,
            "engineering_code_modified": False,
            "parser_executed": False,
            "validates_engineering_interpretation": True,
            "validates_worksheet_structure": False,
            "confidence": stats.get("confidence", "HIGH"),
        }
