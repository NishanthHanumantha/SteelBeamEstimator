"""DXF entity probe helpers (read-only)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def find_entity_by_handle(msp, handle: str) -> Optional[Any]:
    h = str(handle).upper()
    for e in msp:
        try:
            if str(e.dxf.handle).upper() == h:
                return e
        except Exception:
            continue
    return None


def entity_record(entity) -> Dict[str, Any]:
    if entity is None:
        return {"found": False}
    rec: Dict[str, Any] = {
        "found": True,
        "handle": str(entity.dxf.handle),
        "dxftype": entity.dxftype(),
        "layer": str(entity.dxf.layer),
        "block_transform": "none_in_modelspace",
        "rotation": None,
        "scaling": None,
        "translation": None,
    }
    try:
        if entity.dxftype() == "LINE":
            s, e = entity.dxf.start, entity.dxf.end
            rec["raw_coords"] = {
                "start": [float(s.x), float(s.y)],
                "end": [float(e.x), float(e.y)],
            }
            rec["y_position"] = float((s.y + e.y) / 2.0)
        elif entity.dxftype() == "LWPOLYLINE":
            pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            rec["raw_coords"] = {"points": pts}
            rec["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
            rec["y_position"] = float(sum(ys) / len(ys)) if ys else None
    except Exception as exc:  # noqa: BLE001
        rec["error"] = str(exc)
    return rec


def find_line_by_coords(
    msp,
    *,
    y: float,
    start_x: float,
    end_x: float,
    layer: Optional[str] = None,
    tol: float = 2.0,
) -> Optional[Any]:
    x0, x1 = (start_x, end_x) if start_x <= end_x else (end_x, start_x)
    for e in msp.query("LINE"):
        if layer and e.dxf.layer != layer:
            continue
        s, en = e.dxf.start, e.dxf.end
        ey = (s.y + en.y) / 2.0
        if abs(ey - y) > tol:
            continue
        sx0, sx1 = (s.x, en.x) if s.x <= en.x else (en.x, s.x)
        if abs(sx0 - x0) < 5.0 and abs(sx1 - x1) < 5.0:
            return e
    return None
