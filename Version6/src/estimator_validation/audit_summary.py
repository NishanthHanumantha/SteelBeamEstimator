"""Estimator audit summary — Phase QA.1."""

from __future__ import annotations

from typing import Any


class AuditSummary:
    @staticmethod
    def build(audit_result: dict[str, Any]) -> dict[str, Any]:
        stats = audit_result.get("comparison_statistics", {})
        return {
            "phase": audit_result.get("phase"),
            "audit_version": audit_result.get("audit_version"),
            "generated_workbook": audit_result.get("generated_workbook"),
            "estimator_workbook": audit_result.get("estimator_workbook"),
            "total_beams_estimator": stats.get("total_beams_estimator", 0),
            "total_beams_generated": stats.get("total_beams_generated", 0),
            "matching_beams": stats.get("matching_beams", 0),
            "missing_beams": stats.get("missing_beams", 0),
            "missing_rows": stats.get("missing_rows", 0),
            "extra_rows": stats.get("extra_rows", 0),
            "different_cells": stats.get("different_cells", 0),
            "engineering_differences": stats.get("engineering_differences", 0),
            "presentation_differences": stats.get("presentation_differences", 0),
            "root_cause_distribution": stats.get("root_cause_distribution", {}),
            "confidence": stats.get("confidence", "MEDIUM"),
            "discrepancy_count": audit_result.get("root_cause_report", {}).get("entry_count", 0),
            "recommendation_count": audit_result.get("fix_recommendations", {}).get("recommendation_count", 0),
            "engineering_pipeline_frozen": True,
            "engineering_code_modified": False,
        }
