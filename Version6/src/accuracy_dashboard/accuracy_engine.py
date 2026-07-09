"""Accuracy dashboard engine — Phase QA.ACCURACY.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.accuracy_dashboard.accuracy_builder import AccuracyBuilder
from src.accuracy_dashboard.accuracy_exporter import AccuracyExporter
from src.accuracy_dashboard.accuracy_types import (
    COVERAGE_EXTENSION,
    DIAMETER_SUMMARY_SOURCE,
    OFFICIAL_SUMMARY_EXTENSION,
    DASHBOARD_VERSION,
    MODEL_VERSION,
    PHASE,
    default_paths,
)


class AccuracyEngine:
    """Run read-only engineering coverage dashboard."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        builder = AccuracyBuilder(self._paths)
        artifacts = builder.build()
        excel = artifacts["excel_accuracy"]
        steel = artifacts["steel_accuracy"]
        diameter_coverage = artifacts["diameter_coverage"]
        statistics = artifacts["accuracy_statistics"]
        official_quantity_summary = artifacts["official_quantity_summary"]
        return {
            "phase": PHASE,
            "coverage_extension": COVERAGE_EXTENSION,
            "official_summary_extension": OFFICIAL_SUMMARY_EXTENSION,
            "terminology_refinement": "Phase QA.ACCURACY.1.1",
            "dashboard_version": DASHBOARD_VERSION,
            "model_version": MODEL_VERSION,
            "generated_workbook": str(self._paths["generated_workbook"]),
            "estimator_workbook": str(self._paths["estimator_workbook"]),
            "output_dir": str(self._paths["output_dir"]),
            "engineering_code_modified": False,
            "engineering_pipeline_frozen": True,
            "parser_executed": False,
            "dxf_accessed": False,
            **artifacts,
            "accuracy_dashboard": AccuracyExporter.present_dashboard(excel, steel, diameter_coverage),
            "accuracy_statistics": AccuracyExporter.present_statistics(statistics),
            "diameter_coverage_export": AccuracyExporter.present_diameter_coverage(diameter_coverage),
            "official_quantity_summary_export": official_quantity_summary,
        }
