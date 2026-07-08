"""Engineering Calculation Integration Repair orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.engineering_calculation_integration.bar_identity_registry import BarIdentityRegistryIntegrator
from src.engineering_calculation_integration.calculation_context_integrator import CalculationContextIntegrator
from src.engineering_calculation_integration.cut_length_integrator import CutLengthIntegrator
from src.engineering_calculation_integration.dependency_graph_integrator import DependencyGraphIntegrator
from src.engineering_calculation_integration.export import EXPORT_FILES, IntegrationExporter
from src.engineering_calculation_integration.integration_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    IntegrationCollector,
    default_paths,
)
from src.engineering_calculation_integration.lifecycle_integrator import LifecycleIntegrator
from src.engineering_calculation_integration.production_pipeline_integrator import ProductionPipelineIntegrator
from src.engineering_calculation_integration.reporting import IntegrationReporting
from src.engineering_calculation_integration.validation import IntegrationValidator


class IntegrationEngine:
    """Run production calculation integration repair for recovered bars."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = IntegrationCollector(self._project_root).collect()
        pipeline_result = ProductionPipelineIntegrator(self._project_root).integrate(snapshot)
        model = pipeline_result.get("model") or {}

        bar_identity_registry = BarIdentityRegistryIntegrator.build_registry_report(
            snapshot,
            model.get("bar_identity_results") or [],
            model.get("bar_identity_registry") or {},
            model.get("engineering_calculation_results") or [],
        )
        dependency_graph_integration = DependencyGraphIntegrator().integrate(
            model,
            ProductionPipelineIntegrator(self._project_root)._load_drawing_models(),
            str((snapshot.get("project_workspace") or {}).get("project_id") or ""),
            snapshot.get("recovered_bar_ids") or [],
        )
        calculation_context_integration = CalculationContextIntegrator.build_report(
            snapshot,
            model.get("calculation_contexts") or [],
        )
        cut_length_integration = CutLengthIntegrator.build_report(
            snapshot,
            model.get("cut_length_results") or [],
            model.get("engineering_calculation_results") or [],
        )
        lifecycle_integration = LifecycleIntegrator.build_report(
            snapshot,
            model.get("steel_weight_results") or [],
            model.get("bbs_results") or [],
            model.get("engineering_calculation_results") or [],
        )

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "production_enhancement": True,
            "integration_status": pipeline_result.get("status"),
            "load_status": snapshot.get("load_status"),
            "bar_identity_registry": bar_identity_registry,
            "readiness_registry": pipeline_result.get("readiness_registry"),
            "dependency_graph_integration": dependency_graph_integration,
            "calculation_context_integration": calculation_context_integration,
            "cut_length_integration": cut_length_integration,
            "lifecycle_integration": lifecycle_integration,
            "production_pipeline_integration": {
                "status": pipeline_result.get("status"),
                "integration_mode": pipeline_result.get("integration_mode"),
                "recovered_bar_count": pipeline_result.get("recovered_bar_count"),
                "indexed_bars": pipeline_result.get("indexed_bars"),
                "regression": pipeline_result.get("regression"),
                "contribution": pipeline_result.get("contribution"),
            },
            "contribution": pipeline_result.get("contribution"),
            "regression": pipeline_result.get("regression"),
            "model": model,
        }

        reporting = IntegrationReporting()
        result["integration_statistics"] = reporting.build_statistics(result, snapshot)
        result["integration_health"] = reporting.build_health(result["integration_statistics"])
        result["integration_validation"] = IntegrationValidator().validate(result, snapshot)
        result["integration_summary"] = reporting.build_summary(
            result["integration_statistics"],
            result["integration_health"],
            result["integration_validation"],
            result,
        )
        result["integration_report"] = reporting.build_report(result)

        output_dir = self._paths["output_dir"]
        IntegrationExporter.export_all(output_dir, result)
        result["export_validation"] = IntegrationExporter.validate_exports(output_dir, EXPORT_FILES)
        IntegrationExporter.print_summary(result)
        return result
