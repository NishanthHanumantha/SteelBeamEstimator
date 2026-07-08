"""Engineering Quantity Integration Validation orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.engineering_quantity_validation.bbs_validation import BbsValidator
from src.engineering_quantity_validation.contribution_analysis import ContributionAnalyzer
from src.engineering_quantity_validation.excel_validation import ExcelValidator
from src.engineering_quantity_validation.export import (
    EXPORT_FILES,
    QuantityValidationExporter,
    QuantityValidationExportValidator,
)
from src.engineering_quantity_validation.integration_stage_analyzer import IntegrationStageAnalyzer
from src.engineering_quantity_validation.lifecycle_validation import LifecycleValidator
from src.engineering_quantity_validation.quantity_dependency_analysis import QuantityDependencyAnalyzer
from src.engineering_quantity_validation.quantity_traceability import QuantityTraceabilityBuilder
from src.engineering_quantity_validation.reporting import QuantityIntegrationReporting
from src.engineering_quantity_validation.steel_weight_validation import SteelWeightValidator
from src.engineering_quantity_validation.validation_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    RECOVERY_PHASE,
    QuantityValidationCollector,
    default_paths,
)


class QuantityValidationEngine:
    """Run deterministic read-only quantity integration validation."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = QuantityValidationCollector(self._project_root).collect()
        quantity_traceability = QuantityTraceabilityBuilder().build_all(snapshot)
        integration_stage_analysis = IntegrationStageAnalyzer().analyze_all(snapshot)
        steel_weight_validation = SteelWeightValidator().validate(snapshot)
        bbs_validation = BbsValidator().validate(snapshot)
        excel_validation = ExcelValidator().validate(snapshot)
        lifecycle_validation = LifecycleValidator().validate(snapshot)
        quantity_dependency_analysis = QuantityDependencyAnalyzer().analyze(snapshot)
        quantity_contribution_analysis = ContributionAnalyzer().analyze(
            snapshot,
            steel_weight_validation,
            bbs_validation,
            excel_validation,
            quantity_traceability,
        )

        reporting = QuantityIntegrationReporting()
        integration_matrix = reporting.build_integration_matrix(snapshot, quantity_traceability)
        quantity_root_cause_summary = reporting.build_root_cause_summary(
            quantity_traceability,
            steel_weight_validation,
            lifecycle_validation,
            quantity_dependency_analysis,
        )
        engineering_quantity_health = reporting.build_health(
            quantity_contribution_analysis,
            steel_weight_validation,
            bbs_validation,
            excel_validation,
            quantity_traceability,
        )
        recommendations = reporting.build_recommendations(
            quantity_root_cause_summary,
            lifecycle_validation,
            steel_weight_validation,
            quantity_traceability,
        )
        engineering_quantity_validation_summary = reporting.build_summary(
            snapshot,
            quantity_contribution_analysis,
            quantity_traceability,
            quantity_root_cause_summary,
            engineering_quantity_health,
            recommendations,
        )

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
            "quantity_traceability": quantity_traceability,
            "integration_stage_analysis": integration_stage_analysis,
            "steel_weight_validation": steel_weight_validation,
            "bbs_validation": bbs_validation,
            "excel_validation": excel_validation,
            "lifecycle_validation": lifecycle_validation,
            "quantity_dependency_analysis": quantity_dependency_analysis,
            "quantity_contribution_analysis": quantity_contribution_analysis,
            "integration_matrix": integration_matrix,
            "engineering_quantity_health": engineering_quantity_health,
            "quantity_root_cause_summary": quantity_root_cause_summary,
            "engineering_quantity_validation_summary": engineering_quantity_validation_summary,
        }

        validator = QuantityValidationExportValidator()
        result["validation_checks"] = validator.validate_result(result)

        output_dir = self._paths["output_dir"]
        QuantityValidationExporter.export_all(output_dir, result)
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
        QuantityValidationExporter.export_all(output_dir, result)
        QuantityValidationExporter.print_summary(result)
        return result
