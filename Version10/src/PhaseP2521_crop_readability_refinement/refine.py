"""Deterministic crop-bound refinement iterations for P2.5.2.1."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseT182_adaptive_render_extent.adaptive_bbox import inflate_bbox, union_bbox

from .config import (
    CONTEXT_BEAM_HALF_SPAN_MM,
    CONTEXT_PAD_MM,
    CONTEXT_PAD_RELAXED_MM,
    CROP_BEAM_CONTEXT_REFINED,
    CROP_LOCAL_REFINED,
    LOCAL_BEAM_HALF_SPAN_MM,
    LOCAL_PAD_MM,
    LOCAL_PAD_RELAXED_MM,
    MAX_REFINED_HEIGHT_MM,
    MAX_REFINED_WIDTH_MM,
    MAX_REFINEMENT_ITERS,
    MIN_REFINED_HEIGHT_MM,
    MIN_REFINED_WIDTH_MM,
    READABILITY_FAIL,
    READABILITY_PARTIAL,
    READABILITY_PASS,
    READABILITY_REVIEW_REQUIRED,
    BBox,
)
from .geometry import (
    clip_bbox_to_max_span,
    collect_evidence_boxes,
    contains_bbox,
    enforce_min_size,
    local_beam_snippet,
)
from .readability import classify_readability, compute_occupancy_metrics

MODEL_VERSION = "10.6.6"

_STATUS_RANK = {
    READABILITY_PASS: 3,
    READABILITY_PARTIAL: 2,
    READABILITY_FAIL: 1,
    READABILITY_REVIEW_REQUIRED: 0,
}


def _finalize_crop(
    raw: BBox,
    *,
    cx: float,
    cy: float,
    max_w: float,
    max_h: float,
) -> BBox:
    b = enforce_min_size(raw, min_w=MIN_REFINED_WIDTH_MM, min_h=MIN_REFINED_HEIGHT_MM)
    b = clip_bbox_to_max_span(b, center_x=cx, center_y=cy, max_w=max_w, max_h=max_h)
    return b


def _candidate_iterations(
    collected: Dict[str, Any],
    *,
    crop_kind: str,
) -> List[Dict[str, Any]]:
    """
    Build ordered refinement proposals.
    Iter 0 = original P252/P250 crop (baseline).
    Later iters tighten / re-center on evidence.
    """
    beam = collected.get("beam_bbox")
    core = collected.get("evidence_core_bbox")
    original = collected.get("original_crop_bbox")
    cx = float(collected.get("center_x") or 0.0)
    cy = float(collected.get("center_y") or 0.0)
    ann = collected.get("annotation_bbox")

    iters: List[Dict[str, Any]] = []

    # Iteration 1 (index 0): baseline original crop
    if original:
        iters.append(
            {
                "iteration": 1,
                "strategy": "baseline_original_p252_crop",
                "crop_bbox": original,
                "crop_kind": crop_kind,
            }
        )

    half_x = LOCAL_BEAM_HALF_SPAN_MM if crop_kind == CROP_LOCAL_REFINED else CONTEXT_BEAM_HALF_SPAN_MM
    half_y = half_x * 0.75
    pad = LOCAL_PAD_MM if crop_kind == CROP_LOCAL_REFINED else CONTEXT_PAD_MM
    pad_relaxed = (
        LOCAL_PAD_RELAXED_MM if crop_kind == CROP_LOCAL_REFINED else CONTEXT_PAD_RELAXED_MM
    )
    max_w = MAX_REFINED_WIDTH_MM * (0.75 if crop_kind == CROP_LOCAL_REFINED else 1.0)
    max_h = MAX_REFINED_HEIGHT_MM * (0.85 if crop_kind == CROP_LOCAL_REFINED else 1.0)

    # Iteration 2: tight / medium target-centric
    if beam and core:
        snippet = local_beam_snippet(
            beam, center_x=cx, center_y=cy, half_span_x=half_x, half_span_y=half_y
        )
        uni = union_bbox([core, snippet, ann])
        if uni:
            raw = inflate_bbox(uni, pad, pad)
            crop = _finalize_crop(raw, cx=cx, cy=cy, max_w=max_w, max_h=max_h)
            iters.append(
                {
                    "iteration": 2,
                    "strategy": (
                        "tight_target_centric"
                        if crop_kind == CROP_LOCAL_REFINED
                        else "medium_beam_context"
                    ),
                    "crop_bbox": crop,
                    "crop_kind": crop_kind,
                }
            )

    # Iteration 3: evidence + annotation + immediate beam with relaxed pad
    if beam and (core or ann):
        snippet = local_beam_snippet(
            beam,
            center_x=cx,
            center_y=cy,
            half_span_x=half_x * 1.25,
            half_span_y=half_y * 1.25,
        )
        uni = union_bbox([core, snippet, ann, *(collected.get("leader_bboxes") or [])])
        if uni:
            raw = inflate_bbox(uni, pad_relaxed, pad_relaxed)
            crop = _finalize_crop(raw, cx=cx, cy=cy, max_w=max_w, max_h=max_h)
            iters.append(
                {
                    "iteration": 3,
                    "strategy": "evidence_plus_immediate_beam_relaxed",
                    "crop_bbox": crop,
                    "crop_kind": crop_kind,
                }
            )

    # Iteration 4: moderately expanded if annotation/leader context at risk
    if beam and core:
        snippet = local_beam_snippet(
            beam,
            center_x=cx,
            center_y=cy,
            half_span_x=half_x * 1.6,
            half_span_y=half_y * 1.6,
        )
        # Include more of beam for context crop
        beam_part = beam if crop_kind == CROP_BEAM_CONTEXT_REFINED else snippet
        if crop_kind == CROP_BEAM_CONTEXT_REFINED:
            beam_part = local_beam_snippet(
                beam,
                center_x=cx,
                center_y=cy,
                half_span_x=CONTEXT_BEAM_HALF_SPAN_MM * 1.5,
                half_span_y=CONTEXT_BEAM_HALF_SPAN_MM,
            )
        uni = union_bbox([core, beam_part, ann])
        if uni:
            raw = inflate_bbox(uni, pad_relaxed * 1.15, pad_relaxed * 1.15)
            crop = _finalize_crop(
                raw,
                cx=cx,
                cy=cy,
                max_w=min(max_w * 1.15, MAX_REFINED_WIDTH_MM),
                max_h=min(max_h * 1.15, MAX_REFINED_HEIGHT_MM),
            )
            iters.append(
                {
                    "iteration": 4,
                    "strategy": "moderately_expanded_context",
                    "crop_bbox": crop,
                    "crop_kind": crop_kind,
                }
            )

    # Hard-cap
    return iters[:MAX_REFINEMENT_ITERS]


def _evaluate_proposal(
    proposal: Dict[str, Any],
    collected: Dict[str, Any],
) -> Dict[str, Any]:
    crop = proposal["crop_bbox"]
    metrics = compute_occupancy_metrics(
        crop_bbox=crop,
        target_beam_bbox=collected.get("beam_bbox"),
        annotation_bbox=collected.get("annotation_bbox"),
        evidence_bbox=collected.get("evidence_core_bbox") or collected.get("annotation_bbox"),
    )
    critical_clipped = not contains_bbox(crop, collected.get("annotation_bbox"))
    # Leaders should preferably be inside; soft signal
    leaders_out = 0
    for lb in collected.get("leader_bboxes") or []:
        if not contains_bbox(crop, lb):
            leaders_out += 1
    cls = classify_readability(metrics, critical_clipped=critical_clipped)
    if leaders_out:
        cls.setdefault("flags", []).append(f"LEADERS_PARTIAL_CLIP_{leaders_out}")
        if cls["readability_status"] == READABILITY_PASS and leaders_out >= 1:
            # Downgrade PASS → PARTIAL if leader clipped
            cls["readability_status"] = READABILITY_PARTIAL
            cls["reason"] = "leader_context_partially_clipped"
    return {
        **proposal,
        "crop_bbox": list(crop),
        "metrics": metrics,
        "readability": cls,
        "leaders_clipped_count": leaders_out,
    }


def select_best_crop(
    evidence: Dict[str, Any],
    *,
    annotation_id: str,
    crop_kind: str,
) -> Dict[str, Any]:
    """
    Run refinement iterations and select the best readable crop.

    Baseline (iteration 1 / original P252 crop) is evaluated for comparison but
    is only chosen when no refined iteration is at least PARTIAL without clipping.

    Never forces extreme crops through.
    """
    collected = collect_evidence_boxes(evidence, annotation_id=annotation_id)
    proposals = _candidate_iterations(collected, crop_kind=crop_kind)
    evaluated: List[Dict[str, Any]] = []

    for prop in proposals:
        evaluated.append(_evaluate_proposal(prop, collected))

    def _score(ev: Dict[str, Any]) -> Tuple[int, float, float, int]:
        """Higher is better: status, ann_occ, evid_occ, prefer smaller area via negative."""
        status = (ev.get("readability") or {}).get("readability_status")
        metrics = ev.get("metrics") or {}
        # Penalize baseline so refined crops win when equally readable
        baseline_penalty = 1 if ev.get("iteration") == 1 else 0
        area = float(metrics.get("crop_area") or 1e30)
        return (
            _STATUS_RANK.get(status, -1),
            float(metrics.get("annotation_occupancy") or 0.0),
            float(metrics.get("evidence_occupancy") or 0.0),
            # smaller area better; invert via negative int of mm^2/1000
            -int(area / 1000.0) - baseline_penalty * 10_000_000,
        )

    refined_ok = [
        ev
        for ev in evaluated
        if int(ev.get("iteration") or 0) > 1
        and _STATUS_RANK.get((ev.get("readability") or {}).get("readability_status"), -1)
        >= _STATUS_RANK[READABILITY_PARTIAL]
        and not (ev.get("metrics") or {}).get("is_extreme")
    ]
    baseline = [ev for ev in evaluated if int(ev.get("iteration") or 0) == 1]

    if refined_ok:
        selected = max(refined_ok, key=_score)
    elif evaluated:
        # No usable refined crop — pick best non-extreme; else REVIEW
        non_extreme = [ev for ev in evaluated if not (ev.get("metrics") or {}).get("is_extreme")]
        pool = non_extreme or evaluated
        selected = max(pool, key=_score)
        if (selected.get("metrics") or {}).get("is_extreme"):
            selected = dict(selected)
            selected["readability"] = {
                **(selected.get("readability") or {}),
                "readability_status": READABILITY_REVIEW_REQUIRED,
                "reason": "extreme_crop_not_forced",
            }
    else:
        return {
            "success": False,
            "crop_kind": crop_kind,
            "selected": None,
            "iterations": evaluated,
            "collected": {
                "annotation_bbox": list(collected["annotation_bbox"])
                if collected.get("annotation_bbox")
                else None,
                "beam_bbox": list(collected["beam_bbox"]) if collected.get("beam_bbox") else None,
                "evidence_core_bbox": list(collected["evidence_core_bbox"])
                if collected.get("evidence_core_bbox")
                else None,
                "center_x": collected.get("center_x"),
                "center_y": collected.get("center_y"),
            },
            "readability_status": READABILITY_REVIEW_REQUIRED,
            "reason": "no_refinement_proposal",
        }

    status = (selected.get("readability") or {}).get("readability_status")
    if status == READABILITY_FAIL and (selected.get("metrics") or {}).get("is_extreme"):
        status = READABILITY_REVIEW_REQUIRED
        selected = dict(selected)
        selected["readability"] = {
            **(selected.get("readability") or {}),
            "readability_status": status,
            "reason": "extreme_crop_not_forced",
        }

    return {
        "success": True,
        "crop_kind": crop_kind,
        "selected": selected,
        "iterations": evaluated,
        "baseline_comparison": baseline[0] if baseline else None,
        "collected": {
            "annotation_bbox": list(collected["annotation_bbox"])
            if collected.get("annotation_bbox")
            else None,
            "beam_bbox": list(collected["beam_bbox"]) if collected.get("beam_bbox") else None,
            "evidence_core_bbox": list(collected["evidence_core_bbox"])
            if collected.get("evidence_core_bbox")
            else None,
            "leader_bboxes": [list(b) for b in (collected.get("leader_bboxes") or [])],
            "center_x": collected.get("center_x"),
            "center_y": collected.get("center_y"),
            "described_ids": collected.get("described_ids"),
        },
        "readability_status": status,
        "refinement_iteration": selected.get("iteration"),
        "strategy": selected.get("strategy"),
        "crop_bbox": selected.get("crop_bbox"),
    }


__all__ = ["select_best_crop"]
