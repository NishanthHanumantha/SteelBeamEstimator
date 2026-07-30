"""
compiled_report.py — Aggregate per-drawing-set results into compiled benchmark.
MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

MODEL_VERSION = "8.9.0"


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def compile_results(comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_sets = len(comparisons)
    total_beams = detected_beams = correct_beams = 0
    total_bars = detected_bars = correct_bars = missing_bars = 0
    steel_accs: List[float] = []
    beam_det_pcts: List[float] = []
    bar_det_pcts: List[float] = []
    bar_acc_pcts: List[float] = []
    freq: Counter = Counter()
    dashboard_rows: List[Dict[str, Any]] = []

    for c in comparisons:
        s = c.get("summary") or {}
        bd = c.get("beam_detection") or {}
        ba = c.get("bar_detection") or {}
        bac = c.get("bar_accuracy") or {}
        st = c.get("steel_quantity") or {}

        total_beams += int(bd.get("total_estimator_beams") or 0)
        detected_beams += int(bd.get("detected_beams") or 0)
        correct_beams += int((c.get("beam_identification") or {}).get("correctly_matched") or 0)
        total_bars += int(ba.get("estimator_bars") or 0)
        detected_bars += int(ba.get("detected_bars") or 0)
        correct_bars += int(bac.get("correct_bars") or 0)
        missing_bars += int(bac.get("undetected_bars") or 0)

        beam_det_pcts.append(float(s.get("beam_detection_pct") or 0))
        bar_det_pcts.append(float(s.get("bar_detection_pct") or 0))
        bar_acc_pcts.append(float(s.get("bar_accuracy_pct") or 0))
        steel_accs.append(float(s.get("steel_accuracy_pct") or 0))

        for etype, count in ((c.get("errors") or {}).get("frequency") or {}).items():
            freq[etype] += int(count)

        dashboard_rows.append({
            "drawing_set": s.get("drawing_set"),
            "beam_detection_pct": s.get("beam_detection_pct"),
            "beam_accuracy_pct": s.get("beam_accuracy_pct"),
            "bar_detection_pct": s.get("bar_detection_pct"),
            "bar_accuracy_pct": s.get("bar_accuracy_pct"),
            "steel_accuracy_pct": s.get("steel_accuracy_pct"),
            "error_count": s.get("error_count"),
        })

    beam_det = round(100.0 * detected_beams / total_beams, 2) if total_beams else 0.0
    bar_det = round(100.0 * detected_bars / total_bars, 2) if total_bars else 0.0
    bar_acc = round(100.0 * correct_bars / detected_bars, 2) if detected_bars else 0.0
    steel_acc = _avg(steel_accs)
    overall = round((beam_det + bar_det + bar_acc + steel_acc) / 4.0, 2)

    validation_ok = total_sets > 0 and all(
        (c.get("summary") or {}).get("drawing_set") for c in comparisons
    )
    recommendation = (
        "A — Framework validated; review low-accuracy drawing sets before promotion."
        if overall >= 70
        else "B — Material accuracy gaps; prioritize top error categories before production changes."
    )

    benchmark = {
        "model_version": MODEL_VERSION,
        "phase": "QA.2",
        "total_drawing_sets": total_sets,
        "total_beams": total_beams,
        "detected_beams": detected_beams,
        "correct_beams": correct_beams,
        "total_bars": total_bars,
        "detected_bars": detected_bars,
        "correct_bars": correct_bars,
        "missing_bars": missing_bars,
        "beam_detection_pct": beam_det,
        "bar_detection_pct": bar_det,
        "bar_accuracy_pct": bar_acc,
        "steel_accuracy_pct": steel_acc,
        "diameter_accuracy_pct": _avg(bar_acc_pcts),  # proxy until diameter-specific KPI
        "overall_accuracy_pct": overall,
        "validation_status": "PASS" if validation_ok else "FAIL",
        "recommendation": recommendation,
    }

    statistics = {
        "drawing_sets_processed": total_sets,
        "avg_beam_detection_pct": _avg(beam_det_pcts),
        "avg_bar_detection_pct": _avg(bar_det_pcts),
        "avg_bar_accuracy_pct": _avg(bar_acc_pcts),
        "avg_steel_accuracy_pct": steel_acc,
        "overall_accuracy_pct": overall,
        "total_errors": sum(freq.values()),
    }

    return {
        "benchmark": benchmark,
        "statistics": statistics,
        "errors": {
            "frequency": dict(sorted(freq.items(), key=lambda x: -x[1])),
            "total_errors": sum(freq.values()),
        },
        "dashboard": {
            "drawing_sets": dashboard_rows,
            "columns": [
                "Drawing Set", "Beam Detection %", "Beam Accuracy %",
                "Bar Detection %", "Bar Accuracy %", "Steel Accuracy %",
            ],
        },
    }
