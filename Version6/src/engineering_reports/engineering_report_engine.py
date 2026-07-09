"""Engineering report model engine — Phase I.16."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_reports.engineering_report_builder import EngineeringReportBuilder
from src.engineering_reports.engineering_report_registry import EngineeringReportRegistry
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class EngineeringReportEngine:
    """Copy BeamSchedule outputs into technology-independent report models."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._builder = EngineeringReportBuilder()

    def determine(
        self,
        beam_schedule_records: List[dict[str, Any]],
        beam_schedule_registry: dict[str, Any] | None = None,
        quantity_records: List[dict[str, Any]] | None = None,
        project_workspace: dict[str, Any] | None = None,
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
        generation_timestamp: str | None = None,
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        _ = (beam_schedule_registry, self._cache, self._dependency_graph)
        timestamp = generation_timestamp or datetime.now(timezone.utc).isoformat()
        report_records = self._builder.build_reports(
            beam_schedule_records,
            quantity_records=quantity_records,
            project_workspace=project_workspace,
            drawing_models=drawing_models,
            generation_timestamp=timestamp,
        )
        registry = EngineeringReportRegistry()
        for record in report_records:
            registry.register(record)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = EngineeringReportRegistry.build_project_registry(
            report_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return report_records, {
            "engineering_report_results": report_records,
            "engineering_report_registry": project_registry,
        }

    @staticmethod
    def build_project_exports(
        report_records: List[dict[str, Any]],
        report_registry: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "engineering_report_results": report_records,
            "engineering_report_registry": report_registry,
        }
