"""Interpretation audit exporter — Phase QA.3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class InterpretationExporter:
    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = {
            "drawing_interpretation.json": result.get("drawing_interpretation"),
            "estimator_interpretation.json": result.get("estimator_interpretation"),
            "pipeline_interpretation.json": result.get("pipeline_interpretation"),
            "interpretation_matching.json": result.get("interpretation_matching"),
            "engineering_concepts.json": result.get("engineering_concepts"),
            "engineering_decisions.json": result.get("engineering_decisions"),
            "length_interpretation_report.json": result.get("length_interpretation_report"),
            "interpretation_trace.json": result.get("interpretation_trace"),
            "root_cause_matrix.json": result.get("root_cause_matrix"),
            "interpretation_statistics.json": result.get("interpretation_statistics"),
            "interpretation_validation.json": result.get("interpretation_validation"),
            "interpretation_summary.json": result.get("interpretation_summary"),
            "interpretation_report.json": result.get("interpretation_report"),
        }
        for filename, payload in mapping.items():
            if payload is not None:
                (output_dir / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")
