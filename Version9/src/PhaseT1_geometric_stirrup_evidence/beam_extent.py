"""
Beam-scoped crop extent (Track 1, 9.3.4).

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
    floor) when it would otherwise overlap a neighboring beam's extent

9.3.4: after per-side pad shrink, apply a hard NON-OVERLAP split between
beams that share an elevation row (same Y-band of beam-mark labels).
Adjacent extents are pinned to a shared X boundary at the mark-midpoint
(with asymmetric widening if that midpoint would cut a beam's own R.1
annotation anchors). This fixes the B8 bleed-over / B9–B10 truncation
failure mode that pad-shrinking alone could not resolve.

MODEL_VERSION: 9.3.4
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.3.4"

DEFAULT_PAD_MM = 350.0
MIN_PAD_MM = 50.0
# Beams whose marks sit within this Y distance are treated as one
# elevation row for the hard non-overlap split (B8/B9/B10 share y≈16081).
ROW_Y_BAND_MM = 2000.0
# Extra margin past a beam's own R.1 annotation anchors so glyph extents
# just beyond the anchor aren't treated as "neighbor bleed" when deciding
# asymmetric split widening. Kept small so it cannot recreate ±1500mm bleed.
OWN_CONTENT_GLYPH_MARGIN_MM = 200.0


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


def _own_content_x_span(
    annotation_items: List[Dict[str, Any]],
    mark: Optional[Dict[str, Any]],
    *,
    glyph_margin_mm: float = OWN_CONTENT_GLYPH_MARGIN_MM,
) -> Optional[Tuple[float, float]]:
    """X-span of this beam's OWN R.1 anchors + mark (not bloated bbox union).

    Used by the row non-overlap split to decide asymmetric widening: a
    midpoint that sits past this span is safe to clip to; one that cuts
    inside it must be pushed outward so real callout anchors aren't lost.
    Deliberately ignores the resolved-entity bbox union (which can suck in
    a neighbor fragment via an oversized DIMENSION match — the B8 bleed
    root cause under 9.3.3).
    """
    xs = [
        float(a["x"])
        for a in annotation_items
        if a.get("x") is not None
    ]
    if mark is not None:
        xs.append(float(mark["x"]))
    if not xs:
        return None
    return (min(xs) - glyph_margin_mm, max(xs) + glyph_margin_mm)


def _apply_row_nonoverlap_splits(
    extents: Dict[str, Dict[str, Any]],
    own_x_spans: Dict[str, Tuple[float, float]],
    *,
    row_y_band_mm: float = ROW_Y_BAND_MM,
) -> None:
    """In-place: pin adjacent same-row extents to a shared X boundary.

    For each elevation row (beams whose marks share a Y-band), sort by
    mark X and for every adjacent pair (L, R):
      1. Prefer split = midpoint of the two mark X positions.
      2. If that midpoint would cut L's own-content xmax, widen L's share
         (split := own_xmax_L) — and symmetrically for R's own-content xmin.
      3. If both own-content spans cross (true content collision), fall
         back to the midpoint of the own-content overlap zone.
      4. Set L.extent.xmax = R.extent.xmin = split (no gap, no overlap).

    Handles the middle beam of a 3+ pack (B9 bounded on BOTH sides) by
    applying the rule pairwise left-then-right in mark-X order.
    """
    # Group beams that have both an extent and a mark into Y-band rows.
    marked = [
        (bid, info)
        for bid, info in extents.items()
        if info.get("extent") is not None and info.get("mark") is not None
    ]
    if len(marked) < 2:
        return

    # Greedy clustering by mark Y (sort then chain within band).
    marked.sort(key=lambda t: t[1]["mark"]["y"])
    rows: List[List[str]] = []
    current: List[str] = []
    current_y: Optional[float] = None
    for bid, info in marked:
        y = float(info["mark"]["y"])
        if current_y is None or abs(y - current_y) <= row_y_band_mm:
            current.append(bid)
            if current_y is None:
                current_y = y
            else:
                # keep running mean so a slow drift doesn't chain forever
                current_y = (current_y * (len(current) - 1) + y) / len(current)
        else:
            if len(current) >= 2:
                rows.append(current)
            current = [bid]
            current_y = y
    if len(current) >= 2:
        rows.append(current)

    for row in rows:
        row_sorted = sorted(row, key=lambda b: float(extents[b]["mark"]["x"]))
        for i in range(len(row_sorted) - 1):
            left_id = row_sorted[i]
            right_id = row_sorted[i + 1]
            left = extents[left_id]
            right = extents[right_id]
            mark_mid = 0.5 * (
                float(left["mark"]["x"]) + float(right["mark"]["x"])
            )

            left_own = own_x_spans.get(left_id)
            right_own = own_x_spans.get(right_id)
            split = mark_mid
            asymmetric_notes: List[str] = []

            if left_own is not None and right_own is not None:
                left_own_xmax = left_own[1]
                right_own_xmin = right_own[0]
                if left_own_xmax <= right_own_xmin:
                    # Own-content spans do not collide — clamp mark mid
                    # into the gap so neither beam loses its own anchors.
                    split = min(max(mark_mid, left_own_xmax), right_own_xmin)
                    if split > mark_mid + 1e-6:
                        asymmetric_notes.append(
                            f"row_split_asymmetric_widen_left={left_id} "
                            f"mark_mid={mark_mid:.1f} -> {split:.1f} "
                            f"(own_xmax={left_own_xmax:.1f})"
                        )
                    elif split < mark_mid - 1e-6:
                        asymmetric_notes.append(
                            f"row_split_asymmetric_widen_right={right_id} "
                            f"mark_mid={mark_mid:.1f} -> {split:.1f} "
                            f"(own_xmin={right_own_xmin:.1f})"
                        )
                else:
                    # Own-content spans overlap — split the overlap zone.
                    if right_own_xmin <= mark_mid <= left_own_xmax:
                        split = mark_mid
                    else:
                        split = 0.5 * (right_own_xmin + left_own_xmax)
                    asymmetric_notes.append(
                        f"row_split_own_content_overlap {left_id}/{right_id} "
                        f"overlap=[{right_own_xmin:.1f},{left_own_xmax:.1f}] "
                        f"split={split:.1f}"
                    )

            lx0, ly0, lx1, ly1 = left["extent"]
            rx0, ry0, rx1, ry1 = right["extent"]
            prev_l_xmax, prev_r_xmin = lx1, rx0
            left["extent"] = (lx0, ly0, split, ly1)
            right["extent"] = (split, ry0, rx1, ry1)
            note = (
                f"row_split_{left_id}_{right_id} x={split:.1f} "
                f"(was L.xmax={prev_l_xmax:.1f} R.xmin={prev_r_xmin:.1f}; "
                f"mark_mid={mark_mid:.1f})"
            )
            left.setdefault("notes", []).append(note)
            right.setdefault("notes", []).append(note)
            for n in asymmetric_notes:
                left["notes"].append(n)
                right["notes"].append(n)


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

    Note: single-beam call cannot apply the 9.3.4 row non-overlap split
    (needs sibling marks). Prefer compute_extents_for_beams for production.
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

    9.3.4: after pad-aware extents are built, applies a hard non-overlap
    X-split between beams sharing an elevation row (mark Y-band).
    """
    index = build_label_entity_index(msp)
    all_cores: Dict[str, Tuple[float, float, float, float]] = {}
    all_marks: Dict[str, Optional[Dict[str, Any]]] = {}
    all_own_x: Dict[str, Tuple[float, float]] = {}
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
        own = _own_content_x_span(items, mark)
        if own is not None:
            all_own_x[bid] = own
        if mark is not None:
            points = points + [(mark["x"], mark["y"])]
        all_cores[bid] = _points_and_bboxes_to_bounds(points, index)

    # Build extents for EVERY beam with a core (not just beam_ids) so the
    # row-split sees full-row neighbors even when the caller only asked
    # for a subset.
    all_out: Dict[str, Dict[str, Any]] = {}
    for bid, core in all_cores.items():
        others = {k: v for k, v in all_cores.items() if k != bid}
        pads, notes = _per_side_pads(bid, core, others, pad_mm, min_pad_mm)
        extent = (
            core[0] - pads["left"],
            core[1] - pads["bottom"],
            core[2] + pads["right"],
            core[3] + pads["top"],
        )
        all_out[bid] = {
            "beam_id": bid,
            "extent": extent,
            "core": core,
            "mark": all_marks.get(bid),
            "pad_used_mm": {k: round(v, 1) for k, v in pads.items()},
            "notes": notes,
        }

    _apply_row_nonoverlap_splits(all_out, all_own_x)

    out: Dict[str, Dict[str, Any]] = {}
    for bid in beam_ids:
        if bid in all_out:
            out[bid] = all_out[bid]
        else:
            out[bid] = {
                "beam_id": bid,
                "extent": None,
                "core": None,
                "mark": None,
                "pad_used_mm": None,
                "notes": ["no_annotations_for_beam"],
            }
    return out
