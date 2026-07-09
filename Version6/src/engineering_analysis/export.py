"""Export engineering coverage analysis artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


EXPORT_FILES = (
    "engineering_coverage_analysis.json",
    "pipeline_funnel.json",
    "beam_coverage_report.json",
    "reinforcement_coverage.json",
    "diameter_engineering_coverage.json",
    "calculation_state_analysis.json",
    "engineering_gap_analysis.json",
    "engineering_loss_report.json",
    "engineering_health_score.json",
    "root_cause_summary.json",
)


class EngineeringExporter:
    """Write JSON exports and render the console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "engineering_coverage_analysis.json": {
                "phase": result.get("phase"),
                "model_version": result.get("model_version"),
                "engine_version": result.get("engine_version"),
                "run_timestamp": result.get("run_timestamp"),
                "engineering_code_modified": result.get("engineering_code_modified"),
                "engineering_pipeline_frozen": result.get("engineering_pipeline_frozen"),
                "read_only_analysis": result.get("read_only_analysis"),
                "load_status": result.get("load_status"),
                "stage_coverage": result.get("stage_coverage"),
                "statistics": result.get("statistics"),
            },
            "pipeline_funnel.json": result.get("pipeline_funnel"),
            "beam_coverage_report.json": result.get("beam_coverage_report"),
            "reinforcement_coverage.json": {
                "categories": result.get("reinforcement_categories"),
                "bar_type_coverage": result.get("bar_type_coverage"),
            },
            "diameter_engineering_coverage.json": {
                "diameters": result.get("diameter_engineering_coverage"),
            },
            "calculation_state_analysis.json": result.get("calculation_state_analysis"),
            "engineering_gap_analysis.json": result.get("engineering_gap_analysis"),
            "engineering_loss_report.json": result.get("engineering_loss_report"),
            "engineering_health_score.json": result.get("engineering_health_score"),
            "root_cause_summary.json": result.get("root_cause_summary"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            EngineeringExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        pipeline = result.get("pipeline_funnel") or {}
        stages = pipeline.get("stages") or []
        calculation = result.get("calculation_state_analysis") or {}
        blocked = calculation.get("blocked_analysis") or {}
        health = result.get("engineering_health_score") or {}
        root_causes = result.get("root_cause_summary") or {}
        beam_report = result.get("beam_coverage_report") or {}
        export_paths = result.get("export_paths") or {}

        print("\n" + "=" * 80)
        print("Engineering Coverage Analysis")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print("Beam Coverage")
        print("-" * 80)
        print(f"Beams Analysed: {beam_report.get('beam_count', 0)}")
        print(f"Average Completeness: {beam_report.get('average_completeness_percent', 0)}%")
        print("")
        print("Pipeline Funnel")
        print("-" * 80)
        for stage in stages:
            print(f"{stage.get('label')}: {stage.get('count')}")
        print("")
        print("Calculation States")
        print("-" * 80)
        for item in (calculation.get("calculation_states") or {}).get("states") or []:
            if item.get("count", 0) > 0:
                print(f"{item.get('state')}: {item.get('count')} ({item.get('percentage')}%)")
        print("")
        print("Top Blocking Reasons")
        print("-" * 80)
        top_blocked = blocked.get("top_blocking_reasons") or []
        if top_blocked:
            for item in top_blocked[:5]:
                print(f"{item.get('reason')}: {item.get('count')}")
        else:
            deferred = calculation.get("deferred_analysis") or {}
            for item in (deferred.get("reasons") or [])[:5]:
                print(f"{item.get('reason')}: {item.get('count')}")
        print("")
        print("Engineering Health")
        print("-" * 80)
        subsystems = health.get("subsystems") or {}
        for name, score in subsystems.items():
            print(f"{name.replace('_', ' ').title()}: {score}")
        print(f"Overall: {health.get('overall', 0)}")
        print("")
        print("Top Root Causes")
        print("-" * 80)
        for item in (root_causes.get("top_issues") or [])[:5]:
            print(
                f"{item.get('rank')}. {item.get('issue')} "
                f"[{item.get('impact')}] "
                f"({item.get('estimated_downstream_effect_percent')}%)"
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


class EngineeringCoverageValidator:
    """Validate engineering coverage analysis completeness."""

    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.extend(self._scope_checks(result))
        checks.extend(self._beam_checks(result))
        checks.extend(self._funnel_checks(result))
        checks.extend(self._coverage_checks(result))
        checks.extend(self._state_checks(result))
        checks.extend(self._health_checks(result))
        checks.extend(self._root_cause_checks(result))
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "phase": result.get("phase"),
            "model_version": result.get("model_version"),
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    def validate_exports(self, output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        for filename in EXPORT_FILES:
            path = output_dir / filename
            checks.append(self._check(f"Export Written {filename}", path.exists() and path.stat().st_size > 0))
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
            self._check("Engineering Pipeline Frozen", result.get("engineering_pipeline_frozen") is True),
            self._check("Parser Not Executed", result.get("parser_executed") is False),
            self._check("Read Only Analysis", result.get("read_only_analysis") is True),
            self._check("DXF Not Accessed", result.get("dxf_accessed") is False),
            self._check("Model Version 5.22.0", result.get("model_version") == "5.22.0"),
        ]

    def _beam_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        beam_report = result.get("beam_coverage_report") or {}
        beam_count = beam_report.get("beam_count", 0)
        beams = beam_report.get("beams") or []
        return [
            self._check("Every Beam Analysed", beam_count >= 1 and len(beams) == beam_count),
            self._check("Beam Completeness Range Valid", all(
                0 <= float(item.get("overall_completeness_percent", -1)) <= 100 for item in beams
            )),
        ]

    def _funnel_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        funnel = result.get("pipeline_funnel") or {}
        stages = funnel.get("stages") or []
        bar_stage_keys = (
            "normalized_bars",
            "ready_for_calculation",
            "calculated_bars",
            "bbs_rows_written",
            "beam_schedule_rows",
            "excel_rows_written",
        )
        bar_counts = [
            stage.get("count", 0)
            for stage in stages
            if stage.get("stage") in bar_stage_keys
        ]
        monotonic = all(left >= right for left, right in zip(bar_counts, bar_counts[1:]))
        transitions = funnel.get("transitions") or []
        consistent = True
        for transition in transitions:
            expected_loss = max(transition.get("from_count", 0) - transition.get("to_count", 0), 0)
            if transition.get("loss", -1) != expected_loss:
                consistent = False
                break
        return [
            self._check("Funnel Internally Consistent", len(stages) >= 2 and consistent),
            self._check("Stage Counts Monotonic", len(bar_counts) >= 2 and monotonic),
        ]

    def _coverage_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        stage_coverage = result.get("stage_coverage") or {}
        valid = True
        for stage in stage_coverage.values():
            coverage = stage.get("coverage_percent")
            if coverage is None or coverage < 0 or coverage > 100:
                valid = False
                break
        losses = result.get("engineering_loss_report") or {}
        loss_valid = all(item.get("lost", -1) >= 0 for item in losses.get("transitions") or [])
        return [
            self._check("Coverage Percentages Valid", valid),
            self._check("Loss Accounting Valid", loss_valid),
        ]

    def _state_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        calculation = result.get("calculation_state_analysis") or {}
        states = (calculation.get("calculation_states") or {}).get("states") or []
        total = sum(item.get("count", 0) for item in states)
        bar_count = (calculation.get("calculation_states") or {}).get("total_bars", 0)
        return [
            self._check("State Totals Consistent", total == bar_count),
            self._check("Calculation States Generated", len(states) >= 1),
        ]

    def _health_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        health = result.get("engineering_health_score") or {}
        subsystems = health.get("subsystems") or {}
        overall = health.get("overall")
        valid = all(0 <= float(value) <= 100 for value in subsystems.values())
        valid = valid and overall is not None and 0 <= float(overall) <= 100
        return [self._check("Health Score Range Valid", valid)]

    def _root_cause_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        root = result.get("root_cause_summary") or {}
        return [self._check("Root Causes Generated", len(root.get("top_issues") or []) >= 1)]

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
