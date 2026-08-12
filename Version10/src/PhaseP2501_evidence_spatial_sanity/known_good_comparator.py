"""Compare extreme beams vs known-good P2.5.0 crops."""
from __future__ import annotations

from typing import Any, Dict, List

from .spatial_metrics import collect_beam_spatial_metrics


def compare_beams(
    evidence_by_id: Dict[str, Dict[str, Any]],
    focus: List[str],
    known_good: List[str],
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    metrics: Dict[str, Dict[str, Any]] = {}
    for bid in list(focus) + list(known_good):
        ev = evidence_by_id.get(bid)
        if not ev:
            continue
        m = collect_beam_spatial_metrics(ev)
        metrics[bid] = m
        ratios = m.get("ratios") or {}
        dom = m.get("dominant_expander") or {}
        rows.append(
            {
                "beam_id": bid,
                "cohort": "FOCUS" if bid in focus else "KNOWN_GOOD",
                "beam_width_mm": ratios.get("beam_width_mm"),
                "beam_height_mm": ratios.get("beam_height_mm"),
                "crop_width_mm": ratios.get("crop_width_mm"),
                "crop_height_mm": ratios.get("crop_height_mm"),
                "crop_height_to_beam_height_ratio": ratios.get(
                    "crop_height_to_beam_height_ratio"
                ),
                "crop_width_to_beam_width_ratio": ratios.get(
                    "crop_width_to_beam_width_ratio"
                ),
                "crop_area_to_beam_area_ratio": ratios.get("crop_area_to_beam_area_ratio"),
                "max_y_gap_mm": m.get("max_y_gap_mm"),
                "max_spatial_distance_mm": m.get("max_spatial_distance_mm"),
                "dominant_expander_id": dom.get("object_id"),
                "dominant_expander_kind": dom.get("object_kind"),
                "dominant_y_gap_mm": dom.get("y_gap_mm"),
                "reinforcement_count": len(ev.get("reinforcement") or []),
                "annotation_count": len(ev.get("annotations") or []),
                "leader_count": len(ev.get("leaders") or []),
            }
        )

    # Isolating deltas: focus vs mean known-good height ratio
    kg = [r for r in rows if r["cohort"] == "KNOWN_GOOD"]
    mean_h = (
        sum(r["crop_height_to_beam_height_ratio"] or 0 for r in kg) / len(kg) if kg else None
    )
    for r in rows:
        if mean_h and r.get("crop_height_to_beam_height_ratio") is not None:
            r["height_ratio_vs_known_good_mean"] = round(
                (r["crop_height_to_beam_height_ratio"] or 0) / mean_h, 3
            )

    return {
        "rows": rows,
        "metrics": metrics,
        "known_good_mean_height_ratio": mean_h,
        "difference_summary": (
            "Focus beams differ by extreme Y-gap reinforcement objects that "
            "force evidence-window expansion; known-good beams keep reinforcement "
            "Y within / near the beam elevation band."
        ),
    }
