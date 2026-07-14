"""
Phase QA.1.1 — Module 10: Impact Assessor
Estimate downstream impact level, affected phases, engineering risk.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import EngineeringDiagnostic, ImpactLevel, PipelineStage

# How many phases are downstream of each stage
DOWNSTREAM_PHASE_COUNT: Dict[str, int] = {
    PipelineStage.DRAWING_PARSER:              7,
    PipelineStage.GEOMETRY_ENGINE:             6,
    PipelineStage.REINFORCEMENT_INTERPRETATION: 5,
    PipelineStage.GEOMETRY_RECOVERY:           4,
    PipelineStage.FEATURE_EXTRACTION:          3,
    PipelineStage.PATTERN_RECOGNITION:         2,
    PipelineStage.BBS_GENERATION:              1,
    PipelineStage.STEEL_CALCULATION:           0,
    PipelineStage.UNKNOWN:                     0,
}

# Engineering risk label per error type
ERROR_ENGINEERING_RISK: Dict[str, str] = {
    "MISSING_BEAM":           "STRUCTURAL — missing beam may be excluded from steel schedule entirely",
    "FALSE_POSITIVE_BEAM":    "QUANTITY — over-estimation of steel requirements",
    "MISSING_BARS":           "STRUCTURAL — reinforcement under-counted; may violate IS 456 limits",
    "EXTRA_BARS":             "QUANTITY — over-estimation of reinforcement and steel weight",
    "GEOMETRY_ERROR":         "DIMENSIONAL — span error propagates to cut length and weight",
    "TOP_BOTTOM_ERROR":       "STRUCTURAL — incorrect moment zone → wrong bar scheduling",
    "BBS_ROW_ERROR":          "SCHEDULE — BBS diameter error → incorrect steel weight per bar",
    "WRONG_PATTERN":          "ANALYSIS — pattern mismatch may lead to wrong moment envelope",
    "WRONG_STEEL_WEIGHT":     "ESTIMATION — procurement quantity error",
    "FEATURE_ERROR":          "ANALYSIS — incomplete feature set may degrade pattern classifier",
    "KPI_GAP_BEAM_DETECTION": "STRUCTURAL — missed beams excluded from structural analysis",
    "KPI_GAP_BEAM_ASSIGNMENT":"REINFORCEMENT — bar count under-detected",
    "KPI_GAP_GEOMETRY":       "DIMENSIONAL — geometry error in span/depth/width",
    "KPI_GAP_FEATURE_EXTRACTION": "ANALYSIS — feature database incomplete",
    "KPI_GAP_TOP_BOTTOM":     "STRUCTURAL — top/bottom misclassification",
    "KPI_GAP_DIAMETER":       "SCHEDULE — diameter mismatch between BBS and bar model",
    "KPI_GAP_PATTERN":        "ANALYSIS — pattern misclassification",
    "KPI_GAP_BBS":            "SCHEDULE — BBS schedule inaccuracy",
    "KPI_GAP_STEEL_WEIGHT":   "ESTIMATION — steel weight not measurable",
}


class ImpactAssessor:
    """Estimates downstream impact for each engineering diagnostic."""

    def assess(self, diagnostic: EngineeringDiagnostic) -> None:
        """In-place: compute impact_level based on impact_score and context."""
        # Re-derive impact score from downstream phase count if not already custom-set
        stage_weight = DOWNSTREAM_PHASE_COUNT.get(diagnostic.pipeline_stage, 0)
        severity_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        severity_val = severity_map.get(diagnostic.severity, 1)

        derived_score = min(10.0, stage_weight * severity_val * 0.45)

        # Use the higher of the diagnostic's own score or derived score
        if derived_score > diagnostic.impact_score:
            diagnostic.impact_score = derived_score

        diagnostic.impact_level = ImpactLevel.from_score(diagnostic.impact_score)

        # Engineering risk note
        risk = ERROR_ENGINEERING_RISK.get(diagnostic.error_type, "UNKNOWN risk")
        if risk not in diagnostic.engineering_notes:
            diagnostic.engineering_notes.append(f"Engineering risk: {risk}")

    def assess_all(self, diagnostics: List[EngineeringDiagnostic]) -> None:
        """In-place: assess impact for all diagnostics."""
        for d in diagnostics:
            self.assess(d)

    def quantity_impact(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, Any]:
        """Summarise quantity impact across all diagnostics."""
        bbs_affected = sum(1 for d in diagnostics
                           if "BBS_GENERATION" in d.downstream_modules or
                           d.pipeline_stage == PipelineStage.BBS_GENERATION)
        steel_affected = sum(1 for d in diagnostics
                             if "STEEL_CALCULATION" in d.downstream_modules or
                             d.pipeline_stage == PipelineStage.STEEL_CALCULATION)
        return {
            "bbs_rows_affected": bbs_affected,
            "steel_calc_affected": steel_affected,
            "max_impact_level": _max_impact(diagnostics),
            "total_downstream_phase_touches": sum(
                len(d.downstream_modules) for d in diagnostics
            ),
        }


def _max_impact(diagnostics: List[EngineeringDiagnostic]) -> str:
    order = [ImpactLevel.CRITICAL, ImpactLevel.HIGH, ImpactLevel.MEDIUM, ImpactLevel.LOW]
    for level in order:
        if any(d.impact_level == level for d in diagnostics):
            return level
    return ImpactLevel.LOW
