"""Beam reinforcement schedule engine — Phase I.15."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.beam_schedule.beam_schedule_builder import BeamScheduleBuilder
from src.engineering_calculations.beam_schedule.beam_schedule_registry import BeamScheduleRegistry
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class BeamScheduleEngine:
    """Aggregate registry outputs into technology-independent beam schedule records."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._builder = BeamScheduleBuilder()

    def determine(
        self,
        beam_summary_records: List[dict[str, Any]],
        quantity_records: List[dict[str, Any]],
        material_records: List[dict[str, Any]],
        quantity_registry: dict[str, Any] | None = None,
        material_registry: dict[str, Any] | None = None,
        beam_summary_registry: dict[str, Any] | None = None,
        steel_weight_records: List[dict[str, Any]] | None = None,
        bar_group_records: List[dict[str, Any]] | None = None,
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        _ = (
            quantity_registry,
            material_registry,
            beam_summary_registry,
            self._cache,
            self._dependency_graph,
        )
        schedule_records = self._builder.build_schedules(
            beam_summary_records,
            quantity_records,
            material_records,
            steel_weight_records or [],
            bar_group_records or [],
        )
        registry = BeamScheduleRegistry()
        for record in schedule_records:
            registry.register(record)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = BeamScheduleRegistry.build_project_registry(
            schedule_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return schedule_records, {
            "beam_schedule_results": schedule_records,
            "beam_schedule_registry": project_registry,
        }

    @staticmethod
    def build_project_exports(
        schedule_records: List[dict[str, Any]],
        schedule_registry: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "beam_schedule_results": schedule_records,
            "beam_schedule_registry": schedule_registry,
        }
