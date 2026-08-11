"""
Evidence-window geometry helpers (model coordinates).
Reuses T1.8.2 bbox primitives — does not modify T182.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from PhaseT182_adaptive_render_extent.adaptive_bbox import (
    contains,
    estimate_text_bbox,
    inflate_bbox,
    point_bbox,
    segment_bbox,
    touches_border,
    union_bbox,
)

from .config import BBox, EVIDENCE_PAD_MM

MODEL_VERSION = "10.6.0"


def as_bbox(seq: Sequence[float]) -> Optional[BBox]:
    if not seq or len(seq) < 4:
        return None
    return (float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))


def beam_base_bbox(
    *,
    envelope_extent: Optional[Sequence[float]],
    ownership_crop: Optional[Sequence[float]],
    registry_bbox: Optional[Dict[str, Any]],
    base_margin_mm: float,
) -> Optional[BBox]:
    """Deterministic base window from known beam geometry + controlled margin."""
    candidates: List[BBox] = []
    for src in (ownership_crop, envelope_extent):
        b = as_bbox(src) if src else None
        if b:
            candidates.append(b)
    if registry_bbox:
        try:
            candidates.append(
                (
                    float(registry_bbox["x_min"]),
                    float(registry_bbox["y_min"]),
                    float(registry_bbox["x_max"]),
                    float(registry_bbox["y_max"]),
                )
            )
        except Exception:
            pass
    base = union_bbox(candidates)
    if not base:
        return None
    # Degenerate mark-only bbox: inflate more so render is not a point
    w = max(base[2] - base[0], 1.0)
    h = max(base[3] - base[1], 1.0)
    mx = max(base_margin_mm, 50.0)
    my = max(base_margin_mm, 50.0)
    if w < 200:
        mx = max(mx, 1500.0)
    if h < 200:
        my = max(my, 800.0)
    return inflate_bbox(base, mx, my)


def object_bbox_from_node(node: Dict[str, Any]) -> Optional[BBox]:
    t = node.get("type")
    a = node.get("attributes") or {}
    if t == "PhysicalBar":
        try:
            return segment_bbox(
                float(a["start_x"]),
                float(a["y_position"]),
                float(a["end_x"]),
                float(a["y_position"]),
                pad=20.0,
            )
        except Exception:
            return None
    if t == "Leader":
        try:
            return segment_bbox(
                float(a["tip_x"]),
                float(a["tip_y"]),
                float(a["tail_x"]),
                float(a["tail_y"]),
                pad=30.0,
            )
        except Exception:
            return None
    if t == "LeaderArrow":
        try:
            return point_bbox(float(a.get("tip_x") or a["x"]), float(a.get("tip_y") or a["y"]), pad=55.0)
        except Exception:
            return None
    if t in ("Annotation", "SemanticFact", "StirrupNote"):
        try:
            x = float(a.get("x") if a.get("x") is not None else node.get("x"))
            y = float(a.get("y") if a.get("y") is not None else node.get("y"))
        except Exception:
            return None
        text = str(a.get("clean_text") or a.get("text") or node.get("text") or "")
        return estimate_text_bbox(x, y, text)
    if t == "Beam":
        return as_bbox((a.get("extent") or []))
    return None


def evidence_bboxes(
    *,
    bars: Sequence[Dict[str, Any]],
    leaders: Sequence[Dict[str, Any]],
    annotations: Sequence[Dict[str, Any]],
    extras: Optional[Iterable[Optional[BBox]]] = None,
) -> List[BBox]:
    boxes: List[BBox] = []
    for n in list(bars) + list(leaders) + list(annotations):
        bb = object_bbox_from_node(n) if "type" in n else None
        if bb is None and isinstance(n, dict):
            # ownership annotation records (not graph nodes)
            try:
                if "text" in n and ("x" in n or "position" in n):
                    pass
            except Exception:
                pass
        if bb:
            boxes.append(bb)
        # Ownership annotation dicts
        if n.get("type") is None and n.get("id") and (n.get("text") is not None):
            # may lack coordinates — skip bbox
            continue
    if extras:
        for b in extras:
            if b:
                boxes.append(b)
    return boxes


def expand_window_to_evidence(
    base: BBox,
    evidence: Sequence[BBox],
    *,
    pad_mm: float = EVIDENCE_PAD_MM,
    max_iters: int = 4,
) -> Tuple[BBox, Dict[str, Any]]:
    """
    Expand base window until all evidence bboxes are contained.
    Returns final window + expansion diagnostics.
    """
    window = base
    expansions = 0
    clipped_before = [
        b for b in evidence if b and not contains(window, b, eps=1.0)
    ]
    for _ in range(max_iters):
        missing = [b for b in evidence if b and not contains(window, b, eps=1.0)]
        if not missing:
            break
        uni = union_bbox([window] + missing)
        if not uni:
            break
        window = inflate_bbox(uni, pad_mm, pad_mm)
        expansions += 1
    still_clipped = [b for b in evidence if b and not contains(window, b, eps=1.0)]
    border_touch = [
        b for b in evidence if b and touches_border(window, b, tol=2.0)
    ]
    return window, {
        "expansions": expansions,
        "clipped_before_count": len(clipped_before),
        "still_clipped_count": len(still_clipped),
        "border_touch_count": len(border_touch),
        "expanded": expansions > 0,
    }


def bbox_area(b: BBox) -> float:
    return max(b[2] - b[0], 0.0) * max(b[3] - b[1], 0.0)


def point_in_bbox(x: float, y: float, b: BBox, eps: float = 1.0) -> bool:
    return b[0] - eps <= x <= b[2] + eps and b[1] - eps <= y <= b[3] + eps
