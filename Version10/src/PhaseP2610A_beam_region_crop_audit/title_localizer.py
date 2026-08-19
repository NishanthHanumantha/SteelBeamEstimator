"""Independent beam-title localization on a reinforcement DXF. No R.1 association."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from PhaseT1_geometric_stirrup_evidence.geometry_envelope import _outline_bracket

_MARK_RE = re.compile(r"(B\d+[A-Z]?)\s*\(\s*(\d+)\s*[Xx×]\s*(\d+)", re.I)


def _entity_text_xy(entity: Any) -> Optional[Tuple[str, float, float]]:
    try:
        dxftype = entity.dxftype()
        if dxftype not in ("TEXT", "MTEXT"):
            return None
        text = entity.dxf.text if dxftype == "TEXT" else entity.plain_text()
        x, y = float(entity.dxf.insert.x), float(entity.dxf.insert.y)
        return str(text or ""), x, y
    except Exception:
        return None


def iter_text_inserts(msp: Any) -> List[Tuple[str, float, float]]:
    rows: List[Tuple[str, float, float]] = []
    for e in msp:
        hit = _entity_text_xy(e)
        if hit:
            rows.append(hit)
    try:
        inserts = msp.query("INSERT")
    except Exception:
        inserts = []
    for e in inserts:
        try:
            for ve in e.virtual_entities():
                hit = _entity_text_xy(ve)
                if hit:
                    rows.append(hit)
        except Exception:
            continue
    return rows


def parse_beam_title(raw: str) -> Optional[Dict[str, Any]]:
    clean = (raw or "").replace("%%U", "").replace("%%u", "")
    match = _MARK_RE.search(clean)
    if not match:
        return None
    beam_id = match.group(1).upper()
    try:
        width = float(match.group(2))
        depth = float(match.group(3))
    except (TypeError, ValueError):
        width, depth = None, None
    return {"beam_id": beam_id, "text": clean.strip(), "width_mm": width, "depth_mm": depth}


def collect_beam_titles(msp: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for text, x, y in iter_text_inserts(msp):
        parsed = parse_beam_title(text)
        if not parsed:
            continue
        rec = dict(parsed)
        rec["x"] = x
        rec["y"] = y
        out.append(rec)
    return out


def _score_mark(msp: Any, mark: Dict[str, Any]) -> float:
    """Prefer elevation titles that sit between a beam-outline bracket."""
    mx, my = float(mark["x"]), float(mark["y"])
    depth = float(mark.get("depth_mm") or 600.0)
    outline = _outline_bracket(msp, mx, my, 2500.0, depth)
    if not outline:
        return 0.0
    sep = abs(outline[1] - outline[0])
    return 100.0 + max(0.0, 40.0 - abs(sep - 3.0 * depth) / 50.0)


def choose_mark(msp: Any, titles: List[Dict[str, Any]], beam_id: str) -> Optional[Dict[str, Any]]:
    cands = [t for t in titles if str(t.get("beam_id") or "").upper() == beam_id.upper()]
    if not cands:
        return None
    scored = []
    for t in cands:
        rec = dict(t)
        rec["score"] = _score_mark(msp, rec)
        scored.append(rec)
    scored.sort(key=lambda t: float(t.get("score") or 0.0), reverse=True)
    chosen = scored[0]
    chosen["candidate_count"] = len(cands)
    return chosen


def best_marks_by_beam(msp: Any, titles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by: Dict[str, List[Dict[str, Any]]] = {}
    for t in titles:
        by.setdefault(str(t.get("beam_id")), []).append(t)
    out: Dict[str, Dict[str, Any]] = {}
    for bid, rows in by.items():
        mark = choose_mark(msp, rows, bid)
        if mark:
            out[bid] = mark
    return out


__all__ = [
    "best_marks_by_beam",
    "choose_mark",
    "collect_beam_titles",
    "parse_beam_title",
]
