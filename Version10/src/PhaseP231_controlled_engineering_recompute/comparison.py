"""
Baseline vs controlled metric comparison.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import MODEL_VERSION, PHASE_ID


def _pp(a: Optional[float], b: Optional[float]) -> Dict[str, Any]:
    if a is None or b is None:
        return {"baseline": a, "controlled": b, "delta_pp": None}
    d = float(b) - float(a)
    return {
        "baseline": a,
        "controlled": b,
        "delta_pp": round(d, 4),
        "label": f"{a}% -> {b}% ({'+' if d >= 0 else ''}{round(d, 2)} percentage points)",
    }


def _num(a: Optional[float], b: Optional[float], unit: str = "") -> Dict[str, Any]:
    if a is None or b is None:
        return {"baseline": a, "controlled": b, "delta": None, "unit": unit}
    d = float(b) - float(a)
    return {
        "baseline": a,
        "controlled": b,
        "delta": round(d, 6),
        "unit": unit,
        "label": f"{a} -> {b} ({'+' if d >= 0 else ''}{round(d, 3)} {unit})".strip(),
    }


def _overall(summary: Dict[str, Any]) -> Optional[float]:
    if summary.get("overall_accuracy_pct") is not None:
        return float(summary["overall_accuracy_pct"])
    vals = [
        summary.get("beam_detection_pct"),
        summary.get("bar_detection_pct"),
        summary.get("bar_accuracy_pct") or summary.get("bar_matching_pct"),
        summary.get("steel_accuracy_pct"),
    ]
    nums = [float(v) for v in vals if v is not None]
    if len(nums) < 4:
        return None
    return round(sum(nums) / 4.0, 2)


def build_comparison(
    *,
    baseline_wb: Dict[str, Any],
    controlled_wb: Dict[str, Any],
    baseline_bench: Dict[str, Any],
    controlled_bench: Dict[str, Any],
    baseline_counts: Dict[str, Any],
    controlled_counts: Dict[str, Any],
    b16_trace: Dict[str, Any],
) -> Dict[str, Any]:
    bs = baseline_bench.get("drawing_summary") or {}
    cs = controlled_bench.get("drawing_summary") or {}
    bs_ov = _overall(bs)
    cs_ov = _overall(cs)

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "ownership": {
            "baseline": baseline_counts,
            "controlled": controlled_counts,
            "delta_nodes": (controlled_counts.get("accepted_node_total") or 0)
            - (baseline_counts.get("accepted_node_total") or 0),
            "delta_leaders": (controlled_counts.get("accepted_leaders") or 0)
            - (baseline_counts.get("accepted_leaders") or 0),
        },
        "workbook": {
            "baseline_sha256": baseline_wb.get("sha256"),
            "controlled_sha256": controlled_wb.get("sha256"),
            "baseline_content_fingerprint": baseline_wb.get("content_fingerprint"),
            "controlled_content_fingerprint": controlled_wb.get("content_fingerprint"),
            "identical_bytes": baseline_wb.get("sha256") == controlled_wb.get("sha256")
            and baseline_wb.get("sha256") is not None,
            "identical_engineering_content": baseline_wb.get("content_fingerprint")
            == controlled_wb.get("content_fingerprint")
            and baseline_wb.get("content_fingerprint") is not None,
            "steel_kg": _num(baseline_wb.get("steel_kg"), controlled_wb.get("steel_kg"), "kg"),
            "bar_count": _num(baseline_wb.get("bar_count"), controlled_wb.get("bar_count"), "bars"),
            "beam_count": _num(
                baseline_wb.get("beam_count"), controlled_wb.get("beam_count"), "beams"
            ),
            "b16_steel_kg": _num(
                (baseline_wb.get("b16") or {}).get("steel_kg"),
                (controlled_wb.get("b16") or {}).get("steel_kg"),
                "kg",
            ),
            "b16_bar_count": _num(
                (baseline_wb.get("b16") or {}).get("bar_count"),
                (controlled_wb.get("b16") or {}).get("bar_count"),
                "bars",
            ),
        },
        "qa30_fourth": {
            "Beam Detection": _pp(bs.get("beam_detection_pct"), cs.get("beam_detection_pct")),
            "Bar Detection": _pp(bs.get("bar_detection_pct"), cs.get("bar_detection_pct")),
            "Bar Matching": _pp(
                bs.get("bar_accuracy_pct") or bs.get("bar_matching_pct"),
                cs.get("bar_accuracy_pct") or cs.get("bar_matching_pct"),
            ),
            "Steel Accuracy": _pp(bs.get("steel_accuracy_pct"), cs.get("steel_accuracy_pct")),
            "Overall Accuracy": _pp(bs_ov, cs_ov),
            "estimator_kg": _num(bs.get("estimator_kg"), cs.get("estimator_kg"), "kg"),
            "model_kg": _num(bs.get("model_kg"), cs.get("model_kg"), "kg"),
        },
        "b16_effect_class": b16_trace.get("effect_class"),
        "architectural_note": b16_trace.get("architectural_note"),
    }
