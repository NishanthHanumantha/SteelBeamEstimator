"""Engineering Coverage Analysis Engine orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.engineering_analysis.beam_coverage_analysis import BeamCoverageAnalyzer
from src.engineering_analysis.calculation_state_analysis import CalculationStateAnalyzer
from src.engineering_analysis.coverage_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    CoverageCollector,
    default_paths,
)
from src.engineering_analysis.engineering_gap_analysis import EngineeringGapAnalyzer
from src.engineering_analysis.engineering_loss_report import EngineeringLossAnalyzer
from src.engineering_analysis.engineering_statistics import EngineeringStatistics
from src.engineering_analysis.export import EngineeringCoverageValidator, EngineeringExporter
from src.engineering_analysis.pipeline_stage_analyzer import PipelineStageAnalyzer
from src.engineering_analysis.reinforcement_coverage import ReinforcementCoverageAnalyzer


class CoverageAnalysisEngine:
    """Run read-only engineering pipeline coverage analysis."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        collector = CoverageCollector(self._project_root)
        snapshot = collector.collect()

        pipeline_analyzer = PipelineStageAnalyzer()
        pipeline = pipeline_analyzer.analyze(snapshot)

        reinforcement_analyzer = ReinforcementCoverageAnalyzer()
        reinforcement = reinforcement_analyzer.analyze(snapshot)

        calculation_analyzer = CalculationStateAnalyzer()
        calculation_states = calculation_analyzer.analyze(snapshot)

        beam_analyzer = BeamCoverageAnalyzer()
        beam_coverage = beam_analyzer.analyze(snapshot)

        loss_analyzer = EngineeringLossAnalyzer()
        losses = loss_analyzer.analyze(snapshot, pipeline)

        gap_analyzer = EngineeringGapAnalyzer()
        gaps = gap_analyzer.analyze(
            reinforcement,
            beam_coverage,
            calculation_states,
            pipeline,
        )

        statistics_builder = EngineeringStatistics()
        aggregates = statistics_builder.build(
            snapshot,
            pipeline,
            reinforcement,
            calculation_states,
            beam_coverage,
            losses,
            gaps,
        )

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "generated_workbook": snapshot.get("generated_workbook"),
            "estimator_workbook": snapshot.get("estimator_workbook"),
            "engineering_code_modified": False,
            "engineering_pipeline_frozen": True,
            "parser_executed": False,
            "dxf_accessed": False,
            "read_only_analysis": True,
            "load_status": snapshot.get("load_status"),
            "stage_coverage": pipeline.get("stage_coverage"),
            "pipeline_funnel": pipeline.get("pipeline_funnel"),
            "beam_coverage_report": beam_coverage,
            "reinforcement_categories": reinforcement.get("categories"),
            "bar_type_coverage": reinforcement.get("bar_type_coverage"),
            "diameter_engineering_coverage": reinforcement.get("diameter_engineering_coverage"),
            "calculation_state_analysis": calculation_states,
            "engineering_gap_analysis": gaps,
            "engineering_loss_report": losses,
            "engineering_health_score": aggregates.get("engineering_health_score"),
            "root_cause_summary": aggregates.get("root_cause_summary"),
            "statistics": aggregates.get("statistics"),
        }

        output_dir = self._paths["output_dir"]
        EngineeringExporter.export_all(output_dir, result)
        validation = EngineeringCoverageValidator().validate(result)
        export_validation = EngineeringCoverageValidator().validate_exports(output_dir, result)
        result["validation_report"] = validation
        result["export_validation"] = export_validation
        EngineeringExporter.print_summary(result)
        return result
