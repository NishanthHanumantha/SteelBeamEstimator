"""KPI block adapters. Diameter numerators preserved for pooling. No GT in runtime resolution."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.subset_kpis import (
    semantic_field_breakdown,
    split_scores,
)

_NON_DETECTED = ("MISSING", "EXTRA", "ACCEPTABLE_EXTRA")
_NO_GT = ("EXTRA", "ACCEPTABLE_EXTRA")
_PREFERRED_DIAMETERS = (8, 10, 12, 16, 20, 25, 32)


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


def diameter_label(diameter: Any) -> str:
    try:
        return f"Ø{int(diameter)}"
    except (TypeError, ValueError):
        return str(diameter or "")


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _bench_kg(row: Dict[str, Any]) -> float:
    row = row or {}
    if "benchmark_kg" in row:
        return _as_float(row.get("benchmark_kg"))
    for key, value in row.items():
        if str(key).endswith("_kg") and not str(key).startswith("model") and not str(key).startswith("difference"):
            return _as_float(value)
    return 0.0


def ordered_diameters(keys: Iterable[Any]) -> List[int]:
    present = []
    seen = set()
    for key in keys:
        d = _as_int(key)
        if d is None or d in seen:
            continue
        seen.add(d)
        present.append(d)
    preferred = [d for d in _PREFERRED_DIAMETERS if d in seen]
    rest = sorted(d for d in present if d not in _PREFERRED_DIAMETERS and d >= 8)
    return preferred + rest


def _ratio_percent(numerator: float, denominator: float) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(100.0 * numerator / denominator, 2)


def _identification_note(*, gt: int, detected: int, wrong: int) -> str:
    if detected <= 0:
        return "None detected"
    miss_share = 1.0 - (detected / gt) if gt else 0.0
    wrong_share = wrong / detected
    id_pct = (detected - wrong) / detected
    if detected < 12:
        return "Low volume - percentage unstable"
    if wrong_share >= 0.30:
        return "Frequent diameter swaps"
    if miss_share >= 0.50 and id_pct >= 0.85:
        return "Usually right when found; many missing"
    if miss_share >= 0.50:
        return "Detection is the gap"
    return ""


def _finalize_identification_row(*, diameter: int, gt: int, detected: int, match: int, wrong: int) -> Dict[str, Any]:
    correct = max(detected - wrong, 0)
    return {
        "diameter": diameter,
        "diameter_label": diameter_label(diameter),
        "gt_bar_lines": gt,
        "detected": detected,
        "match": match,
        "wrong_diameter": wrong,
        "diameter_correct": correct,
        "diameter_identification_percent": _ratio_percent(correct, detected),
        "note": _identification_note(gt=gt, detected=detected, wrong=wrong),
        "is_total": False,
        "formula": "(detected - WRONG_DIAMETER) / detected * 100",
    }


def identification_from_bar_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detected-bar diameter ID by estimator line diameter. Not QA.2A diameter_accuracy_pct."""
    buckets: Dict[int, Dict[str, int]] = {}
    for row in rows or []:
        status = str((row or {}).get("status") or "")
        if status in _NO_GT:
            continue
        diameter = _as_int((row or {}).get("diameter"))
        if diameter is None:
            continue
        bucket = buckets.setdefault(diameter, {"gt": 0, "detected": 0, "match": 0, "wrong": 0})
        bucket["gt"] += 1
        if status not in _NON_DETECTED:
            bucket["detected"] += 1
            if status == "MATCH":
                bucket["match"] += 1
            if status == "WRONG_DIAMETER":
                bucket["wrong"] += 1
    out = []
    for diameter in ordered_diameters(buckets):
        bucket = buckets[diameter]
        out.append(
            _finalize_identification_row(
                diameter=diameter,
                gt=bucket["gt"],
                detected=bucket["detected"],
                match=bucket["match"],
                wrong=bucket["wrong"],
            )
        )
    return out


def steel_rows_from_metric7(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[int, Dict[str, float]] = {}
    for row in rows or []:
        diameter = _as_int((row or {}).get("diameter"))
        if diameter is None:
            continue
        bucket = buckets.setdefault(diameter, {"benchmark_kg": 0.0, "model_kg": 0.0})
        bucket["benchmark_kg"] += _bench_kg(row)
        bucket["model_kg"] += _as_float((row or {}).get("model_kg"))
    out = []
    for diameter in ordered_diameters(buckets):
        out.append(_finalize_steel_row(diameter=diameter, **buckets[diameter]))
    return out


def _finalize_steel_row(*, diameter: int, benchmark_kg: float, model_kg: float) -> Dict[str, Any]:
    bench = round(float(benchmark_kg), 3)
    model = round(float(model_kg), 3)
    diff = round(model - bench, 3)
    abs_pct = _ratio_percent(abs(diff), bench) if bench else (100.0 if model else 0.0)
    ratio = _ratio_percent(model, bench)
    return {
        "diameter": diameter,
        "diameter_label": diameter_label(diameter),
        "benchmark_kg": bench,
        "model_kg": model,
        "difference_kg": diff,
        "difference_pct": abs_pct,
        "quantity_ratio_percent": ratio,
        "is_total": False,
        "formula": "quantity_ratio = model_kg / benchmark_kg * 100; not accuracy",
    }


def _identification_total(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    gt = sum(int(r.get("gt_bar_lines") or 0) for r in rows)
    detected = sum(int(r.get("detected") or 0) for r in rows)
    match = sum(int(r.get("match") or 0) for r in rows)
    wrong = sum(int(r.get("wrong_diameter") or 0) for r in rows)
    row = _finalize_identification_row(diameter=0, gt=gt, detected=detected, match=match, wrong=wrong)
    row["diameter"] = None
    row["diameter_label"] = "TOTAL scored Ø8-Ø32"
    row["note"] = "Pooled headline from raw counts"
    row["is_total"] = True
    return row


def _steel_total(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    bench = sum(_as_float(r.get("benchmark_kg")) for r in rows)
    model = sum(_as_float(r.get("model_kg")) for r in rows)
    row = _finalize_steel_row(diameter=0, benchmark_kg=bench, model_kg=model)
    row["diameter"] = None
    row["diameter_label"] = "TOTAL"
    row["is_total"] = True
    return row


def pool_identification_rows(tables: Iterable[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    buckets: Dict[int, Dict[str, int]] = {}
    for table in tables or []:
        for row in table or []:
            if (row or {}).get("is_total"):
                continue
            diameter = _as_int((row or {}).get("diameter"))
            if diameter is None:
                continue
            bucket = buckets.setdefault(diameter, {"gt": 0, "detected": 0, "match": 0, "wrong": 0})
            bucket["gt"] += int((row or {}).get("gt_bar_lines") or 0)
            bucket["detected"] += int((row or {}).get("detected") or 0)
            bucket["match"] += int((row or {}).get("match") or 0)
            bucket["wrong"] += int((row or {}).get("wrong_diameter") or 0)
    rows = [
        _finalize_identification_row(diameter=d, gt=buckets[d]["gt"], detected=buckets[d]["detected"], match=buckets[d]["match"], wrong=buckets[d]["wrong"])
        for d in ordered_diameters(buckets)
    ]
    if rows:
        rows.append(_identification_total(rows))
    return rows


def pool_steel_rows(tables: Iterable[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    buckets: Dict[int, Dict[str, float]] = {}
    for table in tables or []:
        for row in table or []:
            if (row or {}).get("is_total"):
                continue
            diameter = _as_int((row or {}).get("diameter"))
            if diameter is None:
                continue
            bucket = buckets.setdefault(diameter, {"benchmark_kg": 0.0, "model_kg": 0.0})
            bucket["benchmark_kg"] += _bench_kg(row)
            bucket["model_kg"] += _as_float((row or {}).get("model_kg"))
    rows = [_finalize_steel_row(diameter=d, **buckets[d]) for d in ordered_diameters(buckets)]
    if rows:
        rows.append(_steel_total(rows))
    return rows


def diameter_wise_from_split(split: Dict[str, Any]) -> Dict[str, Any]:
    kpis = (split or {}).get("kpis") or {}
    dw = (split or {}).get("diameter_wise") or {}
    ident = identification_from_bar_rows((kpis.get("bar_matching") or {}).get("rows") or [])
    steel = steel_rows_from_metric7(dw.get("steel_rows") or [])
    return {
        "identification_rows": ident,
        "steel_rows": steel,
        "quantity_rows": dw.get("quantity_rows") or [],
        "formula_identification": (
            "QA.2A diameter_accuracy_pct is an alias of bar matching (MATCH / detected) and is not used. "
            "A detected bar is diameter-correct unless status is WRONG_DIAMETER. "
            "GT diameter is the estimator line diameter. "
            "Pooled % uses summed raw counts, not the average of set percentages."
        ),
        "formula_steel": (
            "Quantity ratio = model kg / estimator kg x 100. It is not accuracy. "
            "A ratio above 100% is an overestimate. "
            "This is not the same as diameter identification. Diameter remains excluded from overall."
        ),
    }


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
        "diameter_wise": diameter_wise_from_split(splits.get("FULL_POPULATION") or {}),
        "raw_splits": splits,
    }


__all__ = [
    "cohort_block",
    "diameter_label",
    "diameter_wise_from_split",
    "identification_from_bar_rows",
    "kpi_block",
    "ordered_diameters",
    "pool_identification_rows",
    "pool_steel_rows",
    "score_set",
    "steel_rows_from_metric7",
]
