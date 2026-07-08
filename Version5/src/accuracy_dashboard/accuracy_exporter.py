"""Accuracy dashboard exporter — Phase QA.ACCURACY.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from src.accuracy_dashboard.accuracy_types import DASHBOARD_TITLE, DIAMETER_SUMMARY_SOURCE


class AccuracyExporter:
    @staticmethod
    def present_dashboard(
        excel: dict[str, Any],
        steel: dict[str, Any],
        diameter_coverage: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "dashboard_title": DASHBOARD_TITLE,
            "schedule_coverage": {
                "beam_coverage_percent": excel.get("beam_coverage_percent"),
                "beam_coverage": excel.get("beam_coverage"),
                "schedule_coverage_percent": excel.get("row_coverage_percent"),
                "schedule_coverage": excel.get("row_coverage"),
                "missing_beams": excel.get("missing_beams"),
                "missing_rows": excel.get("missing_rows"),
                "missing_values": excel.get("missing_values"),
            },
            "steel_quantity_coverage": {
                "generated_steel_kg": steel.get("generated_steel_kg"),
                "estimator_steel_kg": steel.get("estimator_steel_kg"),
                "coverage_percent": steel.get("accuracy_percent"),
                "difference_kg": steel.get("difference_kg"),
                "difference_percent": steel.get("difference_percent"),
                "quantity_source": steel.get("quantity_source", DIAMETER_SUMMARY_SOURCE),
            },
            "diameter_steel_coverage": {
                "summary": diameter_coverage.get("summary", {}),
                "diameters": diameter_coverage.get("diameters", []),
            },
        }

    @staticmethod
    def present_diameter_coverage(diameter_coverage: dict[str, Any]) -> dict[str, Any]:
        return {"diameters": diameter_coverage.get("diameters", [])}

    @staticmethod
    def present_statistics(statistics: dict[str, Any]) -> dict[str, Any]:
        presented = dict(statistics)
        if "steel_accuracy_percent" in presented:
            presented["steel_quantity_coverage_percent"] = presented.pop("steel_accuracy_percent")
        presented["schedule_coverage_percent"] = presented.get("row_coverage_percent")
        return presented

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = {
            "accuracy_dashboard.json": result.get("accuracy_dashboard"),
            "management_summary.json": result.get("management_summary"),
            "accuracy_statistics.json": result.get("accuracy_statistics"),
            "accuracy_validation.json": result.get("validation_report"),
            "accuracy_report.json": result.get("accuracy_report"),
            "improvement_tracker.json": result.get("improvement_tracker"),
            "diameter_coverage.json": result.get("diameter_coverage_export"),
            "official_quantity_summary.json": result.get("official_quantity_summary_export"),
        }
        for filename, payload in mapping.items():
            if payload is not None:
                path = output_dir / filename
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def build_improvement_tracker(
        output_dir: Path,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        tracker_path = output_dir / "improvement_tracker.json"
        existing_entries: List[dict[str, Any]] = []
        if tracker_path.exists():
            try:
                existing_payload = json.loads(tracker_path.read_text(encoding="utf-8"))
                existing_entries = list(existing_payload.get("entries") or [])
            except (json.JSONDecodeError, OSError):
                existing_entries = []

        excel = result.get("excel_accuracy", {})
        steel = result.get("steel_accuracy", {})
        diameter_coverage = result.get("diameter_coverage", {})
        diameter_map = {
            str(entry.get("diameter_mm")): entry.get("coverage_percent")
            for entry in diameter_coverage.get("diameters", [])
        }
        official = result.get("official_quantity_summary", {})
        entry = {
            "version": result.get("model_version"),
            "timestamp": result.get("run_timestamp"),
            "beam_coverage_percent": excel.get("beam_coverage_percent"),
            "schedule_coverage_percent": excel.get("row_coverage_percent"),
            "steel_quantity_coverage_percent": steel.get("accuracy_percent"),
            "missing_beams": excel.get("missing_beams"),
            "missing_rows": excel.get("missing_rows"),
            "missing_values": excel.get("missing_values"),
            "generated_steel_kg": steel.get("generated_steel_kg"),
            "estimator_steel_kg": steel.get("estimator_steel_kg"),
            "official_total_steel_estimator": official.get("estimator", {}).get("total"),
            "official_total_steel_generated": official.get("generated", {}).get("total"),
            "diameter_summary_source": official.get("diameter_summary_source", DIAMETER_SUMMARY_SOURCE),
            "diameter_coverage": diameter_map,
        }

        if existing_entries and existing_entries[-1].get("version") == entry.get("version"):
            existing_entries[-1] = entry
        else:
            existing_entries.append(entry)

        return {
            "description": "Accumulated coverage metrics across engineering improvement versions",
            "latest_version": entry.get("version"),
            "entry_count": len(existing_entries),
            "entries": existing_entries,
        }
