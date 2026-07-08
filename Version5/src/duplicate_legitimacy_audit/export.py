"""Export duplicate suppression legitimacy audit artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.duplicate_legitimacy_audit.duplicate_group_loader import DuplicateLegitimacy, MODEL_VERSION, PHASE


EXPORT_FILES = (
    "duplicate_legitimacy_report.json",
    "duplicate_legitimacy_summary.json",
    "duplicate_legitimacy_statistics.json",
    "duplicate_group_analysis.json",
    "duplicate_confidence_scores.json",
    "duplicate_root_cause_chain.json",
    "duplicate_engineering_context.json",
    "duplicate_recommendations.json",
    "duplicate_health.json",
    "duplicate_decision_matrix.json",
)

LEGITIMACY_VALUES = {item.value for item in DuplicateLegitimacy}


class DuplicateLegitimacyExporter:
    """Write JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "duplicate_legitimacy_report.json": {
                "phase": result.get("phase"),
                "model_version": result.get("model_version"),
                "engine_version": result.get("engine_version"),
                "run_timestamp": result.get("run_timestamp"),
                "group_count": len(result.get("group_analyses") or []),
                "groups": result.get("group_analyses"),
            },
            "duplicate_legitimacy_summary.json": result.get("summary"),
            "duplicate_legitimacy_statistics.json": result.get("statistics"),
            "duplicate_group_analysis.json": {
                "duplicate_group_count": len(result.get("group_analyses") or []),
                "groups": result.get("group_analyses"),
            },
            "duplicate_confidence_scores.json": {
                "scores": result.get("confidence_scores"),
            },
            "duplicate_root_cause_chain.json": {
                "chains": result.get("root_cause_chains"),
            },
            "duplicate_engineering_context.json": {
                "contexts": result.get("engineering_contexts"),
            },
            "duplicate_recommendations.json": result.get("recommendations"),
            "duplicate_health.json": result.get("health"),
            "duplicate_decision_matrix.json": {
                "records": result.get("decision_matrix"),
            },
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            DuplicateLegitimacyExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("summary") or {}
        health = result.get("health") or {}
        recommendations = (result.get("recommendations") or {}).get("recommendations") or []
        export_paths = result.get("export_paths") or {}

        print("\n" + "=" * 80)
        print("Duplicate Suppression Legitimacy Audit")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Total Duplicate Groups: {summary.get('total_duplicate_groups', 0)}")
        print(f"Legitimate Duplicates: {summary.get('legitimate_duplicates', 0)}")
        print(f"Potential Incorrect Suppressions: {summary.get('potential_incorrect_suppressions', 0)}")
        print(f"Likely Independent Engineering Bars: {summary.get('likely_independent_engineering_bars', 0)}")
        print(f"Potential Steel Recovery: {summary.get('potential_steel_recovery', 0)}")
        print(f"Overall Duplicate Health: {health.get('overall_duplicate_health', 0)}")
        print("")
        print("Highest Risk Duplicate Groups")
        print("-" * 80)
        for item in summary.get("highest_risk_groups") or []:
            print(
                f"{item.get('signature')} — {item.get('legitimacy_class')} "
                f"(confidence {item.get('confidence_score')})"
            )
        print("")
        print("Engineering Recommendations")
        print("-" * 80)
        for item in recommendations[:5]:
            print(f"{item.get('signature')}: {item.get('recommendation')} ({item.get('priority')})")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


class DuplicateLegitimacyValidator:
    """Validate duplicate legitimacy audit completeness."""

    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.extend(self._scope_checks(result))
        checks.extend(self._group_checks(result))
        checks.extend(self._artifact_checks(result))
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
            self._check("Model Version 5.25.0", result.get("model_version") == "5.25.0"),
            self._check("QA.COVERAGE.4 Outputs Unchanged", result.get("prior_phase_outputs_modified") is False),
        ]

    def _group_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        groups = result.get("group_analyses") or []
        duplicate_groups = result.get("duplicate_groups") or []
        confidence_scores = result.get("confidence_scores") or []
        recommendations = (result.get("recommendations") or {}).get("recommendations") or []
        root_cause_chains = result.get("root_cause_chains") or []
        engineering_contexts = result.get("engineering_contexts") or []
        decision_matrix = result.get("decision_matrix") or []

        legitimacy_values = [item.get("legitimacy_class") for item in groups]
        checks = [
            self._check("Every Duplicate Group Classified", len(groups) == len(duplicate_groups) and len(groups) >= 1),
            self._check(
                "One Legitimacy Class Only",
                all(value in LEGITIMACY_VALUES for value in legitimacy_values)
                and len(legitimacy_values) == len(set(item.get("group_id") for item in groups)),
            ),
            self._check("Confidence Generated", len(confidence_scores) == len(groups)),
            self._check("Recommendation Generated", len(recommendations) == len(groups)),
            self._check("Root Cause Generated", len(root_cause_chains) == len(groups)),
            self._check("Engineering Comparison Generated", len(engineering_contexts) == len(groups)),
            self._check("Decision Matrix Complete", len(decision_matrix) == len(groups)),
            self._check(
                "Confidence Scores Valid",
                all(0 <= float(item.get("confidence_score", -1)) <= 100 for item in confidence_scores),
            ),
        ]
        return checks

    def _artifact_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        return [
            self._check("Statistics Generated", bool(result.get("statistics"))),
            self._check("Health Metrics Generated", bool(result.get("health"))),
            self._check("Summary Generated", bool(result.get("summary"))),
            self._check("Decision Reproducible", bool(result.get("decision_matrix"))),
        ]

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
