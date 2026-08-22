"""Denominator-weighted pooling. Never average set percentages for headline KPIs."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def ratio_percent(numerator: Any, denominator: Any) -> Optional[float]:
    try:
        n = float(numerator or 0)
        d = float(denominator or 0)
    except (TypeError, ValueError):
        return None
    if d == 0:
        return None
    return 100.0 * n / d


def weight_accuracy_percent(model_kg: Any, benchmark_kg: Any) -> Optional[float]:
    try:
        pred = float(model_kg or 0)
        bench = float(benchmark_kg or 0)
    except (TypeError, ValueError):
        return None
    if bench == 0:
        return None
    return max(0.0, 100.0 - abs(pred - bench) / bench * 100.0)


def overall_from_kpis(
    *,
    beam_pct: Optional[float],
    bar_pct: Optional[float],
    correct_pct: Optional[float],
    weight_pct: Optional[float],
) -> Optional[float]:
    vals = [beam_pct, bar_pct, correct_pct, weight_pct]
    if any(v is None for v in vals):
        return None
    return float(sum(vals)) / 4.0


def _num(block: Dict[str, Any], key: str) -> float:
    try:
        return float(block.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def pool_kpi_blocks(blocks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [b for b in blocks if isinstance(b, dict)]
    beam_n = sum(_num(b, "beam_n") for b in rows)
    beam_d = sum(_num(b, "beam_d") for b in rows)
    bar_n = sum(_num(b, "bar_n") for b in rows)
    bar_d = sum(_num(b, "bar_d") for b in rows)
    correct_n = sum(_num(b, "correct_n") for b in rows)
    correct_d = sum(_num(b, "correct_d") for b in rows)
    dia_n = sum(_num(b, "diameter_n") for b in rows)
    dia_d = sum(_num(b, "diameter_d") for b in rows)
    model_kg = sum(_num(b, "hybrid_total_kg") for b in rows)
    bench_kg = sum(_num(b, "benchmark_total_kg") for b in rows)
    beam_pct = ratio_percent(beam_n, beam_d)
    bar_pct = ratio_percent(bar_n, bar_d)
    correct_pct = ratio_percent(correct_n, correct_d)
    dia_pct = ratio_percent(dia_n, dia_d)
    weight_pct = weight_accuracy_percent(model_kg, bench_kg)
    overall = overall_from_kpis(
        beam_pct=beam_pct, bar_pct=bar_pct, correct_pct=correct_pct, weight_pct=weight_pct
    )
    signed = model_kg - bench_kg
    return {
        "beam_n": beam_n,
        "beam_d": beam_d,
        "bar_n": bar_n,
        "bar_d": bar_d,
        "correct_n": correct_n,
        "correct_d": correct_d,
        "diameter_n": dia_n,
        "diameter_d": dia_d,
        "hybrid_total_kg": model_kg,
        "benchmark_total_kg": bench_kg,
        "signed_error_kg": signed,
        "absolute_error_kg": abs(signed),
        "beam_identification_percent": beam_pct,
        "bar_identification_percent": bar_pct,
        "correct_of_detected_percent": correct_pct,
        "diameter_identification_percent": dia_pct,
        "weight_accuracy_percent": weight_pct,
        "overall_accuracy_percent": overall,
        "pooling": "RAW_NUMERATOR_DENOMINATOR",
        "note": "Headline pooled KPIs sum raw numerators and denominators. Set percentages are not averaged.",
        "formula_weight": "max(0, 100 - abs(model_kg - benchmark_kg) / benchmark_kg * 100)",
        "formula_overall": "mean(pooled beam, pooled bar, pooled correct-of-detected, pooled weight)",
    }


def round_display(value: Optional[float], n: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), n)


def display_block(block: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(block)
    for key in (
        "beam_identification_percent",
        "bar_identification_percent",
        "correct_of_detected_percent",
        "diameter_identification_percent",
        "weight_accuracy_percent",
        "overall_accuracy_percent",
    ):
        if out.get(key) is not None:
            out[key] = round_display(out.get(key), 2)
    for key in ("hybrid_total_kg", "benchmark_total_kg", "signed_error_kg", "absolute_error_kg"):
        if out.get(key) is not None:
            out[key] = round_display(out.get(key), 3)
    return out


def merge_taxonomy(blocks: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for b in blocks:
        tax = b.get("taxonomy") if isinstance(b, dict) else None
        if not isinstance(tax, dict):
            continue
        for k, v in tax.items():
            try:
                counts[str(k)] = counts.get(str(k), 0) + int(v or 0)
            except (TypeError, ValueError):
                continue
    return counts


__all__ = [
    "display_block",
    "merge_taxonomy",
    "overall_from_kpis",
    "pool_kpi_blocks",
    "ratio_percent",
    "round_display",
    "weight_accuracy_percent",
]
