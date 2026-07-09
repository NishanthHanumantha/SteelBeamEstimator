"""Export engineering intent reconstruction artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.engineering_intent.intent_collector import MODEL_VERSION, PHASE
from src.engineering_intent.reporting import IntentReporting


EXPORT_FILES = (
    "engineering_intent_registry.json",
    "engineering_intent_objects.json",
    "engineering_intent_traceability.json",
    "engineering_intent_statistics.json",
    "engineering_intent_validation.json",
    "engineering_intent_summary.json",
    "engineering_intent_report.json",
    "engineering_intent_health.json",
    "engineering_intent_rules.json",
    "engineering_intent_recommendations.json",
)


class IntentExporter:
    """Write intent JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "engineering_intent_registry.json": result.get("intent_registry"),
            "engineering_intent_objects.json": {
                "object_count": len(result.get("intent_objects") or []),
                "objects": result.get("intent_objects"),
            },
            "engineering_intent_traceability.json": {
                "chain_count": len(result.get("traceability") or []),
                "chains": result.get("traceability"),
            },
            "engineering_intent_statistics.json": result.get("statistics"),
            "engineering_intent_validation.json": result.get("validation"),
            "engineering_intent_summary.json": result.get("summary"),
            "engineering_intent_report.json": IntentReporting.build_report(result),
            "engineering_intent_health.json": result.get("health"),
            "engineering_intent_rules.json": IntentReporting.build_rules_export(),
            "engineering_intent_recommendations.json": result.get("recommendations"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            payload = mapping[filename]
            if filename == "engineering_intent_validation.json" and payload is None:
                continue
            IntentExporter._write_json(path, payload)
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def validate_exports(output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks = []
        for filename in export_files:
            path = output_dir / filename
            payload = IntentExporter._read_json(path)
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
        print("Engineering Intent Reconstruction Engine")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Intent Candidates: {summary.get('intent_candidates', 0)}")
        print(f"Reconstructed Objects: {summary.get('reconstructed_objects', 0)}")
        print(f"Reconstructed Bars: {summary.get('reconstructed_bars', 0)}")
        print(f"Intent Categories: {summary.get('intent_categories', {})}")
        print(f"Engineering Coverage: {summary.get('engineering_coverage_percent', 0)}%")
        print(f"Intent Coverage: {summary.get('intent_coverage_percent', 0)}%")
        print(f"Recovery + Intent Coverage: {summary.get('recovery_plus_intent_coverage_percent', 0)}%")
        print(f"Overall Engineering Health: {health.get('overall_engineering_health')}")
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
        IntentExporter._write_json(output_dir / "engineering_intent_validation.json", result.get("validation"))
        IntentExporter._write_json(output_dir / "engineering_intent_summary.json", result.get("summary"))

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists() or path.stat().st_size <= 2:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if payload is not None else None
