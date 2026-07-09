"""Beam reinforcement summary engine — Phase I.12."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.beam_summary.beam_summary_builder import BeamSummaryBuilder
from src.engineering_calculations.beam_summary.beam_summary_registry import BeamSummaryRegistry
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class BeamSummaryEngine:
    """Aggregate engineering reinforcement outputs into beam-level summaries."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._builder = BeamSummaryBuilder()

    def determine(
        self,
        beams: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        weight_records: List[dict[str, Any]],
        bbs_records: List[dict[str, Any]],
        group_records: List[dict[str, Any]],
        identity_records: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        results: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        bars_by_beam = self._index_bars_by_beam(bars)
        registry = BeamSummaryRegistry()
        summary_records: List[dict[str, Any]] = []

        sorted_beams = sorted(beams, key=lambda item: str(item.get("beam_id", "")))
        for beam in sorted_beams:
            beam_id = str(beam.get("beam_id", ""))
            beam_bars = bars_by_beam.get(beam_id, [])
            record = self._builder.build(
                beam,
                beam_bars,
                weight_records,
                bbs_records,
                group_records,
                identity_records,
                contexts,
                results,
            )
            record["beam_summary_id"] = registry.next_id()
            registry.register(record)
            summary_records.append(record)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = BeamSummaryRegistry.build_project_registry(
            summary_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        return summary_records, {
            "beam_summary_results": summary_records,
            "beam_summary_registry": project_registry,
        }

    @staticmethod
    def _index_bars_by_beam(bars: List[dict[str, Any]]) -> dict[str, List[dict[str, Any]]]:
        mapping: dict[str, List[dict[str, Any]]] = defaultdict(list)
        for bar in bars:
            beam_id = str(bar.get("beam_id", ""))
            if beam_id:
                mapping[beam_id].append(bar)
        for beam_id in mapping:
            mapping[beam_id] = sorted(
                mapping[beam_id],
                key=lambda item: str(item.get("bar_id", "")),
            )
        return mapping

    @staticmethod
    def build_project_exports(
        summary_records: List[dict[str, Any]],
        summary_registry: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "beam_summary_results": summary_records,
            "beam_summary_registry": summary_registry,
        }
