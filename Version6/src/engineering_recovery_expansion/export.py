"""Export recovery expansion artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.engineering_recovery_expansion.candidate_loader import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "expansion_candidates.json",
    "expansion_decisions.json",
    "expansion_registry.json",
    "expansion_statistics.json",
    "expansion_validation.json",
    "expansion_summary.json",
    "expansion_traceability.json",
    "expansion_health.json",
    "expansion_report.json",
)


class ExpansionExporter:
    """Write expansion JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "expansion_candidates.json": {
                "candidate_count": len(result.get("candidates") or []),
                "candidates": result.get("candidates"),
            },
            "expansion_decisions.json": {
                "decision_count": len(result.get("decisions") or []),
                "decisions": result.get("decisions"),
            },
            "expansion_registry.json": result.get("expansion_registry"),
            "expansion_statistics.json": result.get("statistics"),
            "expansion_validation.json": result.get("validation"),
            "expansion_summary.json": result.get("summary"),
            "expansion_traceability.json": {
                "chain_count": len(result.get("traceability") or []),
                "chains": result.get("traceability"),
            },
            "expansion_health.json": result.get("health"),
            "expansion_report.json": {
                "phase": result.get("phase"),
                "model_version": result.get("model_version"),
                "engine_version": result.get("engine_version"),
                "run_timestamp": result.get("run_timestamp"),
                "summary": result.get("summary"),
                "statistics": result.get("statistics"),
                "health": result.get("health"),
                "validation": result.get("validation"),
                "production_integration": result.get("production_integration"),
            },
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            ExpansionExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def validate_exports(output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks = []
        for filename in export_files:
            path = output_dir / filename
            payload = ExpansionExporter._read_json(path)
            checks.append(
                {
                    "name": f"Export Exists {filename}",
                    "status": "PASS" if payload is not None else "FAIL",
                }
            )
            checks.append(
                {
                    "name": f"Export Valid JSON {filename}",
                    "status": "PASS" if payload is not None else "FAIL",
                }
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
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("summary") or {}
        statistics = result.get("statistics") or {}
        health = result.get("health") or {}
        print("\n" + "=" * 80)
        print("Engineering Object Recovery Expansion")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print()
        print(f"Objects Evaluated: {statistics.get('objects_evaluated', 0)}")
        print(f"Expansion Candidates: {statistics.get('expansion_candidates', 0)}")
        print(f"Recovered: {statistics.get('recovered', 0)}")
        print(f"Rejected: {statistics.get('rejected', 0)}")
        print(f"Coverage Before: {statistics.get('coverage_before_percent', 0)}%")
        print(f"Coverage After: {statistics.get('coverage_after_percent', 0)}%")
        print(f"Recovery Improvement: {statistics.get('recovery_improvement_percent', 0)}%")
        print(f"Overall Expansion Health: {health.get('overall_expansion_health', 0)}")
        print()
        print("Export Locations")
        print("-" * 80)
        for filename, path in (result.get("export_paths") or {}).items():
            print(f"{filename}: {path}")
        print("=" * 80)
        validation = result.get("validation") or {}
        export_validation = result.get("export_validation") or {}
        print(
            f"\nValidation: {validation.get('summary', {}).get('passed', 0)}/"
            f"{validation.get('summary', {}).get('total_checks', 0)} PASS"
        )
        print(
            f"Exports: {export_validation.get('summary', {}).get('passed', 0)}/"
            f"{export_validation.get('summary', {}).get('total_checks', 0)} PASS"
        )

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> Any | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
