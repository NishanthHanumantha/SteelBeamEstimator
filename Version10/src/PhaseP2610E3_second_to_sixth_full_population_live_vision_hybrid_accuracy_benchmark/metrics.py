"""KPI block adapters. Diameter numerators preserved for pooling. No GT in runtime resolution."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.subset_kpis import (
    semantic_field_breakdown,
    split_scores,
)


def kpi_block(k: Dict[str, Any]) -> Dict[str, Any]:
    if not k:
        return {}
    beam = k.get("beam_identification") or {}
    bar = k.get("bar_identification") or {}
    correct = k.get("correct_of_detected") or {}
    dia = k.get("diameter_identification") or {}
    steel = k.get("steel") or {}
    overall = k.get("overall") or {}
    return {
        "beam_identification_percent": beam.get("beam_identification_percent"),
        "bar_identification_percent": bar.get("bar_identification_percent"),
        "correct_of_detected_percent": correct.get("correct_of_detected_percent"),
        "diameter_identification_percent": dia.get("diameter_identification_percent"),
        "weight_accuracy_percent": steel.get("weight_accuracy_percent"),
        "overall_accuracy_percent": overall.get("overall_accuracy_percent"),
        "hybrid_total_kg": steel.get("hybrid_total_kg"),
        "benchmark_total_kg": steel.get("benchmark_total_kg"),
        "absolute_error_kg": steel.get("absolute_error_kg"),
        "signed_error_kg": steel.get("signed_error_kg"),
        "beam_n": beam.get("numerator"),
        "beam_d": beam.get("denominator"),
        "bar_n": bar.get("numerator"),
        "bar_d": bar.get("denominator"),
        "correct_n": correct.get("numerator"),
        "correct_d": correct.get("denominator"),
        "diameter_n": dia.get("numerator"),
        "diameter_d": dia.get("denominator"),
        "taxonomy": correct.get("taxonomy"),
        "formula_beam": beam.get("formula"),
        "formula_bar": bar.get("formula"),
        "formula_correct": correct.get("formula"),
        "formula_diameter": dia.get("formula"),
        "formula_weight": steel.get("formula"),
        "formula_overall": overall.get("formula"),
    }


def cohort_block(split: Dict[str, Any]) -> Dict[str, Any]:
    if not split:
        return {"applicable": False, "reason": "NOT_APPLICABLE", "kpis": None}
    if not split.get("applicable"):
        return {"applicable": False, "reason": split.get("reason") or "NOT_APPLICABLE", "kpis": None}
    return {"applicable": True, "reason": None, "kpis": kpi_block(split.get("kpis") or {})}


def score_set(*, drawing_set: str, estimator, model_wb, hybrid_ids: Iterable[str], fallback_ids: Iterable[str]) -> Dict[str, Any]:
    splits = split_scores(
        drawing_set=drawing_set,
        estimator=estimator,
        model_full=model_wb,
        hybrid_ids=hybrid_ids,
        fallback_ids=fallback_ids,
    )
    return {
        "FULL_POPULATION": cohort_block(splits.get("FULL_POPULATION") or {}),
        "HYBRID_ONLY": cohort_block(splits.get("HYBRID_ONLY") or {}),
        "FALLBACK_ONLY": cohort_block(splits.get("FALLBACK_ONLY") or {}),
        "semantic_fields": semantic_field_breakdown(((splits.get("FULL_POPULATION") or {}).get("kpis") or {})),
        "raw_splits": splits,
    }


__all__ = ["cohort_block", "kpi_block", "score_set"]
