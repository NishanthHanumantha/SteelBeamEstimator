"""Root-cause classification for extreme spatial crops."""
from __future__ import annotations

from typing import Any, Dict


def classify_root_cause(
    *,
    trace: Dict[str, Any],
    expansion: Dict[str, Any],
    ownership: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assign exactly one root-cause label when supported by evidence.
    Prefer concrete inclusion/expansion bugs over generic space checks.
    """
    rejected_included = []
    br = ownership.get("bar_results") or {}
    for bt in trace.get("bar_traces") or []:
        bid = bt.get("object_id")
        res = br.get(bid) or {}
        included = False
        for step in bt.get("steps") or []:
            if step.get("step") == "P2.5.0.evidence_package.reinforcement":
                included = bool(step.get("included_in_package"))
        if included and res.get("accepted") is False:
            rejected_included.append(
                {
                    "bar_id": bid,
                    "ownership_reason": res.get("ownership_reason"),
                    "rejected_rule": res.get("rejected_rule"),
                    "y_gap": next(
                        (
                            s.get("y_gap_to_beam_mm")
                            for s in bt.get("steps") or []
                            if s.get("step") == "P2.5.0.evidence_package.reinforcement"
                        ),
                        None,
                    ),
                }
            )

    rejected_leaders_included = []
    lr = ownership.get("leader_results") or {}
    if isinstance(lr, dict):
        for lt in trace.get("leader_traces") or []:
            lid = lt.get("object_id")
            res = lr.get(lid) or {}
            if lt.get("included_in_package") and res.get("accepted") is False:
                rejected_leaders_included.append(
                    {
                        "leader_id": lid,
                        "ownership_reason": res.get("ownership_reason"),
                        "rejected_rule": res.get("rejected_rule"),
                    }
                )

    dom = expansion.get("dominant_vertical_expander") or {}
    final_h = expansion.get("final_height_mm") or 0.0

    if rejected_included:
        return {
            "label": "EVIDENCE_EXPANSION_ERROR",
            "confidence": "HIGH",
            "basis": {
                "summary": (
                    "T18 already rejected far-elevation bars "
                    "(bar_y_outside_reinforcement_elevation / R5_NEIGHBOUR_REJECT). "
                    "P2.5.0 included those rejected bar_results keys in the evidence "
                    "package and expanded the crop to contain them."
                ),
                "rejected_bars_included": rejected_included,
                "dominant_expander": dom,
                "final_height_mm": final_h,
                "ownership_engine_verdict": "REJECTED (correct)",
                "p250_behavior": "INCLUDED_REJECTED (bug)",
                "upstream_of_p250": False,
                "inside_p250": True,
            },
        }

    if rejected_leaders_included:
        return {
            "label": "LEADER_EXPANSION_ERROR",
            "confidence": "HIGH",
            "basis": {
                "rejected_leaders_included": rejected_leaders_included,
                "dominant_expander": dom,
            },
        }

    space = trace.get("coordinate_space_consistency") or {}
    if space.get("unit_mismatch_detected"):
        return {"label": "UNIT_MISMATCH", "confidence": "HIGH", "basis": "unit flags"}
    if space.get("transform_error_detected"):
        return {"label": "TRANSFORM_ERROR", "confidence": "HIGH", "basis": "transform flags"}
    if not space.get("all_same_space", True):
        return {
            "label": "COORDINATE_SPACE_MISMATCH",
            "confidence": "HIGH",
            "basis": space.get("spaces"),
        }

    far_accepted = [
        bt
        for bt in trace.get("bar_traces") or []
        if bt.get("t18_accepted") and bt.get("spatially_inside_beam_y_band") is False
    ]
    if far_accepted:
        return {
            "label": "OWNERSHIP_ERROR",
            "confidence": "MEDIUM",
            "basis": {"far_accepted_bars": [b.get("object_id") for b in far_accepted]},
        }

    if final_h > 20000 and dom:
        return {
            "label": "UNKNOWN_REQUIRES_REVIEW",
            "confidence": "LOW",
            "basis": {"dominant_expander": dom, "final_height_mm": final_h},
        }

    return {
        "label": "LEGITIMATE_LARGE_CONTEXT",
        "confidence": "LOW",
        "basis": {"note": "No rejected-inclusion pattern; large context may be legitimate."},
    }
