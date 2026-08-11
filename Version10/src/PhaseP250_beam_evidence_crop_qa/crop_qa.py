"""
Crop QA gates for P2.5.0 Beam Evidence packages.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseT182_adaptive_render_extent.adaptive_bbox import contains

from .config import CLUTTER_ANN_THRESHOLD, BBox
from .evidence_window import as_bbox, object_bbox_from_node, point_in_bbox

MODEL_VERSION = "10.6.0"

PASS = "PASS"
FAIL = "FAIL"
NA = "NOT_APPLICABLE"


def _gate(ok: Optional[bool], *, applicable: bool = True) -> str:
    if not applicable:
        return NA
    if ok is None:
        return NA
    return PASS if ok else FAIL


def evaluate_crop_qa(
    *,
    evidence: Dict[str, Any],
    engineering_render: Dict[str, Any],
    overlay_render: Dict[str, Any],
    neighbour_beam_ids: Optional[List[str]] = None,
    clutter_threshold: int = CLUTTER_ANN_THRESHOLD,
) -> Dict[str, Any]:
    beam_id = evidence.get("beam_id")
    target = evidence.get("target_beam") or {}
    window = as_bbox(((evidence.get("evidence_window") or {}).get("bbox") or []))
    base = as_bbox(((evidence.get("evidence_window") or {}).get("base_bbox") or []))
    anns = evidence.get("annotations") or []
    leaders = evidence.get("leaders") or []
    bars = evidence.get("reinforcement") or []
    chains = (evidence.get("leader_chains") or {})
    complete_n = int(chains.get("complete_count") or 0)
    accepted_n = len(chains.get("accepted") or [])
    expansion = (evidence.get("evidence_window") or {}).get("expansion") or {}

    # 1 TARGET_BEAM_PRESENT
    target_present = bool(target.get("in_ownership") or target.get("in_envelope") or base)

    # 2 TARGET_BEAM_GEOMETRY_PRESENT
    geom_present = base is not None and window is not None

    # 3 RELEVANT_REINFORCEMENT_PRESENT
    reinf_present = len(bars) > 0

    # 4 RELEVANT_ANNOTATION_PRESENT
    ann_present = len(anns) > 0

    # 5 RELEVANT_LEADER_PRESENT where expected
    # Expected if accepted chains reference leaders OR annotations accepted via chain
    leader_expected = accepted_n > 0 or any(
        (a.get("ownership_reason") or "").find("leader") >= 0 for a in anns
    )
    # Also expected when annotations exist with DESCRIBES via leader in relationships
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
    # Fail if shared scope primary is different AND no ownership
    neighbour_ambiguity = False
    for sc in evidence.get("shared_scopes") or []:
        members = sc.get("member_beams") or []
        if beam_id in members and len(members) > 1:
            # Shared is OK if explicitly recorded; mark as ambiguity watch
            neighbour_ambiguity = False  # shared SFR is known, not confusion
    # If beam not in ownership but neighbours exist near window — soft flag via missing ownership
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
        )
    ]
    soft_fails = [k for k, v in gates.items() if v == FAIL and k not in hard_fails]
    overall = PASS if not hard_fails and not soft_fails else (FAIL if hard_fails else "PARTIAL")

    # Per-evidence inclusion checks inside window
    def _inside(bb) -> bool:
        if not window or not bb:
            return False
        b = as_bbox(bb) if not isinstance(bb, tuple) else bb
        if not b:
            return False
        return contains(window, b, eps=2.0)

    inclusion = {
        "annotations_in_window": sum(1 for a in anns if _inside(a.get("bbox"))),
        "leaders_in_window": sum(1 for l in leaders if _inside(l.get("bbox"))),
        "bars_in_window": sum(1 for b in bars if _inside(b.get("bbox"))),
    }

    return {
        "model_version": MODEL_VERSION,
        "beam_id": beam_id,
        "overall": overall,
        "gates": gates,
        "hard_fails": hard_fails,
        "soft_fails": soft_fails,
        "inclusion": inclusion,
        "flags": {
            "expanded": bool(expansion.get("expanded")),
            "expansions": expansion.get("expansions"),
            "evidence_clipped": evidence_clipped,
            "neighbour_ambiguity": neighbour_ambiguity,
            "leader_expected": leader_expected,
            "clutter": clutter,
        },
        "engineering_png_exists": Path(engineering_render.get("path") or "").exists()
        if engineering_render.get("path")
        else False,
        "overlay_png_exists": Path(overlay_render.get("path") or "").exists()
        if overlay_render.get("path")
        else False,
    }
