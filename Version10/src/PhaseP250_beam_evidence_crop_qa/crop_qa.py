"""
Crop QA gates for P2.5.0 Beam Evidence packages.
MODEL_VERSION: 10.6.2
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseT182_adaptive_render_extent.adaptive_bbox import contains

from .config import CLUTTER_ANN_THRESHOLD, BBox
from .evidence_window import as_bbox, object_bbox_from_node, point_in_bbox

MODEL_VERSION = "10.6.3"

PASS = "PASS"
FAIL = "FAIL"
NA = "NOT_APPLICABLE"

# Align with P2.5.0.1 extreme crop diagnostic thresholds
EXTREME_CROP_HEIGHT_RATIO = 8.0
EXTREME_CROP_AREA_RATIO = 40.0
EXTREME_Y_GAP_MM = 5000.0


def _gate(ok: Optional[bool], *, applicable: bool = True) -> str:
    if not applicable:
        return NA
    if ok is None:
        return NA
    return PASS if ok else FAIL


def _bbox_wh(bb: BBox) -> tuple:
    return max(bb[2] - bb[0], 0.0), max(bb[3] - bb[1], 0.0)


def evaluate_crop_qa(
    *,
    evidence: Dict[str, Any],
    engineering_render: Dict[str, Any],
    overlay_render: Dict[str, Any],
    neighbour_beam_ids: Optional[List[str]] = None,
    clutter_threshold: int = CLUTTER_ANN_THRESHOLD,
    render_validation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    beam_id = evidence.get("beam_id")
    target = evidence.get("target_beam") or {}
    window = as_bbox(((evidence.get("evidence_window") or {}).get("bbox") or []))
    base = as_bbox(((evidence.get("evidence_window") or {}).get("base_bbox") or []))
    anns = evidence.get("annotations") or []
    leaders = evidence.get("leaders") or []
    bars = evidence.get("reinforcement") or []
    owned = evidence.get("owned_geometry") or []
    owned_top = [o for o in owned if o.get("evidence_type") == "OWN_TOP_BAR"]
    chains = evidence.get("leader_chains") or {}
    complete_n = int(chains.get("complete_count") or 0)
    accepted_n = len(chains.get("accepted") or [])
    expansion = (evidence.get("evidence_window") or {}).get("expansion") or {}
    excluded = evidence.get("excluded_rejected_evidence") or {}
    rejected_bars = list(excluded.get("bars") or [])

    # 1 TARGET_BEAM_PRESENT
    target_present = bool(target.get("in_ownership") or target.get("in_envelope") or base)

    # 2 TARGET_BEAM_GEOMETRY_PRESENT
    geom_present = base is not None and window is not None

    # 3 RELEVANT_REINFORCEMENT_PRESENT — PhysicalBar OR accepted OWN TOP_BAR visual
    reinf_present = len(bars) > 0 or len(owned_top) > 0

    # 4 RELEVANT_ANNOTATION_PRESENT
    ann_present = len(anns) > 0

    # 5 RELEVANT_LEADER_PRESENT where expected
    leader_expected = accepted_n > 0 or any(
        (a.get("ownership_reason") or "").find("leader") >= 0 for a in anns
    )
    if any(r.get("type") == "leader_to_annotation" for r in evidence.get("relationships") or []):
        leader_expected = True
    leader_present = len(leaders) > 0

    # 6 COMPLETE_LEADER_CHAIN
    chain_applicable = accepted_n > 0 or leader_expected
    chain_complete = complete_n > 0

    # 7 RELEVANT_EVIDENCE_NOT_CLIPPED
    still_clipped = int(expansion.get("still_clipped_count") or 0)
    evidence_clipped = still_clipped > 0

    # 8 CROP_NOT_EMPTY
    crop_not_empty = bool(engineering_render.get("success")) and window is not None

    # 9 CROP_NOT_EXCESSIVELY_CLUTTERED
    clutter = len(anns) > clutter_threshold

    # 10 TARGET_BEAM_NOT_CONFUSED_WITH_NEIGHBOR
    neighbour_ambiguity = False
    for sc in evidence.get("shared_scopes") or []:
        members = sc.get("member_beams") or []
        if beam_id in members and len(members) > 1:
            neighbour_ambiguity = False
    if not target.get("in_ownership") and (neighbour_beam_ids or []):
        neighbour_ambiguity = True

    # 11 COORDINATE_TRANSFORM_VALID
    xf_ok = bool(
        engineering_render.get("success")
        and engineering_render.get("img_w")
        and engineering_render.get("img_h")
        and window
    )

    # 12 RENDER_SUCCESS
    render_ok = bool(engineering_render.get("success")) and bool(overlay_render.get("success"))

    # --- P2.5.0.3 OWN TOP_BAR gates ---
    own_expected = any(
        any(str(d).startswith("OWN::") for d in (ch.get("describes") or []))
        for ch in (chains.get("accepted") or [])
    )
    own_present = len(owned_top) > 0

    def _inside(bb) -> bool:
        if not window or not bb:
            return False
        b = as_bbox(bb) if not isinstance(bb, tuple) else bb
        if not b:
            return False
        return contains(window, b, eps=2.0)

    own_inside = bool(owned_top) and all(_inside(o.get("bbox")) for o in owned_top if o.get("bbox"))
    if owned_top and not any(o.get("bbox") for o in owned_top):
        own_inside = False

    own_source_valid = bool(owned_top) and all(
        o.get("dxf_resolved")
        and o.get("entity_type") in ("LWPOLYLINE", "LINE")
        and o.get("source_handle")
        for o in owned_top
    )

    own_linked = bool(owned_top) and all(
        o.get("annotation_id") and o.get("leader_id") and o.get("ownership_id")
        for o in owned_top
    )

    # P2.5.0.4 — visual render gates (package inclusion alone is insufficient)
    rv = render_validation or {}
    paint_n = int(engineering_render.get("owned_geometry_paint_count") or 0)
    own_rendered = bool(rv.get("rendered")) if rv else (paint_n > 0 and bool(owned_top))
    own_distinguishable = bool(rv.get("distinguishable")) if rv else own_rendered

    # Rejected PhysicalBars must not appear in reinforcement list
    reinf_ids = {str(b.get("reinforcement_id")) for b in bars}
    rejected_excluded = not any(r in reinf_ids for r in rejected_bars)

    # CROP_NOT_EXTREME — avoid return of 47–76 m crops
    crop_not_extreme = True
    if window and base:
        bw, bh = _bbox_wh(base)
        cw, ch = _bbox_wh(window)
        h_ratio = ch / max(bh, 1.0)
        a_ratio = (cw * ch) / max(bw * bh, 1.0)
        # max |y| gap between base center and window edges
        by_c = (base[1] + base[3]) / 2.0
        max_y_gap = max(abs(window[1] - by_c), abs(window[3] - by_c))
        crop_not_extreme = not (
            h_ratio >= EXTREME_CROP_HEIGHT_RATIO
            or a_ratio >= EXTREME_CROP_AREA_RATIO
            or max_y_gap >= EXTREME_Y_GAP_MM
        )
    elif window:
        _, ch = _bbox_wh(window)
        crop_not_extreme = ch < EXTREME_Y_GAP_MM

    gates = {
        "TARGET_BEAM_PRESENT": _gate(target_present),
        "TARGET_BEAM_GEOMETRY_PRESENT": _gate(geom_present),
        "RELEVANT_REINFORCEMENT_PRESENT": _gate(reinf_present),
        "RELEVANT_ANNOTATION_PRESENT": _gate(ann_present),
        "RELEVANT_LEADER_PRESENT": _gate(
            leader_present if leader_expected else None,
            applicable=leader_expected,
        ),
        "COMPLETE_LEADER_CHAIN": _gate(
            chain_complete if chain_applicable else None,
            applicable=chain_applicable,
        ),
        "RELEVANT_EVIDENCE_NOT_CLIPPED": _gate(not evidence_clipped if window else None),
        "CROP_NOT_EMPTY": _gate(crop_not_empty),
        "CROP_NOT_EXCESSIVELY_CLUTTERED": _gate(not clutter if anns else True),
        "TARGET_BEAM_NOT_CONFUSED_WITH_NEIGHBOR": _gate(not neighbour_ambiguity),
        "COORDINATE_TRANSFORM_VALID": _gate(xf_ok),
        "RENDER_SUCCESS": _gate(render_ok),
        "OWN_TOP_BAR_PRESENT": _gate(
            own_present if own_expected else None,
            applicable=own_expected,
        ),
        "OWN_TOP_BAR_INSIDE_CROP": _gate(
            own_inside if own_expected else None,
            applicable=own_expected,
        ),
        "OWN_TOP_BAR_SOURCE_VALID": _gate(
            own_source_valid if own_expected else None,
            applicable=own_expected,
        ),
        "OWN_TOP_BAR_LINKED_TO_ACCEPTED_CHAIN": _gate(
            own_linked if own_expected else None,
            applicable=own_expected,
        ),
        "OWN_TOP_BAR_RENDERED": _gate(
            own_rendered if own_expected else None,
            applicable=own_expected,
        ),
        "OWN_TOP_BAR_VISUALLY_DISTINGUISHABLE": _gate(
            own_distinguishable if own_expected else None,
            applicable=own_expected,
        ),
        "REJECTED_PHYSICAL_BAR_EXCLUDED": _gate(rejected_excluded),
        "CROP_NOT_EXTREME": _gate(crop_not_extreme if window else None),
    }

    hard_fails = [
        k
        for k, v in gates.items()
        if v == FAIL
        and k
        in (
            "TARGET_BEAM_PRESENT",
            "TARGET_BEAM_GEOMETRY_PRESENT",
            "CROP_NOT_EMPTY",
            "COORDINATE_TRANSFORM_VALID",
            "RENDER_SUCCESS",
            "RELEVANT_EVIDENCE_NOT_CLIPPED",
            "CROP_NOT_EXTREME",
            "REJECTED_PHYSICAL_BAR_EXCLUDED",
            "OWN_TOP_BAR_RENDERED",
        )
    ]
    soft_fails = [k for k, v in gates.items() if v == FAIL and k not in hard_fails]
    overall = PASS if not hard_fails and not soft_fails else (FAIL if hard_fails else "PARTIAL")

    inclusion = {
        "annotations_in_window": sum(1 for a in anns if _inside(a.get("bbox"))),
        "leaders_in_window": sum(1 for l in leaders if _inside(l.get("bbox"))),
        "bars_in_window": sum(1 for b in bars if _inside(b.get("bbox"))),
        "owned_geometry_in_window": sum(1 for o in owned if _inside(o.get("bbox"))),
    }

    return {
        "model_version": MODEL_VERSION,
        "beam_id": beam_id,
        "overall": overall,
        "gates": gates,
        "hard_fails": hard_fails,
        "soft_fails": soft_fails,
        "inclusion": inclusion,
        "render_validation": rv or None,
        "flags": {
            "expanded": bool(expansion.get("expanded")),
            "expansions": expansion.get("expansions"),
            "evidence_clipped": evidence_clipped,
            "neighbour_ambiguity": neighbour_ambiguity,
            "leader_expected": leader_expected,
            "clutter": clutter,
            "own_expected": own_expected,
            "owned_top_bar_count": len(owned_top),
            "owned_geometry_paint_count": paint_n,
        },
        "engineering_png_exists": Path(engineering_render.get("path") or "").exists()
        if engineering_render.get("path")
        else False,
        "overlay_png_exists": Path(overlay_render.get("path") or "").exists()
        if overlay_render.get("path")
        else False,
    }
