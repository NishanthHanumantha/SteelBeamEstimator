"""Trace which evidence objects force evidence-window expansion."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP250_beam_evidence_crop_qa.evidence_window import (
    as_bbox,
    contains,
    expand_window_to_evidence,
)
from PhaseT182_adaptive_render_extent.adaptive_bbox import union_bbox

BBox = Tuple[float, float, float, float]


def _obj_bbox(kind: str, obj: Dict[str, Any]) -> Optional[BBox]:
    return as_bbox(obj.get("bbox"))


def trace_expansion(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replay expansion from evidence package contents.
    Identifies objects outside the base window and the dominant vertical expander.
    """
    win = evidence.get("evidence_window") or {}
    base = as_bbox(win.get("base_bbox"))
    final = as_bbox(win.get("bbox"))
    if not base:
        return {"beam_id": evidence.get("beam_id"), "error": "missing_base_bbox"}

    items: List[Dict[str, Any]] = []
    for a in evidence.get("annotations") or []:
        items.append(
            {
                "id": a.get("annotation_id"),
                "kind": "annotation",
                "bbox": _obj_bbox("annotation", a),
                "text": a.get("raw_text"),
            }
        )
    for l in evidence.get("leaders") or []:
        items.append(
            {
                "id": l.get("leader_id"),
                "kind": "leader",
                "bbox": _obj_bbox("leader", l),
                "geometry": l.get("geometry"),
            }
        )
    for r in evidence.get("reinforcement") or []:
        items.append(
            {
                "id": r.get("reinforcement_id"),
                "kind": "reinforcement",
                "bbox": _obj_bbox("reinforcement", r),
                "geometry": r.get("geometry"),
            }
        )

    clipped = []
    for it in items:
        bb = it["bbox"]
        if bb and not contains(base, bb, eps=1.0):
            y_gap = 0.0
            if bb[3] < base[1]:
                y_gap = base[1] - bb[3]
            elif bb[1] > base[3]:
                y_gap = bb[1] - base[3]
            x_gap = 0.0
            if bb[2] < base[0]:
                x_gap = base[0] - bb[2]
            elif bb[0] > base[2]:
                x_gap = bb[0] - base[2]
            clipped.append({**it, "y_gap_mm": y_gap, "x_gap_mm": x_gap})

    dominant = None
    if clipped:
        dominant = max(clipped, key=lambda c: (c.get("y_gap_mm") or 0.0, c.get("x_gap_mm") or 0.0))

    # Step-by-step union narrative
    steps: List[Dict[str, Any]] = [
        {
            "step": 0,
            "label": "initial_base_bbox",
            "bbox": list(base),
            "height_mm": base[3] - base[1],
            "width_mm": base[2] - base[0],
        }
    ]
    window = base
    for i, c in enumerate(sorted(clipped, key=lambda x: -(x.get("y_gap_mm") or 0.0)), 1):
        bb = c["bbox"]
        uni = union_bbox([window, bb])
        if uni:
            window = uni
        steps.append(
            {
                "step": i,
                "label": f"include_{c['kind']}",
                "object_id": c["id"],
                "object_bbox": list(bb) if bb else None,
                "y_gap_mm": c.get("y_gap_mm"),
                "bbox_after": list(window) if window else None,
                "height_mm": (window[3] - window[1]) if window else None,
            }
        )

    eboxes = [it["bbox"] for it in items if it["bbox"]]
    replayed, diag = expand_window_to_evidence(base, eboxes)
    return {
        "beam_id": evidence.get("beam_id"),
        "initial_bbox": list(base),
        "package_final_bbox": list(final) if final else None,
        "package_expansion_meta": win.get("expansion"),
        "clipped_before_objects": clipped,
        "clipped_before_count": len(clipped),
        "dominant_vertical_expander": dominant,
        "expansion_steps": steps,
        "replayed_final_bbox": list(replayed) if replayed else None,
        "replay_diag": diag,
        "final_height_mm": (final[3] - final[1]) if final else None,
        "final_width_mm": (final[2] - final[0]) if final else None,
    }
