"""Orchestrate drawing interpretation audit — Phase QA.3."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

from src.estimator_validation.audit_types import GENERATED_WORKBOOK_REL
from src.estimator_validation.drawing_interpretation.drawing_callout_extractor import DrawingCalloutExtractor
from src.estimator_validation.drawing_interpretation.drawing_loader import DrawingLoader
from src.estimator_validation.drawing_interpretation.estimator_interpretation_builder import (
    EstimatorInterpretationBuilder,
)
from src.estimator_validation.drawing_interpretation.interpretation_matcher import InterpretationMatcher
from src.estimator_validation.drawing_interpretation.interpretation_trace import InterpretationTraceBuilder
from src.estimator_validation.drawing_interpretation.interpretation_types import default_paths
from src.estimator_validation.drawing_interpretation.pipeline_interpretation_builder import (
    PipelineInterpretationBuilder,
)


class InterpretationAuditBuilder:
    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.loader = DrawingLoader(project_root)
        self.callout_extractor = DrawingCalloutExtractor()
        self.estimator_builder = EstimatorInterpretationBuilder()
        self.pipeline_builder = PipelineInterpretationBuilder()
        self.matcher = InterpretationMatcher()
        self.trace_builder = InterpretationTraceBuilder()

    def build(self) -> dict[str, Any]:
        data = self.loader.load_all()
        generated_workbook = self.paths["generated_workbook"]

        estimator = self.estimator_builder.build(
            self.paths["estimator_workbook"],
            generated_workbook,
        )
        beam_marks = sorted(estimator.keys(), key=lambda mark: int(mark[1:]))
        drawing = self.callout_extractor.extract_all(data, beam_marks)
        pipeline = self.pipeline_builder.build(data, beam_marks)

        matching = self.matcher.match_beams(drawing, estimator, pipeline)
        engineering_decisions = self.matcher.detect_engineering_decisions(matching, drawing)
        engineering_concepts = self.matcher.build_engineering_concepts(matching)
        length_report = self.matcher.build_length_interpretation(
            data,
            generated_workbook,
            self.paths["estimator_workbook"],
        )
        interpretation_trace = self.trace_builder.build(estimator, drawing, pipeline, matching)
        root_cause_matrix = self.matcher.build_root_cause_matrix(matching)

        statistics = self._statistics(matching, interpretation_trace, engineering_decisions, length_report)

        return {
            "phase": "Phase QA.3",
            "interpretation_version": "1.0.0",
            "estimator_workbook": str(self.paths["estimator_workbook"]),
            "generated_workbook": str(generated_workbook),
            "drawing_interpretation": {mark: item.to_dict() for mark, item in drawing.items()},
            "estimator_interpretation": {mark: item.to_dict() for mark, item in estimator.items()},
            "pipeline_interpretation": {mark: item.to_dict() for mark, item in pipeline.items()},
            "interpretation_matching": matching,
            "engineering_concepts": engineering_concepts,
            "engineering_decisions": engineering_decisions,
            "length_interpretation_report": length_report,
            "interpretation_trace": interpretation_trace,
            "root_cause_matrix": root_cause_matrix,
            "interpretation_statistics": statistics,
            "pipeline_data_loaded": data.get("load_status", {}),
            "beam_marks": beam_marks,
        }

    @staticmethod
    def _statistics(matching, trace, decisions, length_report) -> dict[str, Any]:
        entries = matching.get("entries", [])
        diff_count = sum(
            1
            for item in entries
            if item.get("classification")
            not in {"DRAWING_AND_ESTIMATOR_AND_PIPELINE", "DRAWING_AND_ESTIMATOR_ONLY", "DRAWING_AND_PIPELINE_ONLY"}
        )
        return {
            "beam_count": len({item.get("beam_mark") for item in entries}),
            "concept_count": matching.get("entry_count", 0),
            "classification_distribution": matching.get("classification_distribution", {}),
            "root_cause_distribution": matching.get("root_cause_distribution", {}),
            "interpretation_difference_count": diff_count,
            "engineering_decision_count": decisions.get("decision_count", 0),
            "trace_count": trace.get("trace_count", 0),
            "length_beam_count": length_report.get("beam_count", 0),
            "confidence": "HIGH",
        }
