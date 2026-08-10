"""
Read-only DXF geometry probe for Stage 1 (does not modify detectors).
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Set


def build_dxf_beam_index(dxf_path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """
    Index beam-mark text locations and nearby linear entity counts.
    Returns {beam_id: {mark_found, nearby_line_count, sample_handle, sample_type}}.
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not dxf_path or not Path(dxf_path).exists():
        return out
    try:
        import ezdxf
    except Exception:
        return out

    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception:
        return out

    msp = doc.modelspace()
    marks = []
    lines = []
    # Marks often look like: %%UB14(450X900) or B14(450X900)
    beam_re = re.compile(r"(?:%%U)?(B\d+[A-Z]?)\b", re.I)

    for e in msp:
        try:
            dxftype = e.dxftype()
        except Exception:
            continue
        if dxftype in ("TEXT", "MTEXT"):
            try:
                text = e.plain_text() if dxftype == "MTEXT" else (e.dxf.text or "")
            except Exception:
                text = getattr(getattr(e, "dxf", None), "text", "") or ""
            raw = str(text).upper().replace(" ", "")
            m = beam_re.search(raw)
            if not m:
                m = beam_re.search(str(text).upper())
            if not m:
                continue
            bid = m.group(1).upper()
            try:
                if dxftype == "MTEXT":
                    x, y, *_ = e.dxf.insert
                else:
                    x, y, *_ = e.dxf.insert
            except Exception:
                continue
            marks.append((bid, float(x), float(y), str(getattr(e.dxf, "handle", "") or "")))
        elif dxftype in ("LINE", "LWPOLYLINE", "POLYLINE", "ARC", "SPLINE"):
            try:
                if dxftype == "LINE":
                    x = (float(e.dxf.start.x) + float(e.dxf.end.x)) / 2.0
                    y = (float(e.dxf.start.y) + float(e.dxf.end.y)) / 2.0
                elif dxftype == "LWPOLYLINE":
                    pts = list(e.get_points("xy"))
                    if not pts:
                        continue
                    x = sum(p[0] for p in pts) / len(pts)
                    y = sum(p[1] for p in pts) / len(pts)
                else:
                    loc = e.dxf.handle
                    x = y = None
                    if hasattr(e, "dxf") and hasattr(e.dxf, "center"):
                        x, y = float(e.dxf.center.x), float(e.dxf.center.y)
                    if x is None:
                        continue
                lines.append(
                    (
                        float(x),
                        float(y),
                        str(getattr(e.dxf, "handle", "") or ""),
                        dxftype,
                    )
                )
            except Exception:
                continue

    # radius ~ 15000 drawing units around mark
    radius = 15000.0
    for bid, x, y, h in marks:
        nearby = [
            (lx, ly, lh, lt)
            for lx, ly, lh, lt in lines
            if abs(lx - x) <= radius and abs(ly - y) <= radius
        ]
        prev = out.get(bid)
        rec = {
            "mark_found": True,
            "nearby_line_count": len(nearby),
            "sample_handle": (nearby[0][2] if nearby else h) or "UNKNOWN",
            "sample_type": nearby[0][3] if nearby else "TEXT",
            "mark_handle": h or "UNKNOWN",
        }
        if prev is None or rec["nearby_line_count"] > prev.get("nearby_line_count", 0):
            out[bid] = rec
    return out


def classify_dxf(
    beam_id: str,
    *,
    t16_line_count: int,
    graph_bar_handles: int,
    envelope_present: bool,
    dxf_index: Dict[str, Dict[str, Any]],
    text_primary: bool,
) -> Dict[str, Any]:
    if t16_line_count > 0 or graph_bar_handles > 0:
        return {
            "status": "DXF_GEOMETRY_FOUND",
            "handle": "FROM_T16_OR_GRAPH",
            "entity_type": "LINE",
            "source": "pipeline_index",
        }
    info = dxf_index.get(beam_id)
    if info and info.get("nearby_line_count", 0) > 0:
        return {
            "status": "DXF_GEOMETRY_FOUND",
            "handle": info.get("sample_handle") or "UNKNOWN",
            "entity_type": info.get("sample_type") or "LINE",
            "source": "dxf_probe",
        }
    if info and info.get("mark_found"):
        return {
            "status": "DXF_GEOMETRY_AMBIGUOUS",
            "handle": info.get("mark_handle") or "UNKNOWN",
            "entity_type": "TEXT",
            "source": "dxf_mark_only",
        }
    if envelope_present:
        return {
            "status": "DXF_GEOMETRY_AMBIGUOUS",
            "handle": "UNKNOWN",
            "entity_type": "UNKNOWN",
            "source": "geometry_envelope",
        }
    if text_primary:
        return {
            "status": "DXF_GEOMETRY_AMBIGUOUS",
            "handle": "UNKNOWN",
            "entity_type": "UNKNOWN",
            "source": "text_primary_role",
        }
    return {
        "status": "DXF_GEOMETRY_NOT_FOUND",
        "handle": "UNKNOWN",
        "entity_type": "UNKNOWN",
        "source": "none",
    }
