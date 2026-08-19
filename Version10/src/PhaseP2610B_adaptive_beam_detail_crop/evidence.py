"""Spatial reinforcement-evidence collection. No R.1 association. No GT."""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP2610A_beam_region_crop_audit.title_localizer import iter_text_inserts

from .config import NEXT_ROW_MIN_DY_MM, ROW_TITLE_GAP_MM, SAME_ROW_Y_MM, TITLE_BELOW_PAD_MM

_BAR_RE = re.compile(r"\d+\s*[-]?\s*Y\d+", re.I)
_STIR_RE = re.compile(r"\d+\s*L\s*[-]?\s*Y\d+|@\s*\d+|C\s*/\s*C", re.I)
_DIM_RE = re.compile(r"^\s*\d{3,5}\s*$")

KIND_STIRRUP = "STIRRUP"
KIND_REINF = "REINF"
KIND_DIM = "DIM"
KIND_OTHER = "OTHER"


def classify_text(raw: str) -> str:
    clean = (raw or "").replace("%%U", "").replace("%%u", "").strip()
    if _STIR_RE.search(clean):
        return KIND_STIRRUP
    if _BAR_RE.search(clean):
        return KIND_REINF
    if _DIM_RE.match(clean):
        return KIND_DIM
    return KIND_OTHER


def nearest_title(x: float, y: float, titles: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best = None
    best_d = None
    for t in titles or []:
        try:
            d = math.hypot(x - float(t["x"]), y - float(t["y"]))
        except (TypeError, ValueError, KeyError):
            continue
        if best_d is None or d < best_d:
            best, best_d = t, d
    return best


def owned_by_mark(
    x: float,
    y: float,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    *,
    hysteresis_mm: float = 80.0,
    max_dist_mm: float = 5200.0,
) -> bool:
    """Same-row X competition only. Next-row titles must not steal this beam's top band."""
    mx, my = float(mark["x"]), float(mark["y"])
    d_own = math.hypot(x - mx, y - my)
    if d_own > max_dist_mm:
        return False
    d_own_x = abs(x - mx)
    for t in titles or []:
        try:
            tx, ty = float(t["x"]), float(t["y"])
        except (TypeError, ValueError, KeyError):
            continue
        if abs(tx - mx) < 1.0 and abs(ty - my) < 1.0:
            continue
        if abs(ty - my) > SAME_ROW_Y_MM:
            continue
        if abs(x - tx) + hysteresis_mm < d_own_x:
            return False
    return True


def next_row_y_cap(mark: Dict[str, Any], titles: Sequence[Dict[str, Any]]) -> float:
    mx, my = float(mark["x"]), float(mark["y"])
    depth = float(mark.get("depth_mm") or 600.0)
    min_stack = max(0.9 * depth, NEXT_ROW_MIN_DY_MM)
    above = []
    for t in titles or []:
        try:
            tx, ty = float(t["x"]), float(t["y"])
        except (TypeError, ValueError, KeyError):
            continue
        if ty < my + min_stack:
            continue
        if abs(tx - mx) > 4500.0:
            continue
        above.append(ty)
    if not above:
        return my + max(4.8 * depth, min_stack + 400.0)
    return min(above) - ROW_TITLE_GAP_MM


def prev_row_y_floor(mark: Dict[str, Any], titles: Sequence[Dict[str, Any]]) -> float:
    mx, my = float(mark["x"]), float(mark["y"])
    below = []
    for t in titles or []:
        try:
            tx, ty = float(t["x"]), float(t["y"])
        except (TypeError, ValueError, KeyError):
            continue
        if ty > my - 500.0:
            continue
        if abs(tx - mx) > 4500.0:
            continue
        below.append(ty)
    if not below:
        return my - TITLE_BELOW_PAD_MM
    return max(max(below) + 280.0, my - TITLE_BELOW_PAD_MM)


def x_barriers(mark: Dict[str, Any], titles: Sequence[Dict[str, Any]]) -> Tuple[float, float]:
    mx, my = float(mark["x"]), float(mark["y"])
    left = mx - 4500.0
    right = mx + 4500.0
    for t in titles or []:
        try:
            tx, ty = float(t["x"]), float(t["y"])
        except (TypeError, ValueError, KeyError):
            continue
        if abs(ty - my) > SAME_ROW_Y_MM:
            continue
        if abs(tx - mx) < 400.0:
            continue
        if tx < mx:
            left = max(left, tx + 250.0)
        else:
            right = min(right, tx - 250.0)
    return left, right


def collect_text_evidence(
    msp: Any,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    *,
    y_cap: float,
    x_left: float,
    x_right: float,
) -> List[Dict[str, Any]]:
    mx, my = float(mark["x"]), float(mark["y"])
    out: List[Dict[str, Any]] = []
    for text, x, y in iter_text_inserts(msp):
        kind = classify_text(text)
        if kind == KIND_OTHER:
            continue
        if y < my - (TITLE_BELOW_PAD_MM + 80.0) or y > y_cap:
            continue
        if x < x_left - 200.0 or x > x_right + 200.0:
            continue
        if not owned_by_mark(x, y, mark, titles):
            continue
        out.append(
            {
                "kind": kind,
                "text": (text or "").replace("%%U", "").strip()[:80],
                "x": float(x),
                "y": float(y),
                "dx": float(x) - mx,
                "dy": float(y) - my,
            }
        )
    return out


def collect_dimension_points(
    msp: Any,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    *,
    y_cap: float,
    x_left: float,
    x_right: float,
) -> List[Dict[str, Any]]:
    mx, my = float(mark["x"]), float(mark["y"])
    out: List[Dict[str, Any]] = []
    try:
        dims = msp.query("DIMENSION")
    except Exception:
        return out
    for e in dims:
        x = y = None
        try:
            mid = e.dxf.text_midpoint
            x, y = float(mid.x), float(mid.y)
        except Exception:
            try:
                ins = e.dxf.insert
                x, y = float(ins.x), float(ins.y)
            except Exception:
                continue
        if y is None or y < my - (TITLE_BELOW_PAD_MM + 80.0) or y > y_cap:
            continue
        if x < x_left - 400.0 or x > x_right + 400.0:
            continue
        if not owned_by_mark(x, y, mark, titles):
            continue
        raw = ""
        try:
            raw = str(e.dxf.text or "").replace("%%U", "").strip()
        except Exception:
            raw = ""
        kind = classify_text(raw) if raw else KIND_DIM
        if kind == KIND_OTHER:
            kind = KIND_DIM
        out.append(
            {
                "kind": kind if kind != KIND_OTHER else KIND_DIM,
                "text": (raw or "DIMENSION")[:80],
                "x": x,
                "y": y,
                "dx": x - mx,
                "dy": y - my,
            }
        )
    return out


def band_for_point(
    y: float,
    mark: Dict[str, Any],
    outline: Optional[Tuple[float, float]],
    kind: str,
) -> str:
    my = float(mark["y"])
    depth = float(mark.get("depth_mm") or 600.0)
    if kind == KIND_STIRRUP:
        return "STIRRUP_BAND"
    top_cut = my + max(1.15 * depth, 1350.0)
    if y >= top_cut:
        return "TOP_REINFORCEMENT_BAND" if kind != KIND_DIM else "TOP_EXTRA_DIMENSION_BAND"
    if kind == KIND_DIM and y < my + 250.0:
        return "TITLE_BAND"
    if outline:
        lo, hi = outline
        if y >= float(hi) - 40.0:
            return "TOP_REINFORCEMENT_BAND" if kind != KIND_DIM else "TOP_EXTRA_DIMENSION_BAND"
    return "BOTTOM_REINFORCEMENT_BAND"


__all__ = [
    "KIND_DIM",
    "KIND_REINF",
    "KIND_STIRRUP",
    "band_for_point",
    "classify_text",
    "collect_dimension_points",
    "collect_text_evidence",
    "nearest_title",
    "next_row_y_cap",
    "owned_by_mark",
    "prev_row_y_floor",
    "x_barriers",
]
