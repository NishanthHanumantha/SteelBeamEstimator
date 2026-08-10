"""
Baseline vs controlled accuracy comparison.
MODEL_VERSION: 10.5.5

Steel/bar accuracy formulas are not changed. When Estimation_Output.xlsx is not
regenerated, controlled steel metrics equal baseline and the bottleneck is documented.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import MODEL_VERSION, PHASE_ID
from .overlay import ownership_counts


def _delta(a: Optional[float], b: Optional[float]) -> Dict[str, Any]:
    if a is None or b is None:
        return {"baseline": a, "controlled": b, "absolute_pp": None, "pct_point_change": None}
    d = float(b) - float(a)
    return {
        "baseline": a,
        "controlled": b,
        "absolute_pp": round(d, 4),
        "pct_point_change": round(d, 4),
        "label": f"{a}% -> {b}% ({'+' if d >= 0 else ''}{round(d, 2)} percentage points)",
    }


def build_benchmark_comparison(
    *,
    qa30_report: Optional[Dict[str, Any]],
    baseline_ownership: Dict[str, Any],
    controlled_ownership: Dict[str, Any],
    beam_ids: list,
    migration_count: int,
    render_result: Dict[str, Any],
    steel_regenerated: bool = False,
    controlled_qa30: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    overall = (qa30_report or {}).get("overall_metrics") or {}
    fourth = next(
        (
            r
            for r in (qa30_report or {}).get("drawing_set_results") or []
            if "Fourth" in str(r.get("drawing_set") or "")
        ),
        {},
    )
    # If controlled QA30 not regenerated, steel metrics unchanged
    ctrl_overall = (
        (controlled_qa30 or {}).get("overall_metrics") if controlled_qa30 else overall
    ) or overall
    ctrl_fourth = (
        next(
            (
                r
                for r in (controlled_qa30 or {}).get("drawing_set_results") or []
                if "Fourth" in str(r.get("drawing_set") or "")
            ),
            fourth,
        )
        if controlled_qa30
        else fourth
    )

    base_counts = ownership_counts(baseline_ownership, beam_ids)
    ctrl_counts = ownership_counts(controlled_ownership, beam_ids)

    accuracy = {
        "Beam Detection": _delta(
            overall.get("beam_detection_pct"), ctrl_overall.get("beam_detection_pct")
        ),
        "Bar Detection": _delta(
            overall.get("bar_detection_pct"), ctrl_overall.get("bar_detection_pct")
        ),
        "Bar Matching": _delta(
            overall.get("bar_matching_pct"), ctrl_overall.get("bar_matching_pct")
        ),
        "Steel Accuracy": _delta(
            overall.get("steel_accuracy_pct"), ctrl_overall.get("steel_accuracy_pct")
        ),
        "Overall Accuracy": _delta(
            overall.get("overall_accuracy_pct"), ctrl_overall.get("overall_accuracy_pct")
        ),
    }
    fourth_acc = {
        "Beam Detection": _delta(
            fourth.get("beam_detection_pct"), ctrl_fourth.get("beam_detection_pct")
        ),
        "Bar Detection": _delta(
            fourth.get("bar_detection_pct"), ctrl_fourth.get("bar_detection_pct")
        ),
        "Bar Matching": _delta(
            fourth.get("bar_accuracy_pct") or fourth.get("bar_matching_pct"),
            ctrl_fourth.get("bar_accuracy_pct") or ctrl_fourth.get("bar_matching_pct"),
        ),
        "Steel Accuracy": _delta(
            fourth.get("steel_accuracy_pct"), ctrl_fourth.get("steel_accuracy_pct")
        ),
        "Overall Accuracy": _delta(
            fourth.get("overall_accuracy_pct"), ctrl_fourth.get("overall_accuracy_pct")
        ),
    }

    steel_delta = (accuracy["Steel Accuracy"].get("absolute_pp") or 0.0)
    render_improved = bool(render_result.get("any_crop_improved"))
    ownership_improved = migration_count > 0

    bottleneck = None
    if ownership_improved and not steel_regenerated:
        bottleneck = (
            "Recovered leader/annotation chain already partially owned; "
            "Estimation_Output.xlsx not regenerated in P2.3 controlled experiment, "
            "so steel accuracy formulas cannot reflect visual ownership recovery yet."
        )
    elif ownership_improved and steel_delta == 0 and steel_regenerated:
        bottleneck = (
            "Ownership recovered but steel accuracy unchanged — recovered "
            "engineering information did not change estimation quantities."
        )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "steel_regenerated": steel_regenerated,
        "bottleneck": bottleneck,
        "ownership": {
            "baseline": base_counts,
            "controlled": ctrl_counts,
            "delta_accepted_nodes": ctrl_counts["accepted_node_total"]
            - base_counts["accepted_node_total"],
            "delta_leaders": ctrl_counts["accepted_leaders"]
            - base_counts["accepted_leaders"],
            "migration_count": migration_count,
        },
        "render": {
            "affected_beam_count": render_result.get("affected_beam_count"),
            "any_crop_improved": render_improved,
            "any_neighbour_contamination": render_result.get(
                "any_neighbour_contamination"
            ),
        },
        "BenchmarkBaseline": {
            "overall": overall,
            "fourth_set": fourth,
        },
        "BenchmarkControlled": {
            "overall": ctrl_overall,
            "fourth_set": ctrl_fourth,
            "note": (
                None
                if steel_regenerated
                else "Controlled steel metrics equal baseline (Excel not regenerated)"
            ),
        },
        "AccuracyComparison": {
            "overall_three_sets": accuracy,
            "fourth_set_priority_population": fourth_acc,
        },
        "material_improvement": bool(
            steel_delta > 0.05 or (render_improved and ownership_improved and steel_delta > 0)
        ),
        "ownership_or_render_improvement": ownership_improved or render_improved,
    }
