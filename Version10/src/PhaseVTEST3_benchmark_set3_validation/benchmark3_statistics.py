"""
benchmark3_statistics.py — Aggregate statistics for V.TEST.3.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

from typing import Any, Dict, List

from benchmark3_models import PipelineRunResult, ReadinessScore


class Benchmark3Statistics:

    def collect(
        self,
        pipeline: PipelineRunResult,
        discovery: Dict[str, Any],
        beams: Dict[str, Any],
        reinf: Dict[str, Any],
        interp: Dict[str, Any],
        bars: Dict[str, Any],
        prod: Dict[str, Any],
        readiness_scores: List[ReadinessScore],
        overall_score: float,
    ) -> Dict[str, Any]:
        return {
            "model_version": "8.1.1",
            "benchmark_id": "BENCHMARK::DRAWING_3_V8",
            "pipeline": {
                "stages_executed": pipeline.stages_executed,
                "stages_passed": pipeline.stages_passed,
                "stages_failed": pipeline.stages_failed,
                "success_rate_pct": pipeline.success_rate_pct,
                "total_elapsed_seconds": pipeline.total_elapsed_seconds,
                "stage_summary": [
                    {
                        "id": s.stage_id,
                        "name": s.stage_name,
                        "success": s.success,
                        "elapsed_s": s.elapsed_seconds,
                    }
                    for s in pipeline.stages
                ],
            },
            "discovery": discovery,
            "beams": beams,
            "reinforcement": reinf,
            "interpretation": interp,
            "engineering_bars": bars,
            "production": prod,
            "readiness": {
                "overall_score": overall_score,
                "dimensions": [
                    {"dimension": s.dimension, "score": s.score, "detail": s.detail}
                    for s in readiness_scores
                ],
            },
        }
