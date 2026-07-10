"""Export Phase K.2 Engineering Decision Execution artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from decision_collector import MODEL_VERSION, PHASE
from execution_reporting import ExecutionReporting


EXPORT_FILES = (
    "execution_registry.json",
    "execution_context.json",
    "execution_pipeline.json",
    "decision_execution_mapping.json",
    "execution_statistics.json",
    "execution_validation.json",
    "execution_health.json",
    "execution_traceability.json",
    "execution_summary.json",
    "execution_report.json",
    "execution_lifecycle.json",
    "production_bridge.json",
)


class ExecutionExporter:
    """Write Phase K.2 JSON exports and console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "execution_registry.json": result.get("execution_registry"),
            "execution_context.json": {
                "context_count": len(result.get("execution_contexts") or []),
                "contexts": result.get("execution_contexts"),
            },
            "execution_pipeline.json": {
                "steps": result.get("pipeline_steps"),
                "idempotent": result.get("idempotent"),
                "adapter_status": (result.get("adapter_result") or {}).get("status"),
            },
            "decision_execution_mapping.json": result.get("mapping"),
            "execution_statistics.json": result.get("statistics"),
            "execution_validation.json": result.get("validation"),
            "execution_health.json": result.get("health"),
            "execution_traceability.json": {
                "chain_count": len(result.get("traceability") or []),
                "chains": result.get("traceability"),
            },
            "execution_summary.json": result.get("summary"),
            "execution_report.json": ExecutionReporting.build_report(result),
            "execution_lifecycle.json": {
                "lifecycle_count": len(result.get("execution_lifecycle") or []),
                "lifecycles": result.get("execution_lifecycle"),
            },
            "production_bridge.json": result.get("production_bridge"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            payload = mapping[filename]
            if filename == "execution_validation.json" and payload is None:
                continue
            ExecutionExporter._write_json(path, payload)
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def validate_exports(output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks = []
        for filename in export_files:
            path = output_dir / filename
            payload = ExecutionExporter._read_json(path)
            checks.append(
                {"name": f"Export Exists {filename}", "status": "PASS" if payload is not None else "FAIL"}
            )
            checks.append(
                {"name": f"Export Valid JSON {filename}", "status": "PASS" if payload is not None else "FAIL"}
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
        health = result.get("health") or {}
        export_paths = result.get("export_paths") or {}
        print("\n" + "=" * 80)
        print("Engineering Decision Execution Engine")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Engineering Decisions: {summary.get('engineering_decisions', 0)}")
        print(f"Executable Decisions: {summary.get('executable_decisions', 0)}")
        print(f"Not Executable: {summary.get('not_executable_decisions', 0)}")
        print(f"Execution Registry: {summary.get('execution_registry_count', 0)}")
        print(f"Decision Mapping Coverage: {summary.get('decision_mapping_coverage_percent', 0)}%")
        print(f"Calculation Engine Invoked: {summary.get('calculation_engine_invoked', False)}")
        print(f"Formulas Modified: {summary.get('formulas_modified', False)}")
        print(f"Duplicated Calculations: {summary.get('duplicated_calculations', False)}")
        print(f"Execution Health: {health.get('execution_health')}")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

    @staticmethod
    def _write_validation_bundle(output_dir: Path, result: dict[str, Any]) -> None:
        ExecutionExporter._write_json(output_dir / "execution_validation.json", result.get("validation"))
        ExecutionExporter._write_json(output_dir / "execution_summary.json", result.get("summary"))

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists() or path.stat().st_size <= 2:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if payload is not None else None
