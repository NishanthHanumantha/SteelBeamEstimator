"""
report_compiler.py — Compile multi-drawing-set ground-truth results.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

MODEL_VERSION = "9.1.0"


def _avg(vals: List[float]) -> float:
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def compile_results(
    drawing_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total_sets = len(drawing_results)
    total_beams = detected_beams = correct_beams = 0
    total_bars = detected_bars = correct_bars = missing_bars = 0
    steel_accs: List[float] = []
    runtimes: List[float] = []
    freq: Counter = Counter()
    dashboard: List[Dict[str, Any]] = []
    ranking: List[Dict[str, Any]] = []

    for dr in drawing_results:
        m = dr.get("metrics") or {}
        m1 = m.get("metric1_beam_detection") or {}
        m2 = m.get("metric2_beam_matching") or {}
        m3 = m.get("metric3_bar_detection") or {}
        m4 = m.get("metric4_bar_accuracy") or {}
        m5 = m.get("metric5_missing_bars") or {}
        m8 = m.get("metric8_overall_steel") or {}
        pipe = dr.get("pipeline") or {}
        errs = dr.get("errors") or {}

        total_beams += int(m1.get("estimator_beams") or 0)
        detected_beams += int(m1.get("detected_beams") or 0)
        correct_beams += int(m2.get("matched_beams") or 0)
        total_bars += int(m3.get("estimator_bars") or 0)
        detected_bars += int(m3.get("detected_bars") or 0)
        correct_bars += int(m4.get("correct_bars") or 0)
        missing_bars += int(m5.get("missing_bars") or 0)
        steel_accs.append(float(m8.get("accuracy_pct") or 0))
        if pipe.get("elapsed_s") is not None:
            runtimes.append(float(pipe["elapsed_s"]))

        for et, c in (errs.get("frequency") or {}).items():
            freq[et] += int(c)

        overall_ds = round(
            (
                float(m1.get("detection_pct") or 0)
                + float(m3.get("detection_pct") or 0)
                + float(m4.get("accuracy_pct") or 0)
                + float(m8.get("accuracy_pct") or 0)
            ) / 4.0,
            2,
        )
        row = {
            "drawing_set": dr.get("drawing_set"),
            "pipeline_success": pipe.get("success"),
            "pipeline_elapsed_s": pipe.get("elapsed_s"),
            "beam_detection_pct": m1.get("detection_pct"),
            "beam_matching_pct": m2.get("matching_pct"),
            "bar_detection_pct": m3.get("detection_pct"),
            "bar_accuracy_pct": m4.get("accuracy_pct"),
            "steel_accuracy_pct": m8.get("accuracy_pct"),
            "overall_accuracy_pct": overall_ds,
            "error_count": errs.get("total_errors"),
        }
        dashboard.append(row)
        ranking.append(row)

    beam_det = round(100.0 * detected_beams / total_beams, 2) if total_beams else 0.0
    bar_det = round(100.0 * detected_bars / total_bars, 2) if total_bars else 0.0
    bar_acc = round(100.0 * correct_bars / detected_bars, 2) if detected_bars else 0.0
    steel_acc = _avg(steel_accs)
    overall = round((beam_det + bar_det + bar_acc + steel_acc) / 4.0, 2)
    ranking = sorted(ranking, key=lambda r: -(r.get("overall_accuracy_pct") or 0))

    for i, r in enumerate(ranking, 1):
        r["rank"] = i

    pipelines_ok = sum(1 for d in drawing_results if (d.get("pipeline") or {}).get("success"))
    recommendation = (
        "A — Ground-truth framework operational; prioritize top error categories for Version9 accuracy work."
        if overall >= 50 and pipelines_ok == total_sets
        else "B — Material ground-truth gaps or incomplete pipeline runs; investigate per-drawing-set errors."
    )

    benchmark = {
        "model_version": MODEL_VERSION,
        "phase": "QA.2A",
        "total_drawing_sets": total_sets,
        "production_runs_completed": pipelines_ok,
        "model_workbooks_generated": pipelines_ok,
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
        "diameter_accuracy_pct": bar_acc,
        "overall_accuracy_pct": overall,
        "average_pipeline_runtime_s": _avg(runtimes),
        "validation_status": "PASS" if pipelines_ok == total_sets and total_sets > 0 else "FAIL",
        "recommendation": recommendation,
    }

    return {
        "benchmark": benchmark,
        "statistics": {
            "drawing_sets": total_sets,
            "pipelines_ok": pipelines_ok,
            "avg_runtime_s": _avg(runtimes),
            "overall_accuracy_pct": overall,
            "total_errors": sum(freq.values()),
        },
        "errors": {
            "frequency": dict(sorted(freq.items(), key=lambda x: -x[1])),
            "total_errors": sum(freq.values()),
            "affected_drawing_sets": [
                d.get("drawing_set") for d in drawing_results
                if (d.get("errors") or {}).get("total_errors", 0) > 0
            ],
        },
        "dashboard": {"drawing_sets": dashboard},
        "ranking": ranking,
    }
