"""
Phase QA.1.1 — Module 15: Priority Ranking
Rank fixes by Priority Score = Severity × Engineering Impact × Frequency.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from diagnostic_models import EngineeringDiagnostic, PriorityFix

SEVERITY_SCORE: Dict[str, float] = {
    "CRITICAL": 4.0,
    "HIGH":     3.0,
    "MEDIUM":   2.0,
    "LOW":      1.0,
}

# Expected improvement per root cause (deterministic engineering estimate)
IMPROVEMENT_ESTIMATE: Dict[str, float] = {
    "ASSOCIATION_ERROR":    6.5,   # top/bottom fix → ~6-8% improvement
    "BBS_ERROR":            5.0,   # BBS diameter fix → ~4-6%
    "REFERENCE_DATA_ERROR": 5.0,   # reference data alignment
    "FEATURE_ERROR":        4.5,   # feature extraction fix
    "PATTERN_ERROR":        4.0,   # pattern recogniser fix
    "GEOMETRY_ERROR":       3.5,   # geometry fix
    "PARSER_ERROR":         3.0,   # parser fix
    "CALCULATION_ERROR":    2.5,   # calculation fix
    "DRAWING_ERROR":        2.0,   # source drawing issue
    "UNKNOWN":              1.0,
}

# KPI affected by root cause
ROOT_CAUSE_KPI: Dict[str, str] = {
    "PARSER_ERROR":         "beam_detection",
    "GEOMETRY_ERROR":       "geometry",
    "ASSOCIATION_ERROR":    "top_bottom / beam_assignment",
    "FEATURE_ERROR":        "feature_extraction",
    "PATTERN_ERROR":        "pattern",
    "BBS_ERROR":            "bbs",
    "CALCULATION_ERROR":    "steel_weight",
    "REFERENCE_DATA_ERROR": "bbs / steel_weight",
    "UNKNOWN":              "unknown",
}


class PriorityRanker:
    """Ranks engineering fixes using Priority Score = Severity × Impact × Frequency."""

    def rank(self, diagnostics: List[EngineeringDiagnostic]) -> List[PriorityFix]:
        # Group diagnostics by (root_cause, pipeline_stage, error_type)
        groups: Dict[Tuple, List[EngineeringDiagnostic]] = defaultdict(list)
        for d in diagnostics:
            key = (d.root_cause, d.pipeline_stage, d.error_type)
            groups[key].append(d)

        fixes: List[PriorityFix] = []
        for (root_cause, stage, error_type), group in groups.items():
            freq = len(group)
            max_severity_score = max(SEVERITY_SCORE.get(d.severity, 1.0) for d in group)
            avg_impact = sum(d.impact_score for d in group) / freq
            priority_score = round(max_severity_score * avg_impact * freq, 3)
            exp_improvement = IMPROVEMENT_ESTIMATE.get(root_cause, 1.0)

            # Representative fix title
            title = _fix_title(error_type, root_cause, stage)
            recommendation = group[0].recommended_fix[:200]
            affected_beams = sorted({
                bid.strip()
                for d in group
                for bid in d.beam_id.split(",")
                if bid.strip() not in ("", "ALL", "MULTIPLE")
            })

            fixes.append(PriorityFix(
                rank=0,  # filled after sorting
                fix_title=title,
                error_type=error_type,
                root_cause=root_cause,
                pipeline_stage=stage,
                frequency=freq,
                severity=group[0].severity,
                priority_score=priority_score,
                expected_improvement_pct=exp_improvement,
                kpi_affected=ROOT_CAUSE_KPI.get(root_cause, "unknown"),
                recommendation=recommendation,
                affected_beams=affected_beams,
            ))

        fixes.sort(key=lambda f: f.priority_score, reverse=True)
        for i, fix in enumerate(fixes, 1):
            fix.rank = i

        # Back-fill priority_score and rank on diagnostics
        for d in diagnostics:
            key = (d.root_cause, d.pipeline_stage, d.error_type)
            for fix in fixes:
                if (fix.root_cause, fix.pipeline_stage, fix.error_type) == key:
                    d.priority_score = fix.priority_score
                    d.priority_rank = fix.rank
                    break

        return fixes


def _fix_title(error_type: str, root_cause: str, stage: str) -> str:
    MAP: Dict[str, str] = {
        "BBS_ROW_ERROR":               "Fix BBS Diameter Mapping",
        "KPI_GAP_BBS":                 "Improve BBS Schedule Accuracy",
        "KPI_GAP_TOP_BOTTOM":          "Improve Top/Bottom Bar Classification",
        "TOP_BOTTOM_ERROR":            "Fix Top/Bottom Bar Classification",
        "KPI_GAP_FEATURE_EXTRACTION":  "Improve Feature Extraction Coverage",
        "KPI_GAP_BEAM_ASSIGNMENT":     "Improve Bar Association Accuracy",
        "MISSING_BARS":                "Fix Missing Bar Detection",
        "EXTRA_BARS":                  "Fix Duplicate Bar Suppression",
        "GEOMETRY_ERROR":              "Fix Beam Span Measurement",
        "KPI_GAP_GEOMETRY":            "Review Geometry KPI",
        "MISSING_BEAM":                "Fix Beam Detection",
        "FALSE_POSITIVE_BEAM":         "Fix False-Positive Beam Suppression",
        "WRONG_PATTERN":               "Fix Pattern Classifier",
        "KPI_GAP_PATTERN":             "Improve Pattern Recognition",
        "KPI_GAP_STEEL_WEIGHT":        "Provide Steel Weight Ground Truth",
        "KPI_GAP_DIAMETER":            "Fix Diameter Assignment",
    }
    return MAP.get(error_type, f"Fix {error_type.replace('_', ' ').title()}")
