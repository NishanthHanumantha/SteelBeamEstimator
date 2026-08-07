"""
Read-only DXF probing for QA.3.2 (metadata + entity counts in crops).
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .geometry_utils import BBox, as_bbox, entity_in_bbox, intersection

MODEL_VERSION = "10.0.2"

# Cache: resolved dxf path -> list of (dxftype, bbox)
_ENTITY_CACHE: Dict[str, List[Tuple[str, Optional[BBox]]]] = {}

_BARISH = frozenset({"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "SPLINE", "ELLIPSE"})
_TEXTISH = frozenset({"TEXT", "MTEXT", "ATTRIB", "ATTDEF"})
_LEADERISH = frozenset({"LEADER", "MULTILEADER", "MLEADER"})
_DIMISH = frozenset({"DIMENSION", "TOLERANCE"})


def probe_dxf_metadata(dxf_path: Optional[Path]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "path": str(dxf_path) if dxf_path else None,
        "exists": bool(dxf_path and Path(dxf_path).exists()),
        "sheet_layout": None,
        "space": None,
        "drawing_scale": None,
        "units": None,
        "units_name": None,
        "insunits": None,
        "error": None,
    }
    if not out["exists"]:
        out["error"] = "missing_dxf"
        return out
    try:
        import ezdxf

        doc = ezdxf.readfile(str(dxf_path))
        header = doc.header
        insunits = header.get("$INSUNITS")
        out["insunits"] = insunits
        try:
            from ezdxf import units as ez_units

            out["units_name"] = ez_units.decode(insunits) if insunits is not None else None
        except Exception:
            out["units_name"] = str(insunits)
        out["units"] = out["units_name"] or str(insunits)
        out["drawing_scale"] = header.get("$DIMSCALE")
        layouts = [ly.name for ly in doc.layouts if ly.name]
        out["sheet_layout"] = layouts
        # Reinforcement details typically authored in model space
        out["space"] = "Model Space"
        out["layout_count"] = len(layouts)
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _entity_bbox(entity, cache) -> Optional[BBox]:
    try:
        from ezdxf import bbox as ezdxf_bbox

        ext = ezdxf_bbox.extents([entity], cache=cache, fast=True)
        if not ext.has_data:
            return None
        return as_bbox((ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y))
    except Exception:
        return None


def _load_entity_index(dxf_path: Path) -> List[Tuple[str, Optional[BBox]]]:
    key = str(Path(dxf_path).resolve())
    if key in _ENTITY_CACHE:
        return _ENTITY_CACHE[key]
    import ezdxf
    from ezdxf import bbox as ezdxf_bbox

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    cache = ezdxf_bbox.Cache()
    items: List[Tuple[str, Optional[BBox]]] = []
    for ent in msp:
        items.append((ent.dxftype(), _entity_bbox(ent, cache)))
    _ENTITY_CACHE[key] = items
    return items


def count_entities_in_crop(
    dxf_path: Path, crop: BBox, *, tol_frac: float = 0.02
) -> Dict[str, Any]:
    """Count DXF entities whose bbox intersects crop."""
    empty = {
        "bars_approx": 0,
        "leaders": 0,
        "leader_arrows": 0,
        "TEXT": 0,
        "MTEXT": 0,
        "dimensions": 0,
        "blocks": 0,
        "polylines": 0,
        "lines": 0,
        "arcs": 0,
        "total": 0,
        "by_type": {},
        "error": None,
    }
    if not dxf_path or not Path(dxf_path).exists() or not crop:
        empty["error"] = "missing_dxf_or_crop"
        return empty
    try:
        items = _load_entity_index(Path(dxf_path))
        w = max(crop[2] - crop[0], 1e-6)
        h = max(crop[3] - crop[1], 1e-6)
        tol = max(w, h) * tol_frac

        by_type: Dict[str, int] = {}
        counts = {k: 0 for k in empty if k not in ("by_type", "error", "total")}
        total = 0
        for dt, bb in items:
            if not entity_in_bbox(bb, crop, tol=tol):
                continue
            total += 1
            by_type[dt] = by_type.get(dt, 0) + 1
            if dt in _BARISH:
                counts["bars_approx"] += 1
            if dt in _LEADERISH:
                counts["leaders"] += 1
                counts["leader_arrows"] += 1
            if dt == "TEXT":
                counts["TEXT"] += 1
            if dt == "MTEXT":
                counts["MTEXT"] += 1
            if dt in _DIMISH:
                counts["dimensions"] += 1
            if dt == "INSERT":
                counts["blocks"] += 1
            if dt in ("LWPOLYLINE", "POLYLINE"):
                counts["polylines"] += 1
            if dt == "LINE":
                counts["lines"] += 1
            if dt == "ARC":
                counts["arcs"] += 1

        return {**counts, "total": total, "by_type": by_type, "error": None}
    except Exception as exc:
        empty["error"] = str(exc)
        return empty


def completeness_compare(
    expected_counts: Dict[str, Any], actual_counts: Dict[str, Any]
) -> Dict[str, Any]:
    keys = (
        "bars_approx",
        "leaders",
        "leader_arrows",
        "TEXT",
        "MTEXT",
        "dimensions",
        "blocks",
        "polylines",
        "lines",
        "arcs",
        "total",
    )
    missing: Dict[str, int] = {}
    extra: Dict[str, int] = {}
    for k in keys:
        e = int(expected_counts.get(k) or 0)
        a = int(actual_counts.get(k) or 0)
        if e > a:
            missing[k] = e - a
        elif a > e:
            extra[k] = a - e
    e_tot = max(int(expected_counts.get("total") or 0), 1)
    a_tot = int(actual_counts.get("total") or 0)
    # Completeness: how much of expected entity mass is covered by actual crop
    covered = min(a_tot, e_tot)
    # Prefer intersection-style: if actual is subset of expected region, a_tot/e_tot
    completeness = round(100.0 * min(1.0, a_tot / e_tot), 2)
    return {
        "missing_entities": missing,
        "extra_entities": extra,
        "missing_bars": int(missing.get("bars_approx") or 0),
        "missing_annotations": int(
            (missing.get("TEXT") or 0)
            + (missing.get("MTEXT") or 0)
            + (missing.get("dimensions") or 0)
        ),
        "missing_leaders": int(missing.get("leaders") or 0),
        "unexpected_entities": int(sum(extra.values())),
        "completeness_pct": completeness,
        "expected_total": e_tot,
        "actual_total": a_tot,
        "covered_proxy": covered,
    }


def neighbour_beam_intrusion(
    beam_bbox: BBox,
    crop: BBox,
    other_extents: Dict[str, BBox],
    self_id: str,
) -> Dict[str, Any]:
    intruders = []
    for bid, ext in other_extents.items():
        if bid == self_id or not ext:
            continue
        inter = intersection(ext, crop)
        if not inter:
            continue
        # Significant if neighbour center is inside crop or overlap area > 5% of neighbour
        from .geometry_utils import bbox_area, bbox_center

        cx, cy = bbox_center(ext)
        inside = crop[0] <= cx <= crop[2] and crop[1] <= cy <= crop[3]
        overlap_frac = bbox_area(inter) / max(bbox_area(ext), 1e-9)
        if inside or overlap_frac >= 0.05:
            intruders.append(
                {
                    "beam_id": bid,
                    "overlap_frac": round(overlap_frac, 4),
                    "centroid_inside_crop": inside,
                }
            )
    return {
        "neighbour_intrusion": len(intruders) > 0,
        "multiple_beams_visible": len(intruders) > 0,
        "intruders": intruders[:10],
        "intruder_count": len(intruders),
    }
