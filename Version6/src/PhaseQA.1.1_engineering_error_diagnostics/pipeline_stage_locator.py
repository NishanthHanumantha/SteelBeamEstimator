"""
Phase QA.1.1 — Module 2: Pipeline Stage Locator
Determine the earliest pipeline stage where the prediction diverged.
Earliest divergence wins.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from diagnostic_models import EngineeringDiagnostic, PipelineStage
from pipeline_trace_loader import PipelineTraceLoader


class PipelineStageLocator:
    """Locates the originating pipeline stage for each diagnostic."""

    def __init__(self) -> None:
        self._tracer = PipelineTraceLoader()

    def locate(
        self,
        diagnostic: EngineeringDiagnostic,
        l2_by_beam: Dict[str, Any],
        l21_by_beam: Dict[str, Any],
        l3_by_beam: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Return the earliest pipeline stage where this error originated."""
        stage = self._tracer.locate_stage(
            error_type=diagnostic.error_type,
            beam_id=diagnostic.beam_id,
            l2_by_beam=l2_by_beam,
            l21_by_beam=l21_by_beam,
            l3_by_beam=l3_by_beam,
            additional_context=additional_context,
        )
        return stage

    def locate_all(
        self,
        diagnostics: List[EngineeringDiagnostic],
        l2_by_beam: Dict[str, Any],
        l21_by_beam: Dict[str, Any],
        l3_by_beam: Dict[str, Any],
    ) -> None:
        """In-place: assign pipeline_stage and downstream_modules to each diagnostic."""
        for d in diagnostics:
            stage = self.locate(d, l2_by_beam, l21_by_beam, l3_by_beam)
            d.pipeline_stage = stage
            if not d.downstream_modules:
                d.downstream_modules = self._tracer.get_downstream(stage)

    def pick_earliest(self, stage_a: str, stage_b: str) -> str:
        """Return the earlier of two pipeline stages."""
        return stage_a if PipelineStage.index(stage_a) <= PipelineStage.index(stage_b) else stage_b

    @staticmethod
    def distribution(diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for d in diagnostics:
            dist[d.pipeline_stage] = dist.get(d.pipeline_stage, 0) + 1
        return dict(sorted(dist.items(), key=lambda kv: PipelineStage.index(kv[0])))

    def stage_description(self, stage: str) -> str:
        return self._tracer.get_stage_description(stage)
