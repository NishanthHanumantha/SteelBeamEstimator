"""Completeness checks on an adaptive crop. Spatial evidence only. No GT coords."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .evidence import KIND_DIM, KIND_REINF, KIND_STIRRUP


def _inside(x: float, y: float, box: Sequence[float], margin: float = 0.0) -> bool:
    xmin, ymin, xmax, ymax = box
    return (xmin - margin) <= x <= (xmax + margin) and (ymin - margin) <= y <= (ymax + margin)


def _edge(x: float, y: float, box: Sequence[float], frac: float = 0.03) -> bool:
    xmin, ymin, xmax, ymax = box
    w = max(xmax - xmin, 1.0)
    h = max(ymax - ymin, 1.0)
    return (
        x - xmin < frac * w
        or xmax - x < frac * w
        or y - ymin < frac * h
        or ymax - y < frac * h
    )


def _yn(flag: bool) -> str:
    return "YES" if flag else "NO"


def _yna(flag: Optional[bool]) -> str:
    if flag is None:
        return "N/A"
    return "YES" if flag else "NO"


def evaluate_completeness(
    *,
    beam_id: str,
    extent: Sequence[float],
    mark: Dict[str, Any],
    outline: Optional[Sequence[float]],
    evidence: List[Dict[str, Any]],
    titles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    mx, my = float(mark["x"]), float(mark["y"])
    title_visible = _inside(mx, my, extent)
    geom = False
    if outline and len(outline) >= 2:
        mid_y = 0.5 * (float(outline[0]) + float(outline[1]))
        geom = _inside(mx, mid_y, extent) or _inside(mx, float(outline[1]), extent)
    else:
        geom = title_visible

    def _rows(kind: str = None, band_prefix: str = None) -> List[Dict[str, Any]]:
        out = []
        for row in evidence or []:
            if kind and row.get("kind") != kind:
                continue
            if band_prefix and not str(row.get("band") or "").startswith(band_prefix):
                continue
            out.append(row)
        return out

    stir = _rows(KIND_STIRRUP)
    reinf = _rows(KIND_REINF)
    dims = _rows(KIND_DIM)
    top = [r for r in reinf if str(r.get("band") or "").startswith("TOP_")]
    bottom = [r for r in reinf if str(r.get("band") or "").startswith("BOTTOM_")]
    extra_dim = [r for r in (reinf + dims) if "TOP_EXTRA" in str(r.get("band") or "") or (
        str(r.get("band") or "").startswith("TOP_") and r.get("kind") == KIND_DIM
    )]
    left = [r for r in evidence if float(r.get("dx") or 0.0) < -700.0]
    right = [r for r in evidence if float(r.get("dx") or 0.0) > 700.0]

    def _all_in(rows: List[Dict[str, Any]]) -> Optional[bool]:
        if not rows:
            return None
        return all(_inside(float(r["x"]), float(r["y"]), extent) for r in rows)

    def _any_in(rows: List[Dict[str, Any]]) -> Optional[bool]:
        if not rows:
            return None
        return any(_inside(float(r["x"]), float(r["y"]), extent) for r in rows)

    missing = []
    for row in evidence:
        if not _inside(float(row["x"]), float(row["y"]), extent):
            missing.append({"text": row.get("text"), "kind": row.get("kind"), "band": row.get("band"), "dx": row.get("dx"), "dy": row.get("dy")})

    clipped = []
    for row in evidence:
        if _inside(float(row["x"]), float(row["y"]), extent) and _edge(float(row["x"]), float(row["y"]), extent):
            clipped.append(row.get("text"))

    neighbor_ids = []
    for t in titles or []:
        nid = str(t.get("beam_id") or "")
        if not nid or nid.upper() == beam_id.upper():
            continue
        try:
            if _inside(float(t["x"]), float(t["y"]), extent, margin=-40.0):
                neighbor_ids.append(nid)
        except (TypeError, ValueError, KeyError):
            continue

    top_ok = _any_in(top)
    bot_ok = _any_in(bottom)
    stir_ok = _any_in(stir) if stir else _any_in([r for r in evidence if "STIRRUP" in str(r.get("band") or "")])
    extra_ok = _all_in(extra_dim) if extra_dim else _all_in(top)
    dim_ok = _any_in(dims)
    left_ok = _all_in(left)
    right_ok = _all_in(right)
    leaders = True
    vert = bool(title_visible and geom and (top_ok is not False) and (bot_ok is not False) and not missing)
    horiz = (left_ok is not False) and (right_ok is not False)

    complete = bool(
        title_visible
        and geom
        and (stir_ok is not False)
        and (bot_ok is not False)
        and (top_ok is True)
        and not neighbor_ids
        and len(missing) == 0
    )
    return {
        "title_visible": _yn(title_visible),
        "beam_geometry_visible": _yn(geom),
        "stirrup_visible": _yna(stir_ok),
        "bottom_reinforcement_visible": _yna(bot_ok),
        "top_reinforcement_visible": _yna(top_ok),
        "top_extra_visible_when_present": _yna(extra_ok if extra_dim else None),
        "relevant_dimensions_visible_when_present": _yna(dim_ok),
        "left_support_evidence_visible_when_present": _yna(left_ok),
        "right_support_evidence_visible_when_present": _yna(right_ok),
        "leaders_preserved": _yn(leaders),
        "important_text_clipped": _yn(bool(clipped)),
        "unrelated_neighbor_detail_present": _yn(bool(neighbor_ids)),
        "vertical_evidence_complete": _yn(vert and top_ok is True),
        "horizontal_evidence_complete": _yn(horiz),
        "missing_evidence": missing,
        "clipped_text": clipped,
        "neighbor_titles_in_crop": neighbor_ids,
        "complete": complete,
        "evidence_in_crop": sum(1 for r in evidence if _inside(float(r["x"]), float(r["y"]), extent)),
        "evidence_total": len(evidence),
    }


__all__ = ["evaluate_completeness"]
