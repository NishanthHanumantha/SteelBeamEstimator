"""
Deterministic OWN TOP_BAR render validation (pixel support check).
MODEL_VERSION: 10.6.3

Maps OWN DXF geometry → crop pixels and verifies non-white stroke presence.
Does NOT infer reinforcement semantics via CV.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import OWN_TOP_BAR_ENGINEERING_COLOR
from .evidence_window import as_bbox
from .renderer import _owned_polyline_points

MODEL_VERSION = "10.6.3"


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) != 6:
        return (192, 0, 128)
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _to_px(
    x: float,
    y: float,
    *,
    extent: Tuple[float, float, float, float],
    img_w: int,
    img_h: int,
) -> Tuple[int, int]:
    xmin, ymin, xmax, ymax = extent
    xspan = max(xmax - xmin, 1e-6)
    yspan = max(ymax - ymin, 1e-6)
    px = int(round((x - xmin) / xspan * img_w))
    py = int(round(img_h - (y - ymin) / yspan * img_h))
    return px, py


def validate_owned_geometry_rendered(
    *,
    engineering_png: Path,
    evidence: Dict[str, Any],
    paint_meta: Optional[Sequence[Dict[str, Any]]] = None,
    dark_threshold: int = 250,
    match_tol: int = 55,
) -> Dict[str, Any]:
    """
    For each OWN TOP_BAR, sample pixels along the mapped segment.
    PASS if enough samples are non-white / near the engineering stroke color.
    """
    from PIL import Image
    import numpy as np

    path = Path(engineering_png) if engineering_png else None
    window = as_bbox(((evidence.get("evidence_window") or {}).get("bbox") or []))
    owned = [
        o
        for o in (evidence.get("owned_geometry") or [])
        if o.get("evidence_type") == "OWN_TOP_BAR" or str(o.get("semantic_role") or "").upper() == "TOP_BAR"
    ]
    painted_ids = {
        str(p.get("ownership_id"))
        for p in (paint_meta or [])
        if p.get("ownership_id")
    }

    if not path or not path.exists() or not window:
        return {
            "rendered": False,
            "distinguishable": False,
            "reason": "missing_png_or_window",
            "items": [],
            "paint_count": len(paint_meta or []),
        }

    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)
    img_h, img_w = arr.shape[0], arr.shape[1]
    target_rgb = _hex_to_rgb(OWN_TOP_BAR_ENGINEERING_COLOR)
    items: List[Dict[str, Any]] = []

    for og in owned:
        pts = _owned_polyline_points(og)
        oid = og.get("ownership_id")
        if not pts or len(pts) < 2:
            items.append(
                {
                    "ownership_id": oid,
                    "rendered": False,
                    "distinguishable": False,
                    "reason": "no_points",
                }
            )
            continue
        samples = []
        hit_nonwhite = 0
        hit_color = 0
        for t in (0.15, 0.3, 0.45, 0.55, 0.7, 0.85):
            x = pts[0][0] + t * (pts[-1][0] - pts[0][0])
            y = pts[0][1] + t * (pts[-1][1] - pts[0][1])
            px, py = _to_px(x, y, extent=window, img_w=img_w, img_h=img_h)
            if not (0 <= px < img_w and 0 <= py < img_h):
                continue
            # local 3x3 mean
            y0, y1 = max(0, py - 1), min(img_h, py + 2)
            x0, x1 = max(0, px - 1), min(img_w, px + 2)
            patch = arr[y0:y1, x0:x1].astype(float)
            mean = patch.mean(axis=(0, 1))
            samples.append({"px": px, "py": py, "rgb": [float(mean[0]), float(mean[1]), float(mean[2])]})
            if mean.mean() < dark_threshold:
                hit_nonwhite += 1
            if all(abs(float(mean[i]) - target_rgb[i]) <= match_tol for i in range(3)):
                hit_color += 1

        rendered = hit_nonwhite >= 3 or hit_color >= 2 or (oid in painted_ids and hit_nonwhite >= 2)
        distinguishable = hit_color >= 2 or (hit_nonwhite >= 4 and oid in painted_ids)
        items.append(
            {
                "ownership_id": oid,
                "source_handle": og.get("source_handle"),
                "rendered": rendered,
                "distinguishable": distinguishable,
                "hit_nonwhite": hit_nonwhite,
                "hit_color": hit_color,
                "sample_count": len(samples),
                "samples": samples[:4],
                "painted_in_meta": oid in painted_ids,
            }
        )

    all_r = bool(items) and all(i.get("rendered") for i in items)
    all_d = bool(items) and all(i.get("distinguishable") for i in items)
    return {
        "model_version": MODEL_VERSION,
        "rendered": all_r,
        "distinguishable": all_d,
        "paint_count": len(paint_meta or []),
        "owned_top_bar_count": len(owned),
        "items": items,
        "target_color": OWN_TOP_BAR_ENGINEERING_COLOR,
    }
