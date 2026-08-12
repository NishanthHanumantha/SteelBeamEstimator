"""Classify rejected BAR candidates and completeness state."""
from __future__ import annotations

from typing import Any, Dict, List


def classify_rejected_bar(bar_trace: Dict[str, Any], own_trace: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rejected far-elevation BAR::* vs OWN::* actual top geometry.
    """
    spatial = (bar_trace.get("17_relationship_to_target_beam") or {}).get("spatial") or {}
    y_off = spatial.get("beam_to_bar_y_offset_mm") or 0.0
    depth = spatial.get("beam_depth_mm") or 600.0
    position = spatial.get("bar_vs_envelope_position")
    own_ok = bool(own_trace.get("is_actual_top_reinforcement_geometry"))

    # Far elevation bars that are real DXF LINEs but not in beam envelope
    if (
        bar_trace.get("2_dxf_entity_type") == "LINE"
        and y_off > 10 * depth
        and position != "inside"
        and own_ok
    ):
        return {
            "classification": "FALSE_CANDIDATE",
            "confidence": "HIGH",
            "evidence": {
                "y_offset_mm": y_off,
                "depth_mm": depth,
                "y_offset_to_depth_ratio": round(y_off / depth, 2),
                "dxf_handle": bar_trace.get("1_dxf_entity_id"),
                "layer": bar_trace.get("3_layer"),
                "t18_reason": bar_trace.get("16_t18_rejection_reason"),
                "actual_top_is": own_trace.get("own_id"),
                "note": (
                    "Real -STR-REINF LINE exists at a different drawing elevation. "
                    "R.3.1 assigned beam_id by X-overlap heuristics, but geometry is "
                    "not this beam's top reinforcement. Actual top bar is OWN::* "
                    "LWPOLYLINE on -STR-BEAM inside the envelope."
                ),
            },
            "corresponds_to_4Y25": False,
        }

    if position == "inside" and bar_trace.get("14_t18_accepted") is False:
        return {
            "classification": "UNRESOLVED",
            "confidence": "MEDIUM",
            "evidence": {"note": "Inside envelope but rejected — needs review"},
            "corresponds_to_4Y25": None,
        }

    return {
        "classification": "UNRESOLVED",
        "confidence": "LOW",
        "evidence": {"spatial": spatial},
        "corresponds_to_4Y25": None,
    }


def completeness_state(
    *,
    beam_id: str,
    evidence: Dict[str, Any],
    ownership: Dict[str, Any],
    own_trace: Dict[str, Any],
    ann_id: str,
) -> Dict[str, Any]:
    anns = evidence.get("annotations") or []
    leaders = evidence.get("leaders") or []
    reinf = evidence.get("reinforcement") or []
    has_4y25 = any(
        (a.get("raw_text") or "").replace(" ", "") == "4-Y25"
        or a.get("annotation_id") == ann_id
        for a in anns
    )
    has_leader = len(leaders) > 0
    has_reinf = len(reinf) > 0
    chains = [
        c
        for c in (ownership.get("accepted_chains") or [])
        if (c.get("text") or "").replace(" ", "") == "4-Y25"
        or c.get("annotation_id") == ann_id
    ]
    condition = has_4y25 and has_leader and (not has_reinf) and bool(chains)
    return {
        "beam_id": beam_id,
        "accepted_top_bar_annotation": has_4y25,
        "accepted_leader": has_leader,
        "target_beam_ownership": bool(ownership),
        "accepted_physical_reinforcement_count": len(reinf),
        "condition_ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY": condition,
        "upstream_physical_geometry_available": bool(
            own_trace.get("is_actual_top_reinforcement_geometry")
        ),
        "upstream_geometry_id": own_trace.get("own_id"),
        "interpretation": (
            "Legitimate semantic chain to T16 OwnedEntity TOP_BAR exists, but P2.5.0 "
            "evidence_pack omits OwnedEntity from reinforcement[]. Not a T18 false reject "
            "of the actual top bar; the rejected BAR::* are different far-elevation lines."
            if condition
            else "Condition not met"
        ),
        "legitimate_or_missing_detection": (
            "UPSTREAM_GEOMETRY_EXISTS_BUT_NOT_PACKAGED"
            if condition and own_trace.get("is_actual_top_reinforcement_geometry")
            else ("MISSING_DETECTION" if condition else "N/A")
        ),
    }


def decide_next_action(
    *,
    classifications: List[Dict[str, Any]],
    completeness: List[Dict[str, Any]],
) -> Dict[str, Any]:
    all_false = all(c.get("classification") == "FALSE_CANDIDATE" for c in classifications)
    pack_gap = all(
        c.get("legitimate_or_missing_detection")
        == "UPSTREAM_GEOMETRY_EXISTS_BUT_NOT_PACKAGED"
        for c in completeness
    )
    if all_false and pack_gap:
        return {
            "decision": "FIX_EVIDENCE_LAYER",
            "rationale": (
                "Rejected BAR::* are FALSE_CANDIDATE far-elevation lines (T18 rejection "
                "correct). Actual top reinforcement is OWN::* LWPOLYLINE on -STR-BEAM, "
                "already owned by T16 and referenced by accepted 4-Y25 chains, but "
                "P2.5.0 evidence_pack does not emit OwnedEntity into reinforcement[]. "
                "Do NOT re-include rejected bars (recreates huge crops). "
                "Optionally later extend R.3.1 to -STR-BEAM, but immediate safe path is "
                "evidence-layer packaging of accepted-chain OWN:: TOP_BAR geometry."
            ),
            "do_not": [
                "Do not re-include T18-rejected BAR::* into crop expansion",
                "Do not change T18 acceptance rules for these bars",
                "Do not hardcode B97A/B98A",
            ],
            "secondary_note": (
                "R.3.1 PhysicalBarDetector only scans -STR-REINF/-rein layers, so it never "
                "emits PhysicalBar for -STR-BEAM top LWPOLYLINEs — secondary upstream gap."
            ),
        }
    return {
        "decision": "MORE_DIAGNOSTICS_REQUIRED",
        "rationale": "Classification/completeness pattern incomplete",
    }
