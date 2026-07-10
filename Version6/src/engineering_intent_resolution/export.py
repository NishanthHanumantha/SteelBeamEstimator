"""Export engineering intent resolution artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.engineering_intent_resolution.reporting import ResolutionReporting
from src.engineering_intent_resolution.resolution_collector import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "engineering_decision_registry.json",
    "engineering_decision_objects.json",
    "engineering_intent_graph.json",
    "engineering_intent_conflicts.json",
    "engineering_intent_merges.json",
    "engineering_intent_resolution_traceability.json",
    "engineering_decision_statistics.json",
    "engineering_decision_validation.json",
    "engineering_decision_health.json",
    "engineering_decision_summary.json",
    "engineering_decision_report.json",
    "engineering_resolution_rules.json",
)


class ResolutionExporter:
    """Write resolution JSON exports and console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "engineering_decision_registry.json": result.get("decision_registry"),
            "engineering_decision_objects.json": {
                "object_count": len(result.get("decisions") or []),
                "objects": result.get("decisions"),
            },
            "engineering_intent_graph.json": {
                "graph_count": len(result.get("graphs") or []),
                "graphs": result.get("graphs"),
            },
            "engineering_intent_conflicts.json": {
                "conflict_count": len(result.get("conflicts") or []),
                "conflicts": result.get("conflicts"),
            },
            "engineering_intent_merges.json": {
                "merge_count": len(result.get("merges") or []),
                "merges": result.get("merges"),
            },
            "engineering_intent_resolution_traceability.json": {
                "chain_count": len(result.get("traceability") or []),
                "chains": result.get("traceability"),
            },
            "engineering_decision_statistics.json": result.get("statistics"),
            "engineering_decision_validation.json": result.get("validation"),
            "engineering_decision_health.json": result.get("health"),
            "engineering_decision_summary.json": result.get("summary"),
            "engineering_decision_report.json": ResolutionReporting.build_report(result),
            "engineering_resolution_rules.json": result.get("resolution_rules"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            payload = mapping[filename]
            if filename == "engineering_decision_validation.json" and payload is None:
                continue
            ResolutionExporter._write_json(path, payload)
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def validate_exports(output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks = []
        for filename in export_files:
            path = output_dir / filename
            payload = ResolutionExporter._read_json(path)
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
        print("Engineering Intent Resolution Engine")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Intent Objects: {summary.get('intent_objects', 0)}")
        print(f"Engineering Decisions: {summary.get('engineering_decisions', 0)}")
        print(f"Merged Intent: {summary.get('merged_intent', 0)}")
        print(f"Suppressed Intent: {summary.get('suppressed_intent', 0)}")
        print(f"Conflicts: {summary.get('conflict_count', 0)}")
        print(f"Resolved Conflicts: {summary.get('resolved_conflicts', 0)}")
        print(f"Decision Coverage: {summary.get('decision_coverage_percent', 0)}%")
        print(f"Intent Reduction Ratio: {summary.get('intent_reduction_ratio', 0)}")
        print(f"Engineering Confidence: {summary.get('engineering_confidence', 0)}")
        print(f"Resolution Health: {health.get('engineering_resolution_health')}")
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
        ResolutionExporter._write_json(
            output_dir / "engineering_decision_validation.json",
            result.get("validation"),
        )
        ResolutionExporter._write_json(
            output_dir / "engineering_decision_summary.json",
            result.get("summary"),
        )

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists() or path.stat().st_size <= 2:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if payload is not None else None
