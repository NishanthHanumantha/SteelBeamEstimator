"""
Phase QA.1.1 — Module 13: Diagnostics Reporter
Build a 12-section structured diagnostics report.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    DiagnosticsSummary, EngineeringDiagnostic, ImpactLevel, PriorityFix
)
from diagnostics_statistics import DiagnosticsStatistics


class DiagnosticsReporter:
    """Builds the full 12-section diagnostics report."""

    def __init__(self) -> None:
        self._stats = DiagnosticsStatistics()

    def build_report(
        self,
        diagnostics: List[EngineeringDiagnostic],
        priority_fixes: List[PriorityFix],
        summary: DiagnosticsSummary,
        qa1_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        stats = self._stats.compute_all(diagnostics)

        bbs_diags = [d for d in diagnostics if "BBS" in d.error_type or
                     d.pipeline_stage in ("BBS_GENERATION",)]
        feature_diags = [d for d in diagnostics if "FEAT" in d.diagnostic_id or
                         "FEATURE" in d.error_type or "TOP_BOTTOM" in d.error_type]
        pattern_diags = [d for d in diagnostics if "PATTERN" in d.diagnostic_id or
                         "PATTERN" in d.error_type]
        beam_diags = [d for d in diagnostics if "BEAM" in d.diagnostic_id and
                      "FEAT" not in d.diagnostic_id and "PATTERN" not in d.diagnostic_id]

        return {
            "model_version": summary.model_version,
            "benchmark_id": summary.benchmark_id,
            "drawing_name": summary.drawing_name,
            "timestamp": summary.timestamp,

            # ── Section 1: Executive Summary ─────────────────────────────────
            "section_1_executive_summary": {
                "title": "Phase QA.1.1 — Engineering Error Diagnostics Summary",
                "total_diagnostics": summary.total_diagnostics,
                "total_qa1_errors_diagnosed": summary.total_qa1_errors_diagnosed,
                "total_kpi_gap_diagnostics": summary.total_kpi_gap_diagnostics,
                "validation_passed": summary.validation_passed,
                "diagnostic_confidence": summary.overall_diagnostic_confidence,
                "top_root_cause": _top_key(stats["root_cause_distribution"]),
                "top_pipeline_stage": _top_key(stats["pipeline_stage_distribution"]),
                "highest_priority_fix": (
                    priority_fixes[0].fix_title if priority_fixes else "N/A"
                ),
                "overall_status": _overall_status(summary),
                "note": (
                    "Phase QA.1.1 diagnoses WHY each engineering error occurred. "
                    "All diagnostics are deterministic and read-only. "
                    "No pipeline outputs were modified."
                ),
            },

            # ── Section 2: Diagnostic Summary ────────────────────────────────
            "section_2_diagnostic_summary": {
                "total_diagnostics": len(diagnostics),
                "error_type_distribution": stats["error_type_distribution"],
                "beam_diagnostic_counts": stats["beam_diagnostic_counts"],
                "average_confidence": stats["average_confidence"],
                "average_impact_score": stats["average_impact_score"],
            },

            # ── Section 3: Root Cause Distribution ───────────────────────────
            "section_3_root_cause_distribution": {
                "distribution": stats["root_cause_distribution"],
                "primary_root_cause": _top_key(stats["root_cause_distribution"]),
                "breakdown": [
                    {"root_cause": rc, "count": cnt, "pct": _pct(cnt, len(diagnostics))}
                    for rc, cnt in stats["root_cause_distribution"].items()
                ],
            },

            # ── Section 4: Pipeline Stage Distribution ────────────────────────
            "section_4_pipeline_stage_distribution": {
                "distribution": stats["pipeline_stage_distribution"],
                "highest_error_stage": _top_key(stats["pipeline_stage_distribution"]),
                "breakdown": [
                    {"stage": st, "count": cnt, "pct": _pct(cnt, len(diagnostics))}
                    for st, cnt in stats["pipeline_stage_distribution"].items()
                ],
            },

            # ── Section 5: Beam Diagnostics ───────────────────────────────────
            "section_5_beam_diagnostics": {
                "count": len(beam_diags),
                "diagnostics": [_diag_summary(d) for d in beam_diags],
            },

            # ── Section 6: Feature Diagnostics ────────────────────────────────
            "section_6_feature_diagnostics": {
                "count": len(feature_diags),
                "diagnostics": [_diag_summary(d) for d in feature_diags],
            },

            # ── Section 7: Pattern Diagnostics ────────────────────────────────
            "section_7_pattern_diagnostics": {
                "count": len(pattern_diags),
                "diagnostics": [_diag_summary(d) for d in pattern_diags],
            },

            # ── Section 8: BBS Diagnostics ────────────────────────────────────
            "section_8_bbs_diagnostics": {
                "count": len(bbs_diags),
                "diagnostics": [_diag_summary(d) for d in bbs_diags],
            },

            # ── Section 9: Impact Assessment ──────────────────────────────────
            "section_9_impact_assessment": {
                "severity_distribution": stats["severity_distribution"],
                "impact_distribution": stats["impact_distribution"],
                "max_impact_level": _top_key(stats["impact_distribution"]),
                "critical_count": stats["impact_distribution"].get("CRITICAL", 0),
                "high_count": stats["impact_distribution"].get("HIGH", 0),
                "medium_count": stats["impact_distribution"].get("MEDIUM", 0),
                "low_count": stats["impact_distribution"].get("LOW", 0),
            },

            # ── Section 10: Recommendations ───────────────────────────────────
            "section_10_recommendations": {
                "count": len(set(d.recommended_fix for d in diagnostics)),
                "by_root_cause": _recommendations_by_root_cause(diagnostics),
            },

            # ── Section 11: Priority Fix List ─────────────────────────────────
            "section_11_priority_fix_list": {
                "count": len(priority_fixes),
                "fixes": [_fix_entry(f) for f in priority_fixes],
            },

            # ── Section 12: Future Accuracy Improvements ──────────────────────
            "section_12_future_accuracy_improvements": _future_improvements(
                priority_fixes, qa1_summary
            ),
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _diag_summary(d: EngineeringDiagnostic) -> Dict[str, Any]:
    return {
        "diagnostic_id": d.diagnostic_id,
        "beam_id": d.beam_id,
        "error_type": d.error_type,
        "root_cause": d.root_cause,
        "pipeline_stage": d.pipeline_stage,
        "severity": d.severity,
        "impact_level": d.impact_level,
        "confidence": d.confidence,
        "recommended_fix": d.recommended_fix[:200],
        "priority_rank": d.priority_rank,
    }


def _fix_entry(f: PriorityFix) -> Dict[str, Any]:
    return {
        "rank": f.rank,
        "fix_title": f.fix_title,
        "error_type": f.error_type,
        "root_cause": f.root_cause,
        "pipeline_stage": f.pipeline_stage,
        "frequency": f.frequency,
        "severity": f.severity,
        "priority_score": f.priority_score,
        "expected_improvement_pct": f.expected_improvement_pct,
        "kpi_affected": f.kpi_affected,
        "recommendation": f.recommendation,
        "affected_beams": f.affected_beams,
    }


def _top_key(d: Dict[str, int]) -> str:
    return next(iter(d), "N/A")


def _pct(cnt: int, total: int) -> float:
    return round(100 * cnt / total, 2) if total else 0.0


def _overall_status(summary: DiagnosticsSummary) -> str:
    if not summary.validation_passed:
        return "VALIDATION_FAILED"
    if summary.total_diagnostics == 0:
        return "NO_ERRORS_DIAGNOSED"
    return "DIAGNOSTICS_COMPLETE"


def _recommendations_by_root_cause(diagnostics: List[EngineeringDiagnostic]) -> List[Dict]:
    seen: Dict[str, str] = {}
    for d in diagnostics:
        if d.root_cause not in seen:
            seen[d.root_cause] = d.recommended_fix
    return [{"root_cause": rc, "recommendation": rec[:300]}
            for rc, rec in seen.items()]


def _future_improvements(fixes: List[PriorityFix], qa1_summary: Dict) -> Dict[str, Any]:
    current_score = qa1_summary.get("weighted_score", 0.0)
    max_improvement = sum(f.expected_improvement_pct for f in fixes[:3])
    return {
        "current_weighted_score": current_score,
        "top_3_fix_expected_improvement": round(max_improvement, 2),
        "projected_score_after_fixes": round(min(100.0, current_score + max_improvement), 2),
        "recommended_sprint_order": [
            {"rank": f.rank, "fix": f.fix_title, "kpi": f.kpi_affected,
             "expected_improvement_pct": f.expected_improvement_pct}
            for f in fixes[:5]
        ],
        "note": (
            "Projected improvements are deterministic estimates based on "
            "root cause frequency and engineering impact. "
            "Actual improvement depends on implementation quality."
        ),
    }
