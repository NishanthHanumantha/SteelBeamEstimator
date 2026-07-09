"""Export engineering recovery artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_recovery.recovery_collector import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "recovery_registry.json",
    "recovery_candidates.json",
    "recovery_decisions.json",
    "recovered_engineering_objects.json",
    "recovery_traceability.json",
    "recovery_statistics.json",
    "recovery_validation.json",
    "recovery_health.json",
    "recovery_summary.json",
    "recovery_report.json",
)


class RecoveryExporter:
    """Write recovery JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "recovery_registry.json": result.get("recovery_registry"),
            "recovery_candidates.json": {
                "candidate_count": len(result.get("candidates") or []),
                "candidates": result.get("candidates"),
            },
            "recovery_decisions.json": {
                "decision_count": len(result.get("decisions") or []),
                "decisions": result.get("decisions"),
            },
            "recovered_engineering_objects.json": {
                "recovered_count": len(result.get("recovered_objects") or []),
                "objects": result.get("recovered_objects"),
            },
            "recovery_traceability.json": {
                "chains": result.get("traceability"),
            },
            "recovery_statistics.json": result.get("statistics"),
            "recovery_validation.json": {
                "candidate_validation": result.get("candidate_validation"),
                "recovery_validation": result.get("recovery_validation"),
                "export_validation": result.get("export_validation"),
            },
            "recovery_health.json": result.get("health"),
            "recovery_summary.json": result.get("summary"),
            "recovery_report.json": {
                "phase": result.get("phase"),
                "model_version": result.get("model_version"),
                "engine_version": result.get("engine_version"),
                "run_timestamp": result.get("run_timestamp"),
                "summary": result.get("summary"),
                "statistics": result.get("statistics"),
                "health": result.get("health"),
                "recovered_objects": result.get("recovered_objects"),
                "registry": result.get("recovery_registry"),
                "production_merge": result.get("production_merge"),
            },
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            RecoveryExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("summary") or {}
        health = result.get("health") or {}
        export_paths = result.get("export_paths") or {}
        print("\n" + "=" * 80)
        print("Engineering Object Recovery")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Recovery Candidates: {summary.get('recovery_candidates', 0)}")
        print(f"Recovered Objects: {summary.get('recovered_objects', 0)}")
        print(f"Rejected Recovery Candidates: {summary.get('rejected_recovery_candidates', 0)}")
        print(f"Recovery Success: {summary.get('recovery_success_percent', 0)}%")
        print(f"Recovered Normalized Bars: {summary.get('recovered_normalized_bars', 0)}")
        print(f"Recovery Safety: {health.get('recovery_safety', 0)}")
        print(f"Recovery Confidence: {health.get('recovery_confidence', 0)}")
        print(f"Recovery Risk: {health.get('recovery_risk', 0)}")
        print(f"Steel Coverage Before: {health.get('steel_coverage_before_percent', 0)}%")
        print(f"Steel Coverage After: {health.get('steel_coverage_after_percent', 0)}%")
        print(f"Improvement: {health.get('steel_coverage_improvement_percent', 0)}%")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


class RecoveryExportValidator:
    """Validate recovery export completeness."""

    def validate_scope(self, result: dict[str, Any]) -> dict[str, Any]:
        checks = [
            RecoveryValidatorHelper.check("Model Version 5.26.0", result.get("model_version") == "5.26.0"),
            RecoveryValidatorHelper.check("Production Enhancement Phase", result.get("read_only_analysis") is False),
            RecoveryValidatorHelper.check("Recovery Reproducible", bool(result.get("decisions"))),
        ]
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


class RecoveryValidatorHelper:
    @staticmethod
    def check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
