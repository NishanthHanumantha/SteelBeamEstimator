"""
Phase QA.1.1 — Module 11: Engineering Recommendation Engine
Generate deterministic recommendations based on root cause and pipeline stage.
NO AI reasoning — rules only.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Dict, List

from diagnostic_models import EngineeringDiagnostic, PipelineStage, RootCause

# (root_cause, pipeline_stage) → deterministic recommendation template
RULE_TABLE: Dict[tuple, str] = {
    (RootCause.PARSER_ERROR, PipelineStage.DRAWING_PARSER): (
        "Drawing Parser: improve annotation association by tightening the beam-ID "
        "extraction regex and expanding the reference table of valid beam designators. "
        "Add boundary-box filtering to reject phantom elements outside the drawing frame."
    ),
    (RootCause.GEOMETRY_ERROR, PipelineStage.GEOMETRY_ENGINE): (
        "Geometry Engine: review beam axis reconstruction algorithm. "
        "Validate support node identification using known column grid lines. "
        "Apply end-condition snapping to align span endpoints to the nearest "
        "structural grid intersection within ±5 mm."
    ),
    (RootCause.ASSOCIATION_ERROR, PipelineStage.REINFORCEMENT_INTERPRETATION): (
        "Phase L.2 Reinforcement Interpretation: review bar-to-beam association rules. "
        "Refine top/bottom classification threshold: bars with centroid above beam "
        "mid-depth are TOP; bars below are BOTTOM. "
        "Extend role hierarchy logic to handle edge cases for extra bars and side-face bars."
    ),
    (RootCause.ASSOCIATION_ERROR, PipelineStage.GEOMETRY_RECOVERY): (
        "Phase L.2.2 Geometry Recovery: recovered beams (B14–B18) correctly receive "
        "geometry from surrounding evidence but bar data is absent. "
        "Add a post-recovery bar inference step that estimates bar roles from adjacent "
        "span patterns when bar annotations are missing."
    ),
    (RootCause.FEATURE_ERROR, PipelineStage.FEATURE_EXTRACTION): (
        "Phase L.2.1 Feature Extraction: review bar-to-feature mapping pipeline. "
        "Ensure every bar role (TOP_MAIN, BOTTOM_MAIN, STIRRUP, SIDE_FACE) "
        "generates a corresponding feature entry in engineering_feature_database.json. "
        "Add zone assignment for side-face bars using beam depth fraction (< 0.2D from each face)."
    ),
    (RootCause.PATTERN_ERROR, PipelineStage.PATTERN_RECOGNITION): (
        "Phase L.3 Pattern Recognition: review span/continuity/structural-behaviour "
        "classifier decision boundaries. "
        "Re-evaluate the continuity detection heuristic at beam ends: "
        "check if top bars extend past the support node and adjust the "
        "continuity threshold from 50% to 30% of adjacent span."
    ),
    (RootCause.BBS_ERROR, PipelineStage.BBS_GENERATION): (
        "BBS Generation: review bar bending schedule diameter mapping. "
        "Ensure BBS diameter is populated from the drawing annotation "
        "and not from a hardcoded default. "
        "Cross-validate BBS diameter against L.2 bar diameter_mm for each member beam."
    ),
    (RootCause.REFERENCE_DATA_ERROR, PipelineStage.BBS_GENERATION): (
        "BBS Generation / Reference Data: diameter recorded in V5 BBS does not match "
        "the diameter in the L.2 engineering model. "
        "Review V5 Phase I annotation-to-diameter lookup. "
        "Ensure that bar size notation (e.g. T16, Y20, H25) is correctly mapped "
        "to mm using the IS 1786 standard bar size table."
    ),
    (RootCause.CALCULATION_ERROR, PipelineStage.STEEL_CALCULATION): (
        "Steel Calculation: verify density constant (7850 kg/m³), diameter-to-area table "
        "(IS 1786), and the cut-length source (use L.2 span + standard hook/lap allowances). "
        "Ensure quantity field is correctly pulled from the BBS schedule per bar entry."
    ),
    (RootCause.REFERENCE_DATA_ERROR, PipelineStage.STEEL_CALCULATION): (
        "Steel Weight Reference: V5 pipeline has not produced a steel weight result "
        "for this drawing. Run V5 Phase I to completion and add the result to the "
        "benchmark ground truth file to enable this KPI."
    ),
    (RootCause.CALCULATION_ERROR, PipelineStage.BBS_GENERATION): (
        "BBS Cut Length: review cut length formula using span + lap + hook + bend allowances. "
        "Validate against IS 2502 bent bar length calculation procedures."
    ),
    (RootCause.UNKNOWN, PipelineStage.UNKNOWN): (
        "No deterministic recommendation available. "
        "Manual engineering review required. "
        "Collect additional diagnostic evidence from drawing and pipeline outputs."
    ),
}

# Fallback by root_cause only
ROOT_CAUSE_FALLBACK: Dict[str, str] = {
    RootCause.PARSER_ERROR:        "Improve parser annotation extraction accuracy.",
    RootCause.GEOMETRY_ERROR:      "Review geometry engine beam axis and span reconstruction.",
    RootCause.ASSOCIATION_ERROR:   "Improve bar-to-beam and top/bottom association heuristics.",
    RootCause.FEATURE_ERROR:       "Extend feature extraction to cover all bar roles.",
    RootCause.PATTERN_ERROR:       "Refine pattern recognition classifier thresholds.",
    RootCause.BBS_ERROR:           "Fix BBS generation diameter and shape code mapping.",
    RootCause.CALCULATION_ERROR:   "Verify numerical calculation constants and formulas.",
    RootCause.REFERENCE_DATA_ERROR:"Align reference data (V5 BBS) with engineering model (L.2).",
    RootCause.DRAWING_ERROR:       "Manually review source drawing annotations.",
    RootCause.UNKNOWN:             "Manual engineering review required.",
}


class EngineeringRecommendationEngine:
    """
    Generates deterministic recommendations.
    Rules only — no AI inference.
    """

    def recommend(self, diagnostic: EngineeringDiagnostic) -> str:
        key = (diagnostic.root_cause, diagnostic.pipeline_stage)
        template = RULE_TABLE.get(key)
        if template:
            return template

        # Fallback by root cause alone
        fallback = ROOT_CAUSE_FALLBACK.get(diagnostic.root_cause, RULE_TABLE[
            (RootCause.UNKNOWN, PipelineStage.UNKNOWN)
        ])
        return fallback

    def assign_all(self, diagnostics: List[EngineeringDiagnostic]) -> None:
        """In-place: assign recommended_fix to each diagnostic if not already set."""
        for d in diagnostics:
            if not d.recommended_fix:
                d.recommended_fix = self.recommend(d)

    @staticmethod
    def distribution(diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for d in diagnostics:
            key = d.root_cause
            dist[key] = dist.get(key, 0) + 1
        return dict(sorted(dist.items(), key=lambda kv: kv[1], reverse=True))
