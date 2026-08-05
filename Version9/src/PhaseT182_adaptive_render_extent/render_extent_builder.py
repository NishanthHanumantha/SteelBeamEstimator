"""
T1.8.2 — Build adaptive render extent from owned graphical objects.
MODEL_VERSION: 9.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .adaptive_bbox import (
    BBox,
    estimate_text_bbox,
    inflate_bbox,
    object_record,
    point_bbox,
    segment_bbox,
    union_bbox,
)

MODEL_VERSION = "9.5.2"

# Configurable safety margins (fraction of union size)
DEFAULT_MARGIN_FRAC_X = 0.08
DEFAULT_MARGIN_FRAC_Y = 0.08
MIN_MARGIN_MM = 80.0
ARROW_PAD_MM = 55.0
BAR_PAD_MM = 20.0


def _beam_bbox(nodes: List[Dict[str, Any]]) -> Optional[BBox]:
    for n in nodes:
        if n.get("type") != "Beam":
            continue
        ext = (n.get("attributes") or {}).get("extent")
        if ext and len(ext) >= 4:
            return (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))
    return None


def collect_owned_objects(
    scoped: Dict[str, Any],
    *,
    inventory_by_handle: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Enumerate every owned graphical primitive that must be visible."""
    nodes = list(scoped.get("nodes") or [])
    inv = inventory_by_handle or {}
    objects: List[Dict[str, Any]] = []

    beam_bb = _beam_bbox(nodes)
    if beam_bb:
        objects.append(object_record("BEAM_OUTLINE", "beam_geometry", beam_bb))

    for n in nodes:
        t = n.get("type")
        a = n.get("attributes") or {}
        nid = n.get("id") or "?"

        if t == "PhysicalBar":
            try:
                bb = segment_bbox(
                    float(a["start_x"]),
                    float(a["y_position"]),
                    float(a["end_x"]),
                    float(a["y_position"]),
                    pad=BAR_PAD_MM,
                )
            except Exception:
                continue
            objects.append(object_record(nid, "owned_bar", bb))

        elif t == "OwnedEntity":
            role = str(a.get("role") or "")
            if role not in ("TOP_BAR", "BOTTOM_BAR", "LONGITUDINAL_BAR"):
                continue
            h = str(a.get("handle") or "").upper()
            ent = inv.get(h) or {}
            sp, ep = ent.get("start_point"), ent.get("end_point")
            if not sp or not ep:
                continue
            try:
                x0, y0 = float(sp[0]), float(sp[1])
                x1, y1 = float(ep[0]), float(ep[1])
            except Exception:
                continue
            if abs(y1 - y0) > 80:
                continue
            # Clip horizontal contribution lightly to beam X if available
            if beam_bb:
                x0c = max(min(x0, x1), beam_bb[0] - 200)
                x1c = min(max(x0, x1), beam_bb[2] + 200)
            else:
                x0c, x1c = min(x0, x1), max(x0, x1)
            y = 0.5 * (y0 + y1)
            bb = segment_bbox(x0c, y, x1c, y, pad=BAR_PAD_MM)
            objects.append(object_record(nid, "owned_bar_entity", bb, {"handle": h}))

        elif t == "Leader":
            try:
                tip_x, tip_y = float(a["tip_x"]), float(a["tip_y"])
                tail_x, tail_y = float(a["tail_x"]), float(a["tail_y"])
            except Exception:
                continue
            line_bb = segment_bbox(tip_x, tip_y, tail_x, tail_y, pad=8.0)
            objects.append(object_record(nid, "owned_leader", line_bb))
            # Arrowhead at tip
            objects.append(
                object_record(
                    f"{nid}::ARROW",
                    "owned_arrowhead",
                    point_bbox(tip_x, tip_y, pad=ARROW_PAD_MM),
                )
            )
            # Elbow proxy: midpoint when multi-vertex leaders (no vertex list in graph)
            vc = int(a.get("vertex_count") or 2)
            if vc >= 3:
                mx, my = 0.5 * (tip_x + tail_x), 0.5 * (tip_y + tail_y)
                objects.append(
                    object_record(
                        f"{nid}::ELBOW",
                        "owned_leader_elbow",
                        point_bbox(mx, my, pad=40.0),
                    )
                )

        elif t == "LeaderArrow":
            try:
                x, y = float(a.get("x", a.get("tip_x"))), float(
                    a.get("y", a.get("tip_y"))
                )
            except Exception:
                continue
            objects.append(
                object_record(nid, "owned_arrowhead", point_bbox(x, y, pad=ARROW_PAD_MM))
            )

        elif t == "LeaderTarget":
            try:
                x, y = float(a.get("x", a.get("tip_x"))), float(
                    a.get("y", a.get("tip_y"))
                )
            except Exception:
                continue
            objects.append(object_record(nid, "owned_leader_target", point_bbox(x, y, 30)))

        elif t == "Annotation":
            try:
                x, y = float(a["x"]), float(a["y"])
            except Exception:
                continue
            text = str(a.get("clean_text") or "")
            # Anchor marker
            objects.append(object_record(nid, "owned_annotation_anchor", point_bbox(x, y, 25)))
            # Text / MTEXT extent
            tbb = estimate_text_bbox(x, y, text)
            objects.append(
                object_record(
                    f"{nid}::TEXT",
                    "owned_annotation_text",
                    tbb,
                    {"text": text},
                )
            )

    return objects


def build_render_extent(
    beam_id: str,
    scoped: Dict[str, Any],
    *,
    inventory_by_handle: Optional[Dict[str, Dict[str, Any]]] = None,
    margin_frac_x: float = DEFAULT_MARGIN_FRAC_X,
    margin_frac_y: float = DEFAULT_MARGIN_FRAC_Y,
    min_margin_mm: float = MIN_MARGIN_MM,
) -> Dict[str, Any]:
    """
    render_bbox = inflate(UNION(owned graphical objects), margin)
    """
    nodes = list(scoped.get("nodes") or [])
    beam_bb = _beam_bbox(nodes)
    objects = collect_owned_objects(scoped, inventory_by_handle=inventory_by_handle)
    owned_union = union_bbox(tuple(o["bbox"]) for o in objects)
    if not owned_union and beam_bb:
        owned_union = beam_bb
    if not owned_union:
        return {
            "beam": beam_id,
            "success": False,
            "error": "no_owned_geometry",
            "model_version": MODEL_VERSION,
        }

    w = max(owned_union[2] - owned_union[0], 1.0)
    h = max(owned_union[3] - owned_union[1], 1.0)
    mx = max(min_margin_mm, margin_frac_x * w)
    my = max(min_margin_mm, margin_frac_y * h)
    render_bb = inflate_bbox(owned_union, mx, my)

    return {
        "beam": beam_id,
        "success": True,
        "model_version": MODEL_VERSION,
        "beam_bbox": list(beam_bb) if beam_bb else None,
        "owned_union_bbox": list(owned_union),
        "computed_render_bbox": list(render_bb),
        "margin_applied": {
            "horizontal_mm": mx,
            "vertical_mm": my,
            "frac_x": margin_frac_x,
            "frac_y": margin_frac_y,
            "min_margin_mm": min_margin_mm,
        },
        "largest_margin_used": max(mx, my),
        "owned_object_count": len(objects),
        "owned_objects": objects,
    }


def apply_extent_to_scoped_copy(
    scoped: Dict[str, Any], render_bbox: Sequence[float]
) -> Dict[str, Any]:
    """
    In-memory only: set Beam.attributes.extent so T1.8.1 renderer uses
    the adaptive viewport without modifying T1.8.1 source.
    """
    import copy

    scoped2 = copy.deepcopy(scoped)
    rb = [float(render_bbox[0]), float(render_bbox[1]), float(render_bbox[2]), float(render_bbox[3])]
    found = False
    for n in scoped2.get("nodes") or []:
        if n.get("type") == "Beam":
            attrs = n.setdefault("attributes", {})
            attrs["extent"] = rb
            attrs["adaptive_render_extent"] = True
            attrs["adaptive_render_model_version"] = MODEL_VERSION
            found = True
            break
    if not found:
        scoped2.setdefault("nodes", []).append(
            {
                "id": f"BEAM::{scoped.get('beam_id') or 'UNK'}::ADAPTIVE",
                "type": "Beam",
                "beam_id": scoped.get("beam_id"),
                "attributes": {
                    "extent": rb,
                    "adaptive_render_extent": True,
                },
            }
        )
    return scoped2
