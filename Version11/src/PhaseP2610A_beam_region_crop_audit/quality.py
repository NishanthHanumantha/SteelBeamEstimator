"""P2.6.10-A quality checks. OCR is NOT_EVALUABLE unless already present."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_REINF_RE = re.compile(r"(Y\d+|@\d+|C/C|STIRRUP|STIRUP|\d+L[- ]Y\d+)", re.I)


def _inside(xy: Tuple[float, float], bbox: Sequence[float], margin: float = 0.0) -> bool:
    x, y = xy
    xmin, ymin, xmax, ymax = bbox
    return (xmin - margin) <= x <= (xmax + margin) and (ymin - margin) <= y <= (ymax + margin)


def _edge_clip(xy: Tuple[float, float], bbox: Sequence[float], frac: float = 0.04) -> bool:
    x, y = xy
    xmin, ymin, xmax, ymax = bbox
    w = max(xmax - xmin, 1.0)
    h = max(ymax - ymin, 1.0)
    return (
        x - xmin < frac * w
        or xmax - x < frac * w
        or y - ymin < frac * h
        or ymax - y < frac * h
    )


def png_occupancy(path: Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists() or p.stat().st_size <= 0:
        return {"exists": False, "non_empty": False, "white_fraction": 1.0, "excessively_empty": True}
    try:
        from PIL import Image

        with Image.open(p) as im:
            gray = im.convert("L")
            hist = gray.histogram()
            total = sum(hist) or 1
            white = sum(hist[250:]) / total
            extrema = gray.getextrema()
            width, height = gray.size
        return {
            "exists": True,
            "non_empty": bool(extrema and extrema[0] < 250),
            "white_fraction": round(white, 4),
            "excessively_empty": white >= 0.95,
            "width": int(width),
            "height": int(height),
        }
    except Exception:
        return {
            "exists": True,
            "non_empty": p.stat().st_size > 1000,
            "white_fraction": None,
            "excessively_empty": False,
        }


def titles_in_extent(titles: Iterable[Dict[str, Any]], extent: Sequence[float]) -> List[str]:
    hits = []
    for t in titles or []:
        try:
            xy = (float(t["x"]), float(t["y"]))
        except (TypeError, ValueError, KeyError):
            continue
        if _inside(xy, extent):
            bid = str(t.get("beam_id") or "")
            if bid and bid not in hits:
                hits.append(bid)
    return hits


def nearby_reinforcement_text(msp: Any, mark: Dict[str, Any], extent: Sequence[float]) -> int:
    mx, my = float(mark["x"]), float(mark["y"])
    n = 0
    for e in msp:
        try:
            if e.dxftype() not in ("TEXT", "MTEXT"):
                continue
            text = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
            x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
        except Exception:
            continue
        if not _inside((x, y), extent):
            continue
        if abs(x - mx) > 4500.0 or abs(y - my) > 2500.0:
            continue
        if _REINF_RE.search(str(text or "")):
            n += 1
    return n


def readability_from_scale(scale_px_per_mm: Sequence[float], assumed_text_mm: float = 180.0) -> str:
    sx = float(scale_px_per_mm[0] or 0.0)
    title_px = sx * assumed_text_mm
    if title_px >= 36:
        return "GOOD"
    if title_px >= 18:
        return "PARTIAL"
    return "POOR"


def assess_crop(
    *,
    beam_id: str,
    crop_type: str,
    path: Path,
    extent: Sequence[float],
    mark: Dict[str, Any],
    geometry_included: bool,
    titles: List[Dict[str, Any]],
    scale_px_per_mm: Sequence[float],
    msp: Optional[Any] = None,
) -> Dict[str, Any]:
    occ = png_occupancy(path)
    title_xy = (float(mark["x"]), float(mark["y"]))
    title_in = _inside(title_xy, extent)
    clip = _edge_clip(title_xy, extent) if title_in else True
    other_titles = [b for b in titles_in_extent(titles, extent) if b.upper() != beam_id.upper()]
    reinf_n = nearby_reinforcement_text(msp, mark, extent) if msp is not None else 0
    read = readability_from_scale(scale_px_per_mm)
    bbox_ok = float(extent[2]) > float(extent[0]) and float(extent[3]) > float(extent[1])
    ready = "NOT_READY"
    if occ.get("exists") and occ.get("non_empty") and title_in and geometry_included and read != "POOR" and not occ.get("excessively_empty"):
        ready = "READY" if (not clip and reinf_n > 0) else "PARTIAL"
    elif occ.get("exists") and title_in:
        ready = "PARTIAL"
    return {
        "image_exists": bool(occ.get("exists")),
        "image_non_empty": bool(occ.get("non_empty")),
        "crop_bbox_valid": bbox_ok,
        "beam_title_included": title_in,
        "beam_geometry_included": bool(geometry_included),
        "context_included": crop_type == "context" or bool(other_titles),
        "clipping_detected": bool(clip),
        "excessively_empty": bool(occ.get("excessively_empty")),
        "white_fraction": occ.get("white_fraction"),
        "neighbor_titles_in_crop": other_titles,
        "reinforcement_text_near_mark": reinf_n,
        "readability_status": read,
        "ocr_validation": "NOT_EVALUABLE",
        "confidence": (
            "HIGH" if ready == "READY" else "MEDIUM" if ready == "PARTIAL" else "LOW"
        ),
        "vision_readiness": ready,
    }


__all__ = ["assess_crop", "nearby_reinforcement_text", "png_occupancy", "titles_in_extent"]
