"""Recovery Impact Validation orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.engineering_recovery_validation.baseline_loader import BaselineLoader
from src.engineering_recovery_validation.beam_delta_analysis import BeamDeltaAnalyzer
from src.engineering_recovery_validation.delta_analyzer import DeltaAnalyzer
from src.engineering_recovery_validation.export import (
    EXPORT_FILES,
    ValidationExporter,
    ValidationExportValidator,
)
from src.engineering_recovery_validation.impact_statistics import ImpactStatistics
from src.engineering_recovery_validation.recovery_contribution import RecoveryContributionAnalyzer
from src.engineering_recovery_validation.reinforcement_delta_analysis import ReinforcementDeltaAnalyzer
from src.engineering_recovery_validation.reporting import RecoveryImpactReporting
from src.engineering_recovery_validation.schedule_delta_analysis import ScheduleDeltaAnalyzer
from src.engineering_recovery_validation.steel_delta_analysis import SteelDeltaAnalyzer
from src.engineering_recovery_validation.validation_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    RECOVERY_PHASE,
    ValidationCollector,
    default_paths,
)


class ValidationEngine:
    """Run deterministic read-only recovery impact validation."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = ValidationCollector(self._project_root).collect()
        baseline_snapshot = BaselineLoader().build(snapshot)
        pipeline_delta = DeltaAnalyzer().analyze(baseline_snapshot)
        beam_delta_analysis = BeamDeltaAnalyzer().analyze(snapshot, baseline_snapshot)
        reinforcement_delta_analysis = ReinforcementDeltaAnalyzer().analyze(snapshot)
        diameter_delta_analysis = ReinforcementDeltaAnalyzer().build_diameter_export(reinforcement_delta_analysis)
        steel_delta_analysis = SteelDeltaAnalyzer().analyze(snapshot, baseline_snapshot)
        schedule_delta_analysis = ScheduleDeltaAnalyzer().analyze(snapshot, baseline_snapshot)
        recovery_contribution_analysis = RecoveryContributionAnalyzer().analyze(snapshot)

        impact_statistics = ImpactStatistics()
        recovery_effectiveness = impact_statistics.build_effectiveness(snapshot)
        engineering_health_delta = impact_statistics.build_health_delta(baseline_snapshot, pipeline_delta)
        qa_dashboard_impact = impact_statistics.build_qa_dashboard_impact(snapshot, baseline_snapshot)
        top_contributors = impact_statistics.build_top_contributors(
            recovery_contribution_analysis,
            beam_delta_analysis,
            steel_delta_analysis,
            reinforcement_delta_analysis,
        )
        no_regression = impact_statistics.verify_no_regression(snapshot)

        reporting = RecoveryImpactReporting()
        recovery_impact_summary = reporting.build_summary(
            pipeline_delta,
            recovery_effectiveness,
            qa_dashboard_impact,
            top_contributors,
            no_regression,
        )
        recovery_impact_summary["recovery_effectiveness"] = recovery_effectiveness
        recovery_impact_summary["top_contributors"] = top_contributors

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "read_only_analysis": True,
            "production_modified": False,
            "recovery_executed": False,
            "recovery_phase_validated": RECOVERY_PHASE,
            "load_status": snapshot.get("load_status"),
            "baseline_snapshot": baseline_snapshot,
            "pipeline_delta": pipeline_delta,
            "beam_delta_analysis": beam_delta_analysis,
            "reinforcement_delta_analysis": reinforcement_delta_analysis,
            "diameter_delta_analysis": diameter_delta_analysis,
            "steel_delta_analysis": steel_delta_analysis,
            "schedule_delta_analysis": schedule_delta_analysis,
            "recovery_contribution_analysis": recovery_contribution_analysis,
            "engineering_health_delta": engineering_health_delta,
            "recovery_effectiveness": recovery_effectiveness,
            "qa_dashboard_impact": qa_dashboard_impact,
            "top_contributors": top_contributors,
            "no_regression": no_regression,
            "recovery_impact_summary": recovery_impact_summary,
        }

        validator = ValidationExportValidator()
        result["validation_checks"] = validator.validate_result(result)
        result["recovery_validation_report"] = reporting.build_report(result)

        output_dir = self._paths["output_dir"]
        ValidationExporter.export_all(output_dir, result)
        result["export_validation"] = validator.validate_exports(output_dir, EXPORT_FILES)

        validation_checks = (
            (result["validation_checks"].get("checks") or [])
            + (result["export_validation"].get("checks") or [])
        )
        failed = [item for item in validation_checks if item.get("status") == "FAIL"]
        result["validation_report"] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "status": "PASS" if not failed else "FAIL",
            "checks": validation_checks,
            "summary": {
                "total_checks": len(validation_checks),
                "passed": len(validation_checks) - len(failed),
                "failed": len(failed),
            },
        }
        result["recovery_validation_report"] = reporting.build_report(result)
        ValidationExporter.export_all(output_dir, result)
        ValidationExporter.print_summary(result)
        return result
