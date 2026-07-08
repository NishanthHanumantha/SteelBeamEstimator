"""Export engineering object creation audit artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_object_audit.audit_collector import MODEL_VERSION, REJECTION_CODES


EXPORT_FILES = (
    "engineering_object_creation_audit.json",
    "engineering_object_decision_matrix.json",
    "engineering_object_rejection_statistics.json",
    "dependency_analysis.json",
    "duplicate_analysis.json",
    "engineering_object_health.json",
    "engineering_object_readiness.json",
    "engineering_recommendations.json",
    "root_cause_chain.json",
    "engineering_object_creation_summary.json",
)


class AuditExporter:
    """Write JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "engineering_object_creation_audit.json": {
                "phase": result.get("phase"),
                "model_version": result.get("model_version"),
                "audit_count": len(result.get("audits") or []),
                "audits": result.get("audits"),
            },
            "engineering_object_decision_matrix.json": {
                "records": result.get("decision_matrix"),
            },
            "engineering_object_rejection_statistics.json": result.get("rejection_statistics"),
            "dependency_analysis.json": result.get("dependency_analysis"),
            "duplicate_analysis.json": result.get("duplicate_analysis"),
            "engineering_object_health.json": result.get("engineering_object_health"),
            "engineering_object_readiness.json": result.get("readiness_analysis"),
            "engineering_recommendations.json": result.get("recommendations"),
            "root_cause_chain.json": {"chains": result.get("root_cause_chains")},
            "engineering_object_creation_summary.json": result.get("summary"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            AuditExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        health = result.get("engineering_object_health") or {}
        stats = result.get("rejection_statistics") or {}
        dependency = result.get("dependency_analysis") or {}
        duplicate = result.get("duplicate_analysis") or {}
        recommendations = (result.get("recommendations") or {}).get("recommendations") or []
        readiness = result.get("readiness_analysis") or {}
        export_paths = result.get("export_paths") or {}

        print("\n" + "=" * 80)
        print("Engineering Object Creation Audit")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print("Engineering Object Health")
        print("-" * 80)
        for name, score in (health.get("subsystems") or {}).items():
            print(f"{name.replace('_', ' ').title()}: {score}")
        print(f"Overall Object Creation Health: {health.get('overall_object_creation_health', 0)}")
        print("")
        print(f"Overall Readiness: {readiness.get('average_readiness_score', 0)}")
        print("")
        print("Top Rejection Codes")
        print("-" * 80)
        for item in (stats.get("primary_rejection_codes") or [])[:5]:
            print(f"{item.get('rejection_code')}: {item.get('count')} ({item.get('engineering_impact')})")
        print("")
        print("Top Dependency Failures")
        print("-" * 80)
        for item in (dependency.get("top_dependency_failures") or [])[:5]:
            print(f"{item.get('dependency')}: {item.get('count')}")
        print("")
        print("Duplicate Summary")
        print("-" * 80)
        print(f"Duplicate Groups: {duplicate.get('duplicate_group_count', 0)}")
        print(f"Valid Duplicates: {duplicate.get('valid_duplicate_groups', 0)}")
        print(f"Suspicious Duplicates: {duplicate.get('suspicious_duplicate_groups', 0)}")
        print("")
        print("Top Recommendations")
        print("-" * 80)
        for item in recommendations[:5]:
            print(f"{item.get('root_cause')}: {item.get('recommendation')} ({item.get('expected_impact')})")
        print("")
        print("Highest Impact Engineering Issues")
        print("-" * 80)
        for item in (stats.get("primary_rejection_codes") or [])[:3]:
            print(
                f"{item.get('rejection_code')} — {item.get('count')} callouts "
                f"({item.get('engineering_impact')} impact)"
            )
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


class AuditValidator:
    """Validate engineering object creation audit completeness."""

    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.extend(self._scope_checks(result))
        checks.extend(self._audit_checks(result))
        checks.extend(self._matrix_checks(result))
        checks.extend(self._analysis_checks(result))
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "phase": result.get("phase"),
            "model_version": MODEL_VERSION,
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    def validate_exports(self, output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
        checks = [
            self._check(
                f"Export Written {filename}",
                (output_dir / filename).exists() and (output_dir / filename).stat().st_size > 0,
            )
            for filename in EXPORT_FILES
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

    def _scope_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        return [
            self._check("Engineering Code Not Modified", result.get("engineering_code_modified") is False),
            self._check("Parser Not Executed", result.get("parser_executed") is False),
            self._check("Read Only Analysis", result.get("read_only_analysis") is True),
            self._check("Model Version 5.24.0", result.get("model_version") == "5.24.0"),
        ]

    def _audit_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        inventory = result.get("inventory") or []
        audits = result.get("audits") or []
        rejected = [item for item in audits if not item.get("engineering_object_created")]
        checks = [
            self._check("Every Reinforcement Annotation Audited", len(audits) == len(inventory) and len(audits) >= 1),
            self._check(
                "Every Rejected Annotation Has Primary Code",
                all(
                    isinstance(item.get("primary_rejection_code"), str)
                    and item.get("primary_rejection_code") in REJECTION_CODES
                    for item in rejected
                ),
            ),
        ]
        accepted = [item for item in audits if item.get("engineering_object_created")]
        checks.append(
            self._check(
                "Accepted Annotations Have No Primary Rejection Code",
                all(item.get("primary_rejection_code") is None for item in accepted),
            )
        )
        return checks

    def _matrix_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        matrix = result.get("decision_matrix") or []
        chains = result.get("root_cause_chains") or []
        readiness = (result.get("readiness_analysis") or {}).get("records") or []
        inventory_count = len(result.get("inventory") or [])
        valid_readiness = all(
            0 <= float(item.get("readiness_score", -1)) <= 100 for item in readiness
        )
        return [
            self._check("Decision Matrix Complete", len(matrix) == inventory_count),
            self._check("Root Cause Chains Complete", len(chains) == inventory_count),
            self._check("Readiness Scores Valid", valid_readiness),
        ]

    def _analysis_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        return [
            self._check("Dependency Graph Complete", bool(result.get("dependency_analysis"))),
            self._check("Duplicate Analysis Complete", bool(result.get("duplicate_analysis"))),
            self._check("Recommendation Engine Complete", bool(result.get("recommendations"))),
            self._check("Health Metrics Generated", bool(result.get("engineering_object_health"))),
        ]

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
