"""
Generate Expected-vs-Manual crop overlays (additive diagnostic only).
MODEL_VERSION: 10.0.2

Colours:
  Expected crop  - Green
  Existing crop  - Red
  Shared region  - Yellow
  Missing region - Blue (expected minus actual)
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .geometry_utils import BBox, as_bbox, bbox_size, expand_bbox, intersection

MODEL_VERSION = "10.0.2"


def _load_renderer(engine_root: Path):
    path = (
        Path(engine_root)
        / "src"
        / "PhaseM.1_engineering_vision_dataset"
        / "dxf_renderer.py"
    )
    name = "dxf_renderer_qa32"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _rect_pixels(xform, bbox: BBox) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    # corners: bottom-left and top-right in DXF
    px0, py_top = xform.dxf_to_pixel(x0, y1)  # top in image (smaller py)
    px1, py_bot = xform.dxf_to_pixel(x1, y0)
    left = int(min(px0, px1))
    right = int(max(px0, px1))
    top = int(min(py_top, py_bot))
    bottom = int(max(py_top, py_bot))
    return left, top, right, bottom


def generate_overlay(
    *,
    engine_root: Path,
    dxf_path: Path,
    expected: BBox,
    actual: BBox,
    dest_dir: Path,
    beam_id: str,
) -> Dict[str, Any]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    info: Dict[str, Any] = {
        "beam_id": beam_id,
        "overlay_path": None,
        "heatmap_path": None,
        "base_path": None,
        "error": None,
    }
    exp = as_bbox(expected)
    act = as_bbox(actual)
    if not exp or not act or not dxf_path or not Path(dxf_path).exists():
        info["error"] = "missing_inputs"
        return info

    union = (
        min(exp[0], act[0]),
        min(exp[1], act[1]),
        max(exp[2], act[2]),
        max(exp[3], act[3]),
    )
    view = expand_bbox(union, pad_frac=0.08)

    try:
        from PIL import Image, ImageDraw

        mod = _load_renderer(engine_root)
        base_path = dest_dir / f"{beam_id}_base.png"
        overlay_path = dest_dir / f"{beam_id}_expected_vs_manual.png"
        heatmap_path = dest_dir / f"{beam_id}_difference_heatmap.png"

        xform = mod.render_dxf_region_to_png(
            dxf_path, base_path, view, render_text=True, max_dim_px=1400
        )
        base = Image.open(base_path).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")

        el, et, er, eb = _rect_pixels(xform, exp)
        al, at, ar, ab = _rect_pixels(xform, act)

        # Expected green outline + light fill
        draw.rectangle([el, et, er, eb], outline=(0, 200, 0, 255), width=3)
        draw.rectangle([el, et, er, eb], fill=(0, 200, 0, 40))
        # Actual red
        draw.rectangle([al, at, ar, ab], outline=(220, 0, 0, 255), width=3)
        draw.rectangle([al, at, ar, ab], fill=(220, 0, 0, 40))

        # Shared yellow
        inter = intersection(exp, act)
        if inter:
            il, it, ir, ib = _rect_pixels(xform, inter)
            draw.rectangle(
                [il, it, ir, ib],
                fill=(255, 220, 0, 70),
                outline=(255, 180, 0, 255),
                width=2,
            )

        # Missing (expected - actual) via mask — blue
        mask = Image.new("L", base.size, 0)
        md_mask = ImageDraw.Draw(mask)
        md_mask.rectangle([el, et, er, eb], fill=180)
        md_mask.rectangle([al, at, ar, ab], fill=0)
        blue = Image.new("RGBA", base.size, (0, 90, 255, 80))
        composed = Image.alpha_composite(base, overlay)
        composed = Image.composite(blue, composed, mask)

        # Legend strip
        ld = ImageDraw.Draw(composed)
        legend = [
            ((0, 200, 0, 255), "Expected (green)"),
            ((220, 0, 0, 255), "Manual (red)"),
            ((255, 180, 0, 255), "Shared (yellow)"),
            ((0, 90, 255, 255), "Missing (blue)"),
        ]
        y = 8
        for color, label in legend:
            ld.rectangle([8, y, 28, y + 14], fill=color)
            ld.text((34, y), label, fill=(0, 0, 0, 255))
            y += 18

        composed.convert("RGB").save(overlay_path)

        # Heatmap: simple channel map of region membership
        heat = Image.new("RGB", base.size, (20, 20, 20))
        hd = ImageDraw.Draw(heat)
        # blue missing
        hd.rectangle([el, et, er, eb], fill=(0, 60, 180))
        # red actual-only (draw actual then yellow shared)
        hd.rectangle([al, at, ar, ab], fill=(180, 30, 30))
        if inter:
            il, it, ir, ib = _rect_pixels(xform, inter)
            hd.rectangle([il, it, ir, ib], fill=(220, 200, 40))
        # outlines
        hd.rectangle([el, et, er, eb], outline=(0, 255, 0), width=2)
        hd.rectangle([al, at, ar, ab], outline=(255, 0, 0), width=2)
        heat.save(heatmap_path)

        info["base_path"] = str(base_path)
        info["overlay_path"] = str(overlay_path)
        info["heatmap_path"] = str(heatmap_path)
        info["view_extent"] = list(view)
        ew, eh = bbox_size(exp)
        aw, ah = bbox_size(act)
        info["expected_size"] = [ew, eh]
        info["actual_size"] = [aw, ah]
    except Exception as exc:
        info["error"] = str(exc)
    return info
