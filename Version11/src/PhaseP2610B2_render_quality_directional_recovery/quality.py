"""Deterministic PNG render-quality validator. No Vision. No beam-ID logic."""
from __future__ import annotations

import math
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import (
    BLACK_DARK_MIN,
    BORDER_BAND_FRAC,
    EMPTY_FOREGROUND_MAX,
    LOW_CONTEXT_COVERAGE_MAX,
    LOW_INFO_FOREGROUND_MAX,
    MEANINGFUL_BORDER_FRAC,
)
from .geometry import pixel_to_dxf

STATUS_VALID = "VALID"
STATUS_EMPTY = "EMPTY_RENDER"
STATUS_BLACK = "BLACK_RENDER"
STATUS_LOW_INFO = "LOW_INFORMATION_RENDER"
STATUS_CLIP = "BORDER_CLIPPING_SUSPECT"
STATUS_LOW_CTX = "LOW_CONTEXT_QUALITY"
STATUS_MISSING = "RENDER_MISSING"


def _is_background(r: int, g: int, b: int) -> bool:
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 45:
        return True
    if mn > 248:
        return True
    if mx < 85 and (mx - mn) < 14:
        return True
    if mn > 232 and (mx - mn) < 14:
        return True
    return False


def _load_stats(path: Path, sample: int = 3) -> Optional[Dict[str, Any]]:
    try:
        from PIL import Image
    except Exception:
        return None
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        gray = im.convert("L")
        w, h = rgb.size
        pix = rgb.load()
        hist = gray.histogram()
    total = 0
    fg = 0
    dark = 0
    white = 0
    col_fg = [0] * 8
    row_fg = [0] * 8
    col_n = [0] * 8
    row_n = [0] * 8
    edge = {"left": 0, "right": 0, "top": 0, "bottom": 0, "n_left": 0, "n_right": 0, "n_top": 0, "n_bottom": 0}
    min_x = w
    min_y = h
    max_x = 0
    max_y = 0
    bw = max(int(w * BORDER_BAND_FRAC), 2)
    bh = max(int(h * BORDER_BAND_FRAC), 2)
    for y in range(0, h, sample):
        for x in range(0, w, sample):
            r, g, b = pix[x, y]
            total += 1
            cx = min(7, x * 8 // max(w, 1))
            cy = min(7, y * 8 // max(h, 1))
            col_n[cx] += 1
            row_n[cy] += 1
            bg = _is_background(r, g, b)
            if max(r, g, b) < 45:
                dark += 1
            if min(r, g, b) > 248:
                white += 1
            if x < bw:
                edge["n_left"] += 1
            if x >= w - bw:
                edge["n_right"] += 1
            if y < bh:
                edge["n_top"] += 1
            if y >= h - bh:
                edge["n_bottom"] += 1
            if bg:
                continue
            fg += 1
            col_fg[cx] += 1
            row_fg[cy] += 1
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
            if x < bw:
                edge["left"] += 1
            if x >= w - bw:
                edge["right"] += 1
            if y < bh:
                edge["top"] += 1
            if y >= h - bh:
                edge["bottom"] += 1
    entropy = 0.0
    gtot = sum(hist) or 1
    for c in hist:
        if c:
            p = c / gtot
            entropy -= p * math.log2(p)
    def _frac(num: int, den: int) -> float:
        return float(num) / float(den) if den else 0.0

    col_occ = [_frac(col_fg[i], col_n[i]) for i in range(8)]
    row_occ = [_frac(row_fg[i], row_n[i]) for i in range(8)]
    coverage_x = 0.0
    coverage_y = 0.0
    if fg and max_x >= min_x:
        coverage_x = (max_x - min_x + 1) / float(w)
        coverage_y = (max_y - min_y + 1) / float(h)
    return {
        "width": w,
        "height": h,
        "foreground_ratio": _frac(fg, total),
        "dark_ratio": _frac(dark, total),
        "white_ratio": _frac(white, total),
        "entropy": round(entropy, 4),
        "column_occupancy": col_occ,
        "row_occupancy": row_occ,
        "content_bbox_px": [int(min_x), int(min_y), int(max_x), int(max_y)] if fg else None,
        "coverage_x": coverage_x,
        "coverage_y": coverage_y,
        "border_fg_frac": {
            "left": _frac(edge["left"], edge["n_left"]),
            "right": _frac(edge["right"], edge["n_right"]),
            "top": _frac(edge["top"], edge["n_top"]),
            "bottom": _frac(edge["bottom"], edge["n_bottom"]),
        },
        "component_count": 0,
    }


def _component_count(path: Path, sample: int = 4) -> int:
    try:
        from PIL import Image
    except Exception:
        return 0
    with Image.open(path) as im:
        rgb = im.convert("RGB").resize((64, 48))
    pix = rgb.load()
    w, h = rgb.size
    visited = [[False] * w for _ in range(h)]
    n = 0
    for y in range(h):
        for x in range(w):
            if visited[y][x]:
                continue
            r, g, b = pix[x, y]
            if _is_background(r, g, b):
                visited[y][x] = True
                continue
            n += 1
            q = deque([(x, y)])
            visited[y][x] = True
            while q:
                cx, cy = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or visited[ny][nx]:
                        continue
                    rr, gg, bb = pix[nx, ny]
                    if _is_background(rr, gg, bb):
                        visited[ny][nx] = True
                        continue
                    visited[ny][nx] = True
                    q.append((nx, ny))
    return n


def _empty_side_from_strips(col_occ: Sequence[float], row_occ: Sequence[float]) -> List[str]:
    sides: List[str] = []
    if sum(col_occ[:3]) < 0.015 and sum(col_occ[5:]) > 0.04:
        sides.append("left")
    if sum(col_occ[5:]) < 0.015 and sum(col_occ[:3]) > 0.04:
        sides.append("right")
    if sum(row_occ[:3]) < 0.015 and sum(row_occ[5:]) > 0.04:
        sides.append("top")
    if sum(row_occ[5:]) < 0.015 and sum(row_occ[:3]) > 0.04:
        sides.append("bottom")
    return sides


def validate_render(
    path: Optional[Path],
    *,
    extent: Optional[Sequence[float]] = None,
    crop_type: str = "context",
) -> Dict[str, Any]:
    flags: List[str] = []
    if path is None or not Path(path).exists() or Path(path).stat().st_size < 200:
        return {
            "primary_status": STATUS_MISSING,
            "flags": ["FILE_MISSING"],
            "render_status": "MISSING",
            "quality_status": STATUS_MISSING,
            "recovery_required": True,
            "foreground_ratio": 0.0,
            "information_density": 0.0,
            "entropy": 0.0,
            "component_count": 0,
            "meaningful_border_contact": {"left": False, "right": False, "top": False, "bottom": False},
            "clipping_suspected": False,
            "clipping_axes": [],
            "empty_sides": ["left", "right", "top", "bottom"],
            "file_generated": False,
            "visually_usable": False,
        }
    stats = _load_stats(Path(path))
    if stats is None:
        return {
            "primary_status": STATUS_MISSING,
            "flags": ["ANALYZER_UNAVAILABLE"],
            "render_status": "UNKNOWN",
            "quality_status": STATUS_MISSING,
            "recovery_required": True,
            "file_generated": True,
            "visually_usable": False,
        }
    fg = stats["foreground_ratio"]
    dark = stats["dark_ratio"]
    border = stats["border_fg_frac"]
    contact = {k: bool(border[k] >= MEANINGFUL_BORDER_FRAC) for k in ("left", "right", "top", "bottom")}
    empty_sides = _empty_side_from_strips(stats["column_occupancy"], stats["row_occupancy"])
    clipping_axes: List[str] = []
    if contact["left"] or contact["right"]:
        clipping_axes.append("X")
    if contact["top"] or contact["bottom"]:
        clipping_axes.append("Y")

    if fg <= EMPTY_FOREGROUND_MAX and dark >= BLACK_DARK_MIN:
        primary = STATUS_BLACK
        flags.append("BLACK_RENDER")
    elif fg <= EMPTY_FOREGROUND_MAX:
        primary = STATUS_EMPTY
        flags.append("EMPTY_RENDER")
    elif dark >= BLACK_DARK_MIN and fg < 0.05:
        primary = STATUS_BLACK
        flags.append("BLACK_RENDER")
    elif fg < LOW_INFO_FOREGROUND_MAX or (stats["coverage_x"] < 0.28 and fg < 0.08):
        primary = STATUS_LOW_INFO
        flags.append("LOW_INFORMATION_RENDER")
    elif any(contact.values()):
        primary = STATUS_CLIP
        flags.append("BORDER_CLIPPING_SUSPECT")
        for side, hit in contact.items():
            if hit:
                flags.append(f"{side.upper()}_BORDER_CONTACT")
    else:
        primary = STATUS_VALID

    cov = max(stats["coverage_x"], stats["coverage_y"])
    if primary == STATUS_VALID and cov < LOW_CONTEXT_COVERAGE_MAX and crop_type == "context":
        primary = STATUS_LOW_CTX
        flags.append("LOW_CONTEXT_QUALITY")
    elif primary == STATUS_CLIP and crop_type == "context" and stats["coverage_x"] >= 0.85:
        flags.append("LOW_LONGITUDINAL_COVERAGE")

    if empty_sides:
        flags.append("EMPTY_REGION_PRESENT")
        for s in empty_sides:
            flags.append(f"EMPTY_{s.upper()}")
    if contact.get("left") and contact.get("right"):
        flags.append("HORIZONTAL_TRUNCATION_SUSPECT")
    if contact.get("top") and contact.get("bottom"):
        flags.append("VERTICAL_TRUNCATION_SUSPECT")

    recovery = primary in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING) or bool(empty_sides)
    usable = primary in (STATUS_VALID, STATUS_LOW_CTX) or (
        primary == STATUS_CLIP and fg >= LOW_INFO_FOREGROUND_MAX and dark < BLACK_DARK_MIN
    )
    # Clipping still requires recovery; usable here means "not blank".
    visually_nonblank = primary not in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING)
    content_bbox_dxf = None
    if stats.get("content_bbox_px") and extent is not None:
        x0, y0, x1, y1 = stats["content_bbox_px"]
        dx0, dy1 = pixel_to_dxf(x0, y0, extent, stats["width"], stats["height"])
        dx1, dy0 = pixel_to_dxf(x1, y1, extent, stats["width"], stats["height"])
        content_bbox_dxf = [min(dx0, dx1), min(dy0, dy1), max(dx0, dx1), max(dy0, dy1)]

    return {
        "primary_status": primary,
        "flags": flags,
        "render_status": "FILE_GENERATED",
        "quality_status": primary,
        "foreground_ratio": round(fg, 5),
        "information_density": round(fg * (stats["entropy"] / 8.0), 5),
        "entropy": stats["entropy"],
        "component_count": stats["component_count"],
        "dark_ratio": round(dark, 5),
        "white_ratio": round(stats["white_ratio"], 5),
        "coverage_x": round(stats["coverage_x"], 4),
        "coverage_y": round(stats["coverage_y"], 4),
        "column_occupancy": [round(v, 4) for v in stats["column_occupancy"]],
        "row_occupancy": [round(v, 4) for v in stats["row_occupancy"]],
        "meaningful_border_contact": contact,
        "clipping_suspected": primary == STATUS_CLIP or "BORDER_CLIPPING_SUSPECT" in flags,
        "clipping_axes": clipping_axes,
        "empty_sides": empty_sides,
        "content_bbox_px": stats.get("content_bbox_px"),
        "content_bbox_dxf": content_bbox_dxf,
        "recovery_required": recovery,
        "file_generated": True,
        "visually_usable": bool(visually_nonblank),
        "target_visible": bool(visually_nonblank and fg >= EMPTY_FOREGROUND_MAX * 3),
        "image_dimensions": [stats["width"], stats["height"]],
    }


__all__ = ["validate_render"]
