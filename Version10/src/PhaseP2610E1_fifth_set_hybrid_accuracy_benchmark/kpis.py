"""QA.2A KPI wrappers. Documented formulas. No opaque accuracy."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    FORMULA_BAR_MATCH,
    FORMULA_BEAM_MATCH,
    FORMULA_OVERALL,
    FORMULA_OVERALL_SOURCE,
    FORMULA_STEEL,
    FORMULA_STEEL_SOURCE,
)


def _ensure_qa2a() -> None:
    p = str(Path(__file__).resolve().parents[1] / "PhaseQA.2A_ground_truth_benchmark")
    if p not in sys.path:
        sys.path.insert(0, p)


def compute_kpis(*, drawing_set: str, estimator, model) -> Dict[str, Any]:
    _ensure_qa2a()
    from bar_matcher import BarMatcher  # type: ignore
    from beam_matcher import BeamMatcher  # type: ignore
    from error_classifier import ErrorClassifier  # type: ignore
    from metrics_engine import MetricsEngine  # type: ignore

    beam_m = BeamMatcher().match(estimator, model)
    pairs = BeamMatcher().matched_beam_pairs(estimator, model, beam_m)
    unmatched = [b for b in estimator.beams if b.beam_id in (beam_m.get("missing_ids") or [])]
    bar_m = BarMatcher().match_all(drawing_set, pairs, unmatched)
    metrics = MetricsEngine().compute(drawing_set, estimator, model, beam_m, bar_m)
    errors = ErrorClassifier().classify(drawing_set, beam_m, bar_m, metrics["metric8_overall_steel"])

    m1 = metrics["metric1_beam_detection"]
    m3 = metrics["metric3_bar_detection"]
    m4 = metrics["metric4_bar_accuracy"]
    m8 = metrics["metric8_overall_steel"]
    overall = round(
        (
            float(m1.get("detection_pct") or 0)
            + float(m3.get("detection_pct") or 0)
            + float(m4.get("accuracy_pct") or 0)
            + float(m8.get("accuracy_pct") or 0)
        )
        / 4.0,
        2,
    )

    detected_rows = [r for r in (bar_m.get("rows") or []) if r.get("status") not in ("MISSING", "EXTRA", "ACCEPTABLE_EXTRA")]
    dia_eligible = [r for r in detected_rows if r.get("diameter") and r.get("model_diameter")]
    dia_correct = [r for r in dia_eligible if r.get("diameter") == r.get("model_diameter")]
    dia_pct = round(100.0 * len(dia_correct) / len(dia_eligible), 2) if dia_eligible else 0.0

    status_counts: Dict[str, int] = {}
    for r in bar_m.get("rows") or []:
        st = str(r.get("status") or "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1

    return {
        "beam_identification": {
            "detected_ground_truth_beams": m1.get("detected_beams"),
            "total_ground_truth_beams": m1.get("estimator_beams"),
            "missed_beams": m1.get("undetected_beams"),
            "missed_ids": beam_m.get("missing_ids") or [],
            "extra_ids": beam_m.get("extra_ids") or [],
            "beam_identification_percent": m1.get("detection_pct"),
            "formula": "detected_ground_truth_beams / total_ground_truth_beams * 100",
            "source": FORMULA_BEAM_MATCH,
            "numerator": m1.get("detected_beams"),
            "denominator": m1.get("estimator_beams"),
        },
        "bar_identification": {
            "identified_ground_truth_bars": m3.get("detected_bars"),
            "total_ground_truth_bars": m3.get("estimator_bars"),
            "missed_bars": bar_m.get("missing_bars"),
            "bar_identification_percent": m3.get("detection_pct"),
            "formula": "identified_ground_truth_bars / total_ground_truth_bars * 100",
            "source": FORMULA_BAR_MATCH,
            "numerator": m3.get("detected_bars"),
            "denominator": m3.get("estimator_bars"),
        },
        "correct_of_detected": {
            "fully_matched_detected_bars": m4.get("correct_bars"),
            "total_detected_bars": m4.get("detected_bars"),
            "correct_of_detected_percent": m4.get("accuracy_pct"),
            "formula": "fully_matched_detected_bars / total_detected_bars * 100",
            "source": FORMULA_BAR_MATCH,
            "numerator": m4.get("correct_bars"),
            "denominator": m4.get("detected_bars"),
            "taxonomy": status_counts,
        },
        "diameter_identification": {
            "correct_diameter": len(dia_correct),
            "wrong_diameter": len(dia_eligible) - len(dia_correct),
            "eligible_detected_bars": len(dia_eligible),
            "diameter_identification_percent": dia_pct,
            "formula": "correct_diameter / eligible_detected_bars * 100",
            "source": "QA.2A bar rows with both diameters present; WRONG_DIAMETER excluded from correct",
            "numerator": len(dia_correct),
            "denominator": len(dia_eligible),
        },
        "steel": {
            "hybrid_total_kg": m8.get("model_total_kg"),
            "benchmark_total_kg": m8.get("estimator_total_kg"),
            "absolute_error_kg": round(abs(float(m8.get("difference_kg") or 0)), 3),
            "signed_error_kg": m8.get("difference_kg"),
            "absolute_error_percent": m8.get("difference_pct"),
            "weight_accuracy_percent": m8.get("accuracy_pct"),
            "formula": FORMULA_STEEL,
            "source": FORMULA_STEEL_SOURCE,
            "numerator": "max(0, 100 - abs(hybrid - benchmark) / benchmark * 100)",
            "denominator": "benchmark_kg",
            "raw": m8,
        },
        "overall": {
            "overall_accuracy_percent": overall,
            "components": {
                "beam_identification_percent": m1.get("detection_pct"),
                "bar_identification_percent": m3.get("detection_pct"),
                "correct_of_detected_percent": m4.get("accuracy_pct"),
                "weight_accuracy_percent": m8.get("accuracy_pct"),
            },
            "formula": FORMULA_OVERALL,
            "source": FORMULA_OVERALL_SOURCE,
            "note": "Diameter identification is reported separately and is not in the overall mean.",
        },
        "metrics_engine": metrics,
        "beam_matching": beam_m,
        "bar_matching": bar_m,
        "errors": errors,
    }


def diameter_wise(metrics: Dict[str, Any]) -> Dict[str, Any]:
    qty = (metrics.get("metrics_engine") or {}).get("metric6_diameter_accuracy") or []
    steel = (metrics.get("metrics_engine") or {}).get("metric7_diameter_steel") or []
    return {"quantity_rows": qty, "steel_rows": steel}


__all__ = ["compute_kpis", "diameter_wise"]
