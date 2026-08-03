"""
Beam-scoped crop extent (Track 1, 9.3.3).

Replaces the coarse ±1500mm blanket pad (pre-9.3.3) with a tight bounding
union of:
  - R.1's EXISTING annotation/association output for this beam_id
    (reinforcement_annotations.json `by_beam` — NOT re-derived here)
  - the beam-mark elevation label TEXT/MTEXT nearest that annotation
    cluster (disambiguates the elevation-view label from a same-named
    plan/schedule block located elsewhere on the sheet; see the 9.3.2
    diagnostic — plan/schedule marks sat ~25-29m away from the real
    elevation for every Set1 test beam)
  - a small fixed padding margin (default 350mm), shrunk (never below a
    floor) when it would otherwise overlap a neighboring beam's extent.

MODEL_VERSION: 9.3.3
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.3.3"

DEFAULT_PAD_MM = 350.0
MIN_PAD_MM = 50.0


def find_beam_mark(
    msp: Any, beam_id: str, near_xy: Tuple[float, float]
) -> Optional[Dict[str, Any]]:
    """Find the "<beam_id>(...)" TEXT/MTEXT occurrence nearest *near_xy*.

    Searches modelspace TEXT/MTEXT directly and inside INSERT blocks (via
    virtual_entities), matching an optional AutoCAD underline code prefix
    ("%%U"). Picking the occurrence CLOSEST to the beam's own annotation
    centroid (rather than the first match) is what avoids picking up a
    same-named plan/schedule block elsewhere on the sheet.
    """
    pat = re.compile(rf"{re.escape(beam_id)}\s*\(\s*\d", re.I)
    best: Optional[Dict[str, Any]] = None
    best_dist: Optional[float] = None

    def consider(text: str, x: float, y: float) -> None:
        nonlocal best, best_dist
        clean = (text or "").replace("%%U", "").replace("%%u", "")
        if not pat.search(clean):
            return
        dist = math.hypot(x - near_xy[0], y - near_xy[1])
        if best_dist is None or dist < best_dist:
            best = {"text": text, "x": x, "y": y}
            best_dist = dist

    for e in msp:
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        try:
            text = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
            x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
        except Exception:
            continue
        consider(text, x, y)

    try:
        inserts = msp.query("INSERT")
    except Exception:
        inserts = []
    for e in inserts:
        try:
            for ve in e.virtual_entities():
                if ve.dxftype() not in ("TEXT", "MTEXT"):
                    continue
                try:
                    text = ve.dxf.text if ve.dxftype() == "TEXT" else ve.plain_text()
                    x, y = float(ve.dxf.insert.x), float(ve.dxf.insert.y)
                except Exception:
                    continue
                consider(text, x, y)
        except Exception:
            continue

    return best


_LABEL_TYPES = frozenset(
    {"TEXT", "MTEXT", "DIMENSION", "MULTILEADER", "LEADER", "ATTRIB"}
)


def build_label_entity_index(msp: Any) -> List[Tuple[float, float, float, float]]:
    """Index of bboxes for every label-bearing entity (TEXT/MTEXT/DIMENSION/
    MULTILEADER/LEADER/ATTRIB) in modelspace, plus one level of
    INSERT-exploded TEXT/MTEXT.

    R.1's annotation x,y is an ANCHOR point only (no width/height) — a
    beam-scoped extent built purely from anchor points clips any callout
    whose rendered glyph extends beyond that anchor (e.g. a long label
    like "B2(200X600)", or a callout anchored at the annotation cluster's
    own outer edge). Resolving each annotation back to the real DXF
    entity's bbox (this index) instead of a zero-size point fixes that
    without re-deriving R.1's association — we only look up the entity
    the association already points at.
    """
    try:
        from ezdxf import bbox as ezdxf_bbox
    except ImportError:
        return []

    cache = ezdxf_bbox.Cache()
    index: List[Tuple[float, float, float, float]] = []

    def _add(entity) -> None:
        try:
            ext = ezdxf_bbox.extents([entity], cache=cache, fast=True)
        except Exception:
            return
        if not ext.has_data:
            return
        index.append((ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y))

    for e in msp:
        if e.dxftype() in _LABEL_TYPES:
            _add(e)

    try:
        inserts = msp.query("INSERT")
    except Exception:
        inserts = []
    for e in inserts:
        try:
            for ve in e.virtual_entities():
                if ve.dxftype() in ("TEXT", "MTEXT"):
                    _add(ve)
        except Exception:
            continue

    return index


def _resolve_bbox(
    index: List[Tuple[float, float, float, float]],
    x: float,
    y: float,
    tol: float = 250.0,
) -> Optional[Tuple[float, float, float, float]]:
    """Smallest indexed entity bbox that contains (x, y) within *tol* margin.

    Matching by "point falls inside bbox (± tol)" rather than "nearest bbox
    CENTER" is what makes this robust for multi-line MTEXT — R.1's anchor
    is the entity's insertion point (often a corner, not the visual
    center), so for a tall 3-line callout the center can sit further from
    the anchor than a small center-distance tolerance would allow, while
    the anchor point itself is reliably at or near the bbox boundary.
    Ties (multiple containing bboxes) are broken by preferring the
    SMALLEST bbox, so a big neighboring entity that happens to also
    contain the point doesn't win over the actual small callout.
    """
    best_bb: Optional[Tuple[float, float, float, float]] = None
    best_area: Optional[float] = None
    for bb in index:
        xmin, ymin, xmax, ymax = bb
        if xmin - tol <= x <= xmax + tol and ymin - tol <= y <= ymax + tol:
            area = max(xmax - xmin, 0.0) * max(ymax - ymin, 0.0)
            if best_area is None or area < best_area:
                best_area = area
                best_bb = bb
    return best_bb


def _points_and_bboxes_to_bounds(
    points: List[Tuple[float, float]],
    index: List[Tuple[float, float, float, float]],
) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    for x, y in points:
        bb = _resolve_bbox(index, x, y)
        if bb is not None:
            xs.extend([bb[0], bb[2]])
            ys.extend([bb[1], bb[3]])
        else:
            xs.append(x)
            ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys))


def _ranges_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return not (a1 < b0 or b1 < a0)


def _per_side_pads(
    beam_id: str,
    core: Tuple[float, float, float, float],
    all_cores: Dict[str, Tuple[float, float, float, float]],
    pad_mm: float,
    min_pad_mm: float,
) -> Tuple[Dict[str, float], List[str]]:
    """Shrink padding ONLY on the side(s) facing a close neighbor (R3: asymmetric
    shrink toward the beam's own entities, not a uniform radius) — a neighbor
    directly above must not steal margin from the beam's left/right sides.
    """
    pads = {"left": pad_mm, "right": pad_mm, "top": pad_mm, "bottom": pad_mm}
    notes: List[str] = []

    def _consider(side: str, gap: float, other_id: str) -> None:
        # gap >= 0: neighbor's core is genuinely separated on this side —
        # split the gap, each beam gets half (minus a small buffer).
        # gap <  0: the two beams' OWN annotation cores already overlap on
        # this axis (R3 — beams drawn closer together than any padding
        # margin allows). A full-depth overlap (>= pad_mm) is zeroed
        # entirely — leaving any pad there would reach past our own core
        # straight into the neighbor's callouts (the 9.3.3 B8/B13 bleed
        # found during the visual gate). But a SHALLOW, near-zero overlap
        # (a few mm — two independently-derived annotation cores just
        # barely touching, not a real visual collision) is graduated
        # linearly down from the full default pad instead of being
        # zeroed outright, so a beam sitting almost-but-not-quite next
        # to a neighbor isn't punished as if they were drawn overlapping
        # (this is what let B9's own "SIDE FACE REINF" callout be clipped
        # against a neighbor 5.8mm away with no real content that close).
        if gap >= 0:
            allowed = max(min_pad_mm, gap / 2.0 - 10.0)
        else:
            allowed = max(0.0, pad_mm + gap)
        if allowed < pads[side]:
            pads[side] = allowed
            tag = "shrunk" if gap >= 0 else "zeroed_overlap"
            notes.append(
                f"pad_{side}_{tag}_for_neighbor={other_id} gap_mm={gap:.1f} "
                f"pad_mm={allowed:.1f}"
            )

    for other_id, other_core in all_cores.items():
        if other_id == beam_id or other_core is None:
            continue
        # Horizontal neighbors (left/right) only matter if vertical extents overlap.
        if _ranges_overlap(core[1], core[3], other_core[1], other_core[3]):
            # "Relevant to our right side" requires the neighbor to actually
            # extend to/past our right edge — a neighbor entirely to our
            # LEFT must never be treated as a right-side collision just
            # because the raw (other.xmin - our.xmax) arithmetic goes very
            # negative; that sign alone doesn't mean the neighbor is on
            # the right, only that it's somewhere else on the sheet.
            if other_core[2] >= core[2]:
                _consider("right", other_core[0] - core[2], other_id)
            if other_core[0] <= core[0]:
                _consider("left", core[0] - other_core[2], other_id)
        # Vertical neighbors (top/bottom) only matter if horizontal extents overlap.
        if _ranges_overlap(core[0], core[2], other_core[0], other_core[2]):
            if other_core[3] >= core[3]:
                _consider("top", other_core[1] - core[3], other_id)
            if other_core[1] <= core[1]:
                _consider("bottom", core[1] - other_core[3], other_id)
    return pads, notes


def compute_beam_scoped_extent(
    beam_id: str,
    annotation_items: List[Dict[str, Any]],
    msp: Any,
    *,
    pad_mm: float = DEFAULT_PAD_MM,
    min_pad_mm: float = MIN_PAD_MM,
    neighbor_cores: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
) -> Dict[str, Any]:
    """
    Returns dict with:
      beam_id, extent (xmin,ymin,xmax,ymax) or None, core (unpadded union),
      mark (beam-mark match or None), pad_used_mm, notes (list[str]).
    """
    points = [
        (float(a["x"]), float(a["y"]))
        for a in annotation_items
        if a.get("x") is not None and a.get("y") is not None
    ]
    if not points:
        return {
            "beam_id": beam_id,
            "extent": None,
            "core": None,
            "mark": None,
            "pad_used_mm": None,
            "notes": ["no_annotations_for_beam"],
        }

    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    mark = find_beam_mark(msp, beam_id, (cx, cy))
    if mark is not None:
        points = points + [(mark["x"], mark["y"])]

    index = build_label_entity_index(msp)
    core = _points_and_bboxes_to_bounds(points, index)
    pads, notes = _per_side_pads(
        beam_id, core, neighbor_cores or {}, pad_mm, min_pad_mm
    )

    extent = (
        core[0] - pads["left"],
        core[1] - pads["bottom"],
        core[2] + pads["right"],
        core[3] + pads["top"],
    )
    return {
        "beam_id": beam_id,
        "extent": extent,
        "core": core,
        "mark": mark,
        "pad_used_mm": {k: round(v, 1) for k, v in pads.items()},
        "notes": notes,
    }


def compute_extents_for_beams(
    beam_ids: List[str],
    annotations_by_beam: Dict[str, List[Dict[str, Any]]],
    msp: Any,
    *,
    pad_mm: float = DEFAULT_PAD_MM,
    min_pad_mm: float = MIN_PAD_MM,
) -> Dict[str, Dict[str, Any]]:
    """Batch version: computes unpadded cores for ALL beams first so pad
    shrinking (neighbor-awareness) is possible even for a single-beam
    lookup elsewhere. Only `beam_ids` are returned, but neighbor cores are
    drawn from `annotations_by_beam` in full so an out-of-scope neighbor
    (e.g. a beam not in this phase's residual target list) still prevents
    bleed-over.
    """
    index = build_label_entity_index(msp)
    all_cores: Dict[str, Tuple[float, float, float, float]] = {}
    all_marks: Dict[str, Optional[Dict[str, Any]]] = {}
    for bid, items in annotations_by_beam.items():
        points = [
            (float(a["x"]), float(a["y"]))
            for a in items
            if a.get("x") is not None and a.get("y") is not None
        ]
        if not points:
            continue
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        mark = find_beam_mark(msp, bid, (cx, cy))
        all_marks[bid] = mark
        if mark is not None:
            points = points + [(mark["x"], mark["y"])]
        all_cores[bid] = _points_and_bboxes_to_bounds(points, index)

    out: Dict[str, Dict[str, Any]] = {}
    for bid in beam_ids:
        core = all_cores.get(bid)
        if core is None:
            out[bid] = {
                "beam_id": bid,
                "extent": None,
                "core": None,
                "mark": None,
                "pad_used_mm": None,
                "notes": ["no_annotations_for_beam"],
            }
            continue
        others = {k: v for k, v in all_cores.items() if k != bid}
        pads, notes = _per_side_pads(bid, core, others, pad_mm, min_pad_mm)
        extent = (
            core[0] - pads["left"],
            core[1] - pads["bottom"],
            core[2] + pads["right"],
            core[3] + pads["top"],
        )
        out[bid] = {
            "beam_id": bid,
            "extent": extent,
            "core": core,
            "mark": all_marks.get(bid),
            "pad_used_mm": {k: round(v, 1) for k, v in pads.items()},
            "notes": notes,
        }
    return out
