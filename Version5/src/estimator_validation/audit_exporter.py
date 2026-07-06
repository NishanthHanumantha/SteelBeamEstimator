"""Estimator audit exporter — Phase QA.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditExporter:
    @staticmethod
    def export_all(output_dir: Path, audit_result: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = {
            "audit_summary.json": audit_result.get("audit_summary"),
            "beam_comparison.json": audit_result.get("beam_comparison"),
            "row_comparison.json": audit_result.get("row_comparison"),
            "cell_comparison.json": audit_result.get("cell_comparison"),
            "missing_items.json": audit_result.get("missing_items"),
            "root_cause_report.json": audit_result.get("root_cause_report"),
            "fix_recommendations.json": audit_result.get("fix_recommendations"),
            "validation_report.json": audit_result.get("validation_report"),
            "engineering_trace_report.json": audit_result.get("engineering_trace_report"),
            "comparison_statistics.json": audit_result.get("comparison_statistics"),
            "workbook_structure_report.json": audit_result.get("workbook_structure_report"),
            "summary_comparison.json": audit_result.get("summary_comparison"),
            "presentation_report.json": audit_result.get("presentation_report"),
            "audit_report.json": audit_result.get("audit_report"),
        }
        for filename, payload in mapping.items():
            if payload is not None:
                path = output_dir / filename
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
