"""
Phase QA.1.1 — Engineering Error Diagnostics & Root Cause Analysis Engine
pipeline_trace_loader.py — Load pipeline execution traces and provenance.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from diagnostic_models import PipelineStage


# Deterministic rules mapping error type → most likely pipeline stage
ERROR_TYPE_TO_STAGE: Dict[str, str] = {
    "MISSING_BEAM":          PipelineStage.DRAWING_PARSER,
    "FALSE_POSITIVE_BEAM":   PipelineStage.DRAWING_PARSER,
    "MISSING_BARS":          PipelineStage.REINFORCEMENT_INTERPRETATION,
    "EXTRA_BARS":            PipelineStage.REINFORCEMENT_INTERPRETATION,
    "GEOMETRY_ERROR":        PipelineStage.GEOMETRY_ENGINE,
    "WRONG_PATTERN":         PipelineStage.PATTERN_RECOGNITION,
    "BBS_ROW_ERROR":         PipelineStage.BBS_GENERATION,
    "WRONG_STEEL_WEIGHT":    PipelineStage.STEEL_CALCULATION,
    "FEATURE_ERROR":         PipelineStage.FEATURE_EXTRACTION,
    "WRONG_DIAMETER":        PipelineStage.REINFORCEMENT_INTERPRETATION,
    "WRONG_QUANTITY":        PipelineStage.REINFORCEMENT_INTERPRETATION,
    "TOP_BOTTOM_ERROR":      PipelineStage.REINFORCEMENT_INTERPRETATION,
    "KPI_GAP_BEAM_DETECTION":       PipelineStage.DRAWING_PARSER,
    "KPI_GAP_BEAM_ASSIGNMENT":      PipelineStage.REINFORCEMENT_INTERPRETATION,
    "KPI_GAP_GEOMETRY":             PipelineStage.GEOMETRY_ENGINE,
    "KPI_GAP_FEATURE_EXTRACTION":   PipelineStage.FEATURE_EXTRACTION,
    "KPI_GAP_TOP_BOTTOM":           PipelineStage.REINFORCEMENT_INTERPRETATION,
    "KPI_GAP_DIAMETER":             PipelineStage.REINFORCEMENT_INTERPRETATION,
    "KPI_GAP_QUANTITY":             PipelineStage.REINFORCEMENT_INTERPRETATION,
    "KPI_GAP_PATTERN":              PipelineStage.PATTERN_RECOGNITION,
    "KPI_GAP_BBS":                  PipelineStage.BBS_GENERATION,
    "KPI_GAP_STEEL_WEIGHT":         PipelineStage.STEEL_CALCULATION,
}

# Downstream modules affected by each pipeline stage (in order of appearance)
STAGE_DOWNSTREAM: Dict[str, List[str]] = {
    PipelineStage.DRAWING_PARSER: [
        "GEOMETRY_ENGINE",
        "REINFORCEMENT_INTERPRETATION",
        "GEOMETRY_RECOVERY",
        "FEATURE_EXTRACTION",
        "PATTERN_RECOGNITION",
        "BBS_GENERATION",
        "STEEL_CALCULATION",
    ],
    PipelineStage.GEOMETRY_ENGINE: [
        "REINFORCEMENT_INTERPRETATION",
        "GEOMETRY_RECOVERY",
        "FEATURE_EXTRACTION",
        "PATTERN_RECOGNITION",
        "BBS_GENERATION",
        "STEEL_CALCULATION",
    ],
    PipelineStage.REINFORCEMENT_INTERPRETATION: [
        "GEOMETRY_RECOVERY",
        "FEATURE_EXTRACTION",
        "PATTERN_RECOGNITION",
        "BBS_GENERATION",
        "STEEL_CALCULATION",
    ],
    PipelineStage.GEOMETRY_RECOVERY: [
        "FEATURE_EXTRACTION",
        "PATTERN_RECOGNITION",
        "BBS_GENERATION",
        "STEEL_CALCULATION",
    ],
    PipelineStage.FEATURE_EXTRACTION: [
        "PATTERN_RECOGNITION",
        "BBS_GENERATION",
        "STEEL_CALCULATION",
    ],
    PipelineStage.PATTERN_RECOGNITION: [
        "BBS_GENERATION",
        "STEEL_CALCULATION",
    ],
    PipelineStage.BBS_GENERATION: [
        "STEEL_CALCULATION",
    ],
    PipelineStage.STEEL_CALCULATION: [],
    PipelineStage.UNKNOWN: [],
}


class PipelineTraceLoader:
    """Determines the originating pipeline stage for each error type."""

    def locate_stage(
        self,
        error_type: str,
        beam_id: str,
        l2_by_beam: Dict[str, Any],
        l21_by_beam: Dict[str, Any],
        l3_by_beam: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Return the earliest pipeline stage where divergence occurred."""
        base_stage = ERROR_TYPE_TO_STAGE.get(error_type, PipelineStage.UNKNOWN)

        # Refine based on context
        ctx = additional_context or {}

        if error_type == "BBS_ROW_ERROR":
            # Check if the diameter mismatch is traceable to L.2 or V5
            field = ctx.get("mismatch_fields", [])
            if "diameter" in field:
                # L.2 bar has diameter_mm — the mismatch is in the BBS generation
                # (mapping L.2 bar → BBS role), not in L.2 itself
                return PipelineStage.BBS_GENERATION

        if error_type in ("MISSING_BARS", "EXTRA_BARS"):
            # Check if the beam is a recovered beam (L.2.2)
            if ctx.get("is_recovered"):
                return PipelineStage.GEOMETRY_RECOVERY
            return PipelineStage.REINFORCEMENT_INTERPRETATION

        if error_type == "KPI_GAP_TOP_BOTTOM":
            # Top/bottom error originates in L.2 reinforcement interpretation
            model = l2_by_beam.get(beam_id, {})
            if model:
                return PipelineStage.REINFORCEMENT_INTERPRETATION
            return PipelineStage.GEOMETRY_ENGINE

        if error_type == "KPI_GAP_FEATURE_EXTRACTION":
            # Feature count errors originate in L.2.1
            return PipelineStage.FEATURE_EXTRACTION

        return base_stage

    def get_downstream(self, stage: str) -> List[str]:
        return STAGE_DOWNSTREAM.get(stage, [])

    def get_stage_description(self, stage: str) -> str:
        descriptions = {
            PipelineStage.DRAWING_PARSER:              "Drawing Parser — annotation and element detection",
            PipelineStage.GEOMETRY_ENGINE:             "Geometry Engine — beam span, depth, width reconstruction",
            PipelineStage.REINFORCEMENT_INTERPRETATION:"Phase L.2 — Engineering Reinforcement Interpretation",
            PipelineStage.GEOMETRY_RECOVERY:           "Phase L.2.2 — Geometry Recovery for missing beams",
            PipelineStage.FEATURE_EXTRACTION:          "Phase L.2.1 — Engineering Feature Extraction",
            PipelineStage.PATTERN_RECOGNITION:         "Phase L.3 — Beam Reinforcement Pattern Recognition",
            PipelineStage.BBS_GENERATION:              "BBS Generation — bar bending schedule computation",
            PipelineStage.STEEL_CALCULATION:           "Steel Weight Calculation engine",
            PipelineStage.UNKNOWN:                     "Unknown — requires manual investigation",
        }
        return descriptions.get(stage, "Unknown stage")
