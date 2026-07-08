"""Export recovery impact validation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_recovery_validation.validation_collector import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "baseline_snapshot.json",
    "pipeline_delta.json",
    "beam_delta_analysis.json",
    "reinforcement_delta_analysis.json",
    "diameter_delta_analysis.json",
    "steel_delta_analysis.json",
    "schedule_delta_analysis.json",
    "recovery_contribution_analysis.json",
    "engineering_health_delta.json",
    "recovery_impact_summary.json",
    "recovery_validation_report.json",
)


class ValidationExporter:
    """Write validation JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "baseline_snapshot.json": result.get("baseline_snapshot"),
            "pipeline_delta.json": result.get("pipeline_delta"),
            "beam_delta_analysis.json": result.get("beam_delta_analysis"),
            "reinforcement_delta_analysis.json": {
                "categories": (result.get("reinforcement_delta_analysis") or {}).get("categories"),
                "category_summary": (result.get("reinforcement_delta_analysis") or {}).get("category_summary"),
            },
            "diameter_delta_analysis.json": result.get("diameter_delta_analysis"),
            "steel_delta_analysis.json": result.get("steel_delta_analysis"),
            "schedule_delta_analysis.json": result.get("schedule_delta_analysis"),
            "recovery_contribution_analysis.json": result.get("recovery_contribution_analysis"),
            "engineering_health_delta.json": result.get("engineering_health_delta"),
            "recovery_impact_summary.json": result.get("recovery_impact_summary"),
            "recovery_validation_report.json": result.get("recovery_validation_report"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            ValidationExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("recovery_impact_summary") or {}
        no_regression = result.get("no_regression") or {}
        export_paths = result.get("export_paths") or {}
        normalized = summary.get("normalized_bars") or {}
        steel = summary.get("steel_weight_kg") or {}
        schedule = summary.get("beam_schedule_rows") or {}
        qa = summary.get("qa_dashboard_impact") or {}
        norm_cov = qa.get("normalization_coverage") or {}

        print("\n" + "=" * 80)
        print("Recovery Impact Validation")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print("Engineering Objects")
        _print_metric(summary.get("engineering_objects"))
        print("Normalized Bars")
        _print_metric(normalized)
        print("Calculated Bars")
        _print_metric(summary.get("calculated_bars"))
        print("Steel (kg)")
        _print_metric(steel)
        print("Schedule Rows")
        _print_metric(schedule)
        print("")
        print("QA Dashboard Impact")
        print("-" * 80)
        print(
            f"Normalization Coverage: {norm_cov.get('before')}% -> "
            f"{norm_cov.get('after')}% (Delta {norm_cov.get('delta')}%)"
        )
        print(f"Recovery ROI: {summary.get('recovery_roi')}")
        print(f"No Regression Status: {no_regression.get('status')}")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


def _print_metric(metric: dict[str, Any] | None) -> None:
    metric = metric or {}
    print(f"  Before: {metric.get('before', 0)}")
    print(f"  After:  {metric.get('after', 0)}")
    print(f"  Delta:  {metric.get('delta', 0)}")


class ValidationExportValidator:
    """Validate export completeness and read-only scope."""

    REQUIRED_SUMMARY_KEYS = (
        "engineering_objects",
        "normalized_bars",
        "calculated_bars",
        "steel_weight_kg",
        "beam_schedule_rows",
    )

    def validate_exports(self, output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        for filename in export_files:
            path = output_dir / filename
            checks.append(self._check(f"Export Exists {filename}", path.exists()))
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                checks.append(self._check(f"Export JSON Valid {filename}", isinstance(payload, (dict, list))))
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    def validate_result(self, result: dict[str, Any]) -> dict[str, Any]:
        checks = [
            self._check("Model Version 5.26.1", result.get("model_version") == "5.26.1"),
            self._check("Read Only Analysis", result.get("read_only_analysis") is True),
            self._check("Baseline Loaded", bool(result.get("baseline_snapshot"))),
            self._check("Current State Loaded", bool(result.get("pipeline_delta"))),
            self._check("Pipeline Delta Complete", bool((result.get("pipeline_delta") or {}).get("pipeline_delta"))),
            self._check("Beam Deltas Computed", bool(result.get("beam_delta_analysis"))),
            self._check("Reinforcement Deltas Computed", bool(result.get("reinforcement_delta_analysis"))),
            self._check("Diameter Deltas Computed", bool(result.get("diameter_delta_analysis"))),
            self._check("Steel Deltas Computed", bool(result.get("steel_delta_analysis"))),
            self._check("Recovery Contribution Complete", bool(result.get("recovery_contribution_analysis"))),
            self._check("QA Comparison Complete", bool((result.get("recovery_impact_summary") or {}).get("qa_dashboard_impact"))),
            self._check("Engineering Health Delta Complete", bool(result.get("engineering_health_delta"))),
            self._check("No Regressions Detected", (result.get("no_regression") or {}).get("status") == "PASS"),
            self._check("Append-Only Verification", (result.get("no_regression") or {}).get("append_only_growth") is True),
        ]
        summary = result.get("recovery_impact_summary") or {}
        for key in self.REQUIRED_SUMMARY_KEYS:
            checks.append(self._check(f"Summary Contains {key}", key in summary and summary[key] is not None))

        contributions = (result.get("recovery_contribution_analysis") or {}).get("contributions") or []
        recovered_count = (result.get("baseline_snapshot") or {}).get("recovery_index", {}).get("recovered_count", 0)
        checks.append(
            self._check(
                "Every Recovered Object Has Impact Report",
                len(contributions) == recovered_count and recovered_count > 0,
            )
        )

        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
