"""
T1.6 Step 1 — Complete DXF entity inventory (no ownership yet).
MODEL_VERSION: 9.3.6
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.3.6"

DRAWABLE_TYPES = frozenset(
    {
        "LINE",
        "LWPOLYLINE",
        "POLYLINE",
        "ARC",
        "CIRCLE",
        "DIMENSION",
        "TEXT",
        "MTEXT",
        "LEADER",
        "MLINE",
        "SPLINE",
        "INSERT",
        "ELLIPSE",
        "HATCH",
        "SOLID",
        "TRACE",
        "POINT",
        "MULTILEADER",
        "ATTRIB",
        "ATTDEF",
    }
)


def _safe_handle(entity) -> str:
    try:
        h = entity.dxf.handle
        if h is not None:
            return str(h).upper()
    except Exception:
        pass
    return ""


def _safe_layer(entity) -> str:
    try:
        return str(entity.dxf.layer or "")
    except Exception:
        return ""


def _safe_color(entity) -> Any:
    try:
        return entity.dxf.color
    except Exception:
        return None


def _safe_linetype(entity) -> str:
    try:
        return str(entity.dxf.linetype or "")
    except Exception:
        return ""


def _bbox_of(entity, cache) -> Optional[Tuple[float, float, float, float]]:
    try:
        from ezdxf import bbox as ezbbox

        ext = ezbbox.extents([entity], cache=cache, fast=True)
        if not ext.has_data:
            return None
        return (
            float(ext.extmin.x),
            float(ext.extmin.y),
            float(ext.extmax.x),
            float(ext.extmax.y),
        )
    except Exception:
        return None


def _centroid(bb: Optional[Tuple[float, float, float, float]]) -> Optional[List[float]]:
    if not bb:
        return None
    return [round(0.5 * (bb[0] + bb[2]), 3), round(0.5 * (bb[1] + bb[3]), 3)]


def _extract_geometry(entity) -> Dict[str, Any]:
    """Type-specific geometric fields."""
    dtype = entity.dxftype()
    out: Dict[str, Any] = {
        "length": None,
        "radius": None,
        "start_point": None,
        "end_point": None,
        "vertices": None,
        "rotation": None,
        "text": None,
        "dimension_text": None,
        "leader_target": None,
    }
    try:
        if dtype == "LINE":
            s, e = entity.dxf.start, entity.dxf.end
            sx, sy = float(s.x), float(s.y)
            ex, ey = float(e.x), float(e.y)
            out["start_point"] = [round(sx, 3), round(sy, 3)]
            out["end_point"] = [round(ex, 3), round(ey, 3)]
            out["length"] = round(math.hypot(ex - sx, ey - sy), 3)
        elif dtype == "LWPOLYLINE":
            pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
            out["vertices"] = [[round(x, 3), round(y, 3)] for x, y in pts]
            if len(pts) >= 2:
                out["start_point"] = out["vertices"][0]
                out["end_point"] = out["vertices"][-1]
                length = 0.0
                for i in range(len(pts) - 1):
                    length += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                out["length"] = round(length, 3)
        elif dtype == "CIRCLE":
            c = entity.dxf.center
            out["start_point"] = [round(float(c.x), 3), round(float(c.y), 3)]
            out["radius"] = round(float(entity.dxf.radius), 3)
        elif dtype == "ARC":
            c = entity.dxf.center
            out["start_point"] = [round(float(c.x), 3), round(float(c.y), 3)]
            out["radius"] = round(float(entity.dxf.radius), 3)
            out["rotation"] = [
                round(float(entity.dxf.start_angle), 3),
                round(float(entity.dxf.end_angle), 3),
            ]
        elif dtype in ("TEXT", "ATTRIB", "ATTDEF"):
            ins = entity.dxf.insert
            out["start_point"] = [round(float(ins.x), 3), round(float(ins.y), 3)]
            out["text"] = str(entity.dxf.text or "")
            try:
                out["rotation"] = round(float(entity.dxf.rotation), 3)
            except Exception:
                pass
        elif dtype == "MTEXT":
            ins = entity.dxf.insert
            out["start_point"] = [round(float(ins.x), 3), round(float(ins.y), 3)]
            try:
                out["text"] = entity.plain_text()
            except Exception:
                out["text"] = str(getattr(entity.dxf, "text", "") or "")
        elif dtype == "DIMENSION":
            try:
                p = entity.dxf.defpoint
                out["start_point"] = [round(float(p.x), 3), round(float(p.y), 3)]
            except Exception:
                pass
            try:
                out["dimension_text"] = str(entity.dxf.text or "")
            except Exception:
                out["dimension_text"] = ""
            try:
                out["text"] = out["dimension_text"]
            except Exception:
                pass
        elif dtype == "LEADER":
            verts = [(float(v[0]), float(v[1])) for v in entity.vertices]
            out["vertices"] = [[round(x, 3), round(y, 3)] for x, y in verts]
            if verts:
                out["start_point"] = out["vertices"][0]  # tip
                out["end_point"] = out["vertices"][-1]  # tail
                out["leader_target"] = out["start_point"]
                length = 0.0
                for i in range(len(verts) - 1):
                    length += math.hypot(
                        verts[i + 1][0] - verts[i][0], verts[i + 1][1] - verts[i][1]
                    )
                out["length"] = round(length, 3)
        elif dtype == "INSERT":
            ins = entity.dxf.insert
            out["start_point"] = [round(float(ins.x), 3), round(float(ins.y), 3)]
            try:
                out["rotation"] = round(float(entity.dxf.rotation), 3)
            except Exception:
                pass
            try:
                out["text"] = str(entity.dxf.name or "")
            except Exception:
                pass
        elif dtype == "POINT":
            loc = entity.dxf.location
            out["start_point"] = [round(float(loc.x), 3), round(float(loc.y), 3)]
        elif dtype == "ELLIPSE":
            c = entity.dxf.center
            out["start_point"] = [round(float(c.x), 3), round(float(c.y), 3)]
        elif dtype == "SPLINE":
            try:
                pts = list(entity.control_points)
                out["vertices"] = [
                    [round(float(p[0]), 3), round(float(p[1]), 3)] for p in pts
                ]
                if out["vertices"]:
                    out["start_point"] = out["vertices"][0]
                    out["end_point"] = out["vertices"][-1]
            except Exception:
                pass
    except Exception:
        pass
    return out


def build_entity_inventory(msp: Any) -> Dict[str, Any]:
    """Scan modelspace once; return inventory dict with entities list."""
    try:
        from ezdxf import bbox as ezbbox

        cache = ezbbox.Cache()
    except Exception:
        cache = None

    entities: List[Dict[str, Any]] = []
    by_type: Dict[str, int] = {}
    skipped_no_handle = 0

    for entity in msp:
        dtype = entity.dxftype()
        if dtype not in DRAWABLE_TYPES:
            continue
        handle = _safe_handle(entity)
        if not handle:
            skipped_no_handle += 1
            # Still inventory with synthetic key so nothing is silently lost
            handle = f"SYN::{dtype}::{len(entities):06d}"

        bb = _bbox_of(entity, cache) if cache is not None else None
        geom = _extract_geometry(entity)
        rec = {
            "entity_handle": handle,
            "entity_type": dtype,
            "layer": _safe_layer(entity),
            "color": _safe_color(entity),
            "linetype": _safe_linetype(entity),
            "bounding_box": (
                [round(bb[0], 3), round(bb[1], 3), round(bb[2], 3), round(bb[3], 3)]
                if bb
                else None
            ),
            "centroid": _centroid(bb),
            **geom,
        }
        entities.append(rec)
        by_type[dtype] = by_type.get(dtype, 0) + 1

    return {
        "phase_id": "T1.6",
        "model_version": MODEL_VERSION,
        "entity_count": len(entities),
        "by_type": by_type,
        "skipped_no_handle": skipped_no_handle,
        "entities": entities,
    }


def inventory_index(
    inventory: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """handle → entity record."""
    return {
        str(e["entity_handle"]).upper(): e
        for e in (inventory.get("entities") or [])
        if e.get("entity_handle")
    }
