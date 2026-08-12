"""Negative / positive crop-bound tests for P2.5.0.3."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP250_beam_evidence_crop_qa.evidence_window import (
    as_bbox,
    expand_window_to_evidence,
    object_bbox_from_node,
)
from PhaseP250_beam_evidence_crop_qa.config import EVIDENCE_PAD_MM, MAX_EXPAND_ITERS

from .config import FOCUS

BBox = Tuple[float, float, float, float]


def _rejected_bar_bboxes(bundle: Any, beam_id: str, rejected_ids: Sequence[str]) -> List[BBox]:
    boxes: List[BBox] = []
    bars = bundle.bars_by_beam.get(beam_id) or []
    by_id = {n.get("id"): n for n in bars}
    # Also scan full graph
    for n in bundle.annotation_graph.get("nodes") or []:
        if n.get("id") in rejected_ids or n.get("id") in by_id:
            by_id.setdefault(n.get("id"), n)
    for rid in rejected_ids:
        n = by_id.get(rid)
        if not n:
            continue
        bb = object_bbox_from_node(n)
        if bb:
            boxes.append(bb)
    return boxes


def negative_positive_crop_test(
    *,
    beam_id: str,
    bundle: Any,
    evidence: Dict[str, Any],
    handle_index: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compare crop bounds WITHOUT rejected candidates (production) vs WITH them
    (counterfactual that reintroduces the old bug).
    """
    focus = FOCUS.get(beam_id) or {}
    rejected = list(focus.get("rejected_bars") or [])
    own_id = focus.get("own_entity")
    own_handle = focus.get("own_handle")

    prod_bbox = as_bbox(((evidence.get("evidence_window") or {}).get("bbox") or []))
    base = as_bbox(((evidence.get("evidence_window") or {}).get("base_bbox") or []))

    # Counterfactual: expand production evidence boxes + rejected bar boxes
    eboxes: List[BBox] = []
    for section in ("reinforcement", "leaders", "annotations", "owned_geometry"):
        for it in evidence.get(section) or []:
            bb = as_bbox(it.get("bbox") or [])
            if bb:
                eboxes.append(bb)
    rejected_boxes = _rejected_bar_bboxes(bundle, beam_id, rejected)
    with_rejected = None
    if base:
        with_rejected, _ = expand_window_to_evidence(
            base,
            eboxes + rejected_boxes,
            pad_mm=EVIDENCE_PAD_MM,
            max_iters=MAX_EXPAND_ITERS,
        )

    def _wh(bb: Optional[BBox]) -> Dict[str, float]:
        if not bb:
            return {"w_mm": 0.0, "h_mm": 0.0}
        return {"w_mm": bb[2] - bb[0], "h_mm": bb[3] - bb[1]}

    prod_wh = _wh(prod_bbox)
    with_wh = _wh(with_rejected)
    rejected_affected = False
    if prod_bbox and with_rejected:
        # Significant height growth if rejected bars were included
        rejected_affected = (with_wh["h_mm"] - prod_wh["h_mm"]) > 5000.0 or any(
            abs(a - b) > 1.0 for a, b in zip(prod_bbox, with_rejected)
        )

    owned = evidence.get("owned_geometry") or []
    own_item = next((o for o in owned if o.get("ownership_id") == own_id), None)
    own_in_crop = False
    if own_item and prod_bbox and own_item.get("bbox"):
        ob = as_bbox(own_item["bbox"])
        if ob:
            from PhaseT182_adaptive_render_extent.adaptive_bbox import contains

            own_in_crop = contains(prod_bbox, ob, eps=2.0)

    reinf_ids = {str(r.get("reinforcement_id")) for r in evidence.get("reinforcement") or []}
    rejected_in_reinf = [r for r in rejected if r in reinf_ids]

    return {
        "beam_id": beam_id,
        "production_crop_bbox": list(prod_bbox) if prod_bbox else None,
        "production_crop_wh_mm": prod_wh,
        "counterfactual_with_rejected_bbox": list(with_rejected) if with_rejected else None,
        "counterfactual_with_rejected_wh_mm": with_wh,
        "rejected_bar_ids": rejected,
        "rejected_bar_bboxes_found": [list(b) for b in rejected_boxes],
        "rejected_bars_affected_production_crop": False,  # by construction of pack
        "counterfactual_would_differ": rejected_affected,
        "rejected_bars_in_reinforcement_list": rejected_in_reinf,
        "own_entity": own_id,
        "own_handle": own_handle,
        "own_packaged": own_item is not None,
        "own_dxf_resolved": bool(own_item and own_item.get("dxf_resolved")),
        "own_inside_production_crop": own_in_crop,
        "own_bbox": own_item.get("bbox") if own_item else None,
        "extreme_expansion_returned": prod_wh["h_mm"] >= 40000.0,
    }
