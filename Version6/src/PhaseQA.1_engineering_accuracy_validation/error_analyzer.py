"""
Phase QA.1 — Module 11: Error Analyzer
Automatically identify, categorize, and rank errors by impact.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List

from benchmark_models import ErrorEntry


class ErrorAnalyzer:
    """Identifies and ranks engineering errors from validator results."""

    def analyze(
        self,
        beam_result: Dict[str, Any],
        reinforcement_result: Dict[str, Any],
        geometry_result: Dict[str, Any],
        feature_result: Dict[str, Any],
        pattern_result: Dict[str, Any],
        bbs_result: Dict[str, Any],
        steel_weight_result: Dict[str, Any],
    ) -> Dict[str, Any]:

        errors: List[ErrorEntry] = []

        # ── Missing Beams ─────────────────────────────────────────────────
        for bid in beam_result.get("missing_beams", []):
            errors.append(ErrorEntry(
                error_type="MISSING_BEAM",
                beam_id=bid,
                description=f"Beam {bid} expected but not detected",
                severity="HIGH",
                impact_score=10.0,
                kpi_affected="beam_detection",
                details={"beam_id": bid},
            ))

        # ── False Positive Beams ──────────────────────────────────────────
        for bid in beam_result.get("false_positive_beams", []):
            errors.append(ErrorEntry(
                error_type="FALSE_POSITIVE_BEAM",
                beam_id=bid,
                description=f"Beam {bid} detected but not expected",
                severity="HIGH",
                impact_score=8.0,
                kpi_affected="beam_detection",
                details={"beam_id": bid},
            ))

        # ── Incorrect Beam Assignment / Missing Bars ──────────────────────
        for brec in reinforcement_result.get("beam_results", []):
            bid = brec["beam_id"]
            missing = brec.get("missing", 0)
            extra = brec.get("extra", 0)
            if missing > 0:
                errors.append(ErrorEntry(
                    error_type="MISSING_BARS",
                    beam_id=bid,
                    description=f"{missing} bars missing in {bid}",
                    severity="HIGH" if missing > 2 else "MEDIUM",
                    impact_score=min(9.0, 3.0 * missing),
                    kpi_affected="beam_assignment",
                    details={"missing_count": missing, "beam_id": bid},
                ))
            if extra > 0:
                errors.append(ErrorEntry(
                    error_type="EXTRA_BARS",
                    beam_id=bid,
                    description=f"{extra} extra bars detected in {bid}",
                    severity="MEDIUM",
                    impact_score=min(6.0, 2.0 * extra),
                    kpi_affected="beam_assignment",
                    details={"extra_count": extra, "beam_id": bid},
                ))

        # ── Geometry Errors ────────────────────────────────────────────────
        for grec in geometry_result.get("error_records", []):
            if not grec.within_tolerance:
                errors.append(ErrorEntry(
                    error_type="GEOMETRY_ERROR",
                    beam_id=grec.beam_id,
                    description=f"{grec.beam_id} {grec.field}: error {grec.absolute_error_mm:.1f}mm > tolerance",
                    severity="MEDIUM" if grec.absolute_error_mm < 10 else "HIGH",
                    impact_score=min(7.0, grec.absolute_error_mm / 5.0),
                    kpi_affected="geometry",
                    details={
                        "field": grec.field,
                        "expected": grec.expected_value,
                        "predicted": grec.predicted_value,
                        "error_mm": grec.absolute_error_mm,
                    },
                ))

        # ── Pattern Errors ────────────────────────────────────────────────
        for prec in pattern_result.get("comparison_records", []):
            if not prec.match and prec.pattern_type == "span_pattern":
                errors.append(ErrorEntry(
                    error_type="WRONG_PATTERN",
                    beam_id=prec.beam_id,
                    description=f"{prec.beam_id} span pattern: expected {prec.expected}, got {prec.predicted}",
                    severity="MEDIUM",
                    impact_score=5.0,
                    kpi_affected="pattern_recognition",
                    details={
                        "pattern_type": prec.pattern_type,
                        "expected": prec.expected,
                        "predicted": prec.predicted,
                    },
                ))

        # ── BBS Errors ────────────────────────────────────────────────────
        for brec in bbs_result.get("bbs_row_records", []):
            if not brec.row_correct:
                parts = []
                if not brec.diameter_match:
                    parts.append("diameter")
                if not brec.quantity_match:
                    parts.append("quantity")
                if not brec.cut_length_match:
                    parts.append("cut_length")
                errors.append(ErrorEntry(
                    error_type="BBS_ROW_ERROR",
                    beam_id=brec.beam_id,
                    description=f"BBS {brec.bbs_id}: mismatch in {', '.join(parts)}",
                    severity="LOW" if len(parts) == 1 else "MEDIUM",
                    impact_score=3.0 * len(parts),
                    kpi_affected="bbs",
                    details={
                        "bbs_id": brec.bbs_id,
                        "mismatch_fields": parts,
                        "notes": brec.notes,
                    },
                ))

        # ── Steel Weight Errors ───────────────────────────────────────────
        for cmp in steel_weight_result.get("beam_comparisons", []):
            pct = cmp.get("percentage_error_pct") or 0
            if pct > 5.0:
                errors.append(ErrorEntry(
                    error_type="WRONG_STEEL_WEIGHT",
                    beam_id=cmp.get("beam_id", "UNKNOWN"),
                    description=f"Steel weight error {pct:.2f}% for {cmp.get('beam_id')}",
                    severity="HIGH" if pct > 15 else "MEDIUM",
                    impact_score=min(8.0, pct / 5),
                    kpi_affected="steel_weight",
                    details=cmp,
                ))

        # Rank by impact_score descending
        errors.sort(key=lambda e: e.impact_score, reverse=True)

        # Summarize by type
        type_counts: Dict[str, int] = {}
        for e in errors:
            type_counts[e.error_type] = type_counts.get(e.error_type, 0) + 1

        severity_counts: Dict[str, int] = {}
        for e in errors:
            severity_counts[e.severity] = severity_counts.get(e.severity, 0) + 1

        return {
            "errors": errors,
            "total_error_count": len(errors),
            "type_counts": type_counts,
            "severity_counts": severity_counts,
            "highest_impact_errors": [
                {
                    "error_type": e.error_type,
                    "beam_id": e.beam_id,
                    "description": e.description,
                    "severity": e.severity,
                    "impact_score": e.impact_score,
                    "kpi_affected": e.kpi_affected,
                }
                for e in errors[:10]
            ],
            "recommendations": self._generate_recommendations(errors, type_counts),
        }

    def _generate_recommendations(
        self, errors: List[ErrorEntry], type_counts: Dict[str, int]
    ) -> List[str]:
        recs: List[str] = []
        if type_counts.get("MISSING_BEAM", 0) > 0:
            recs.append("Improve drawing parser beam detection to capture all beam annotations.")
        if type_counts.get("MISSING_BARS", 0) > 2:
            recs.append("Review L.2 reinforcement interpretation rules for bars with low confidence.")
        if type_counts.get("WRONG_PATTERN", 0) > 0:
            recs.append("Review L.3 span pattern detector thresholds for deep beam / continuous beam disambiguation.")
        if type_counts.get("BBS_ROW_ERROR", 0) > 3:
            recs.append("Investigate cut length and diameter mapping rules in BBS generation pipeline.")
        if type_counts.get("GEOMETRY_ERROR", 0) > 0:
            recs.append("Review geometry extraction accuracy for beams with span tolerance exceedance.")
        if not recs:
            recs.append("All KPIs within acceptable range. No critical actions required.")
        return recs
