"""Render independent context/detail PNGs via the existing M.1 region renderer."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from .config import CONTEXT_MAX_PX, DETAIL_MAX_PX, RENDER_DPI, RENDERER_VERSION

_V10 = Path(__file__).resolve().parents[2]
_RENDERER_MOD = None


def _load_dxf_renderer():
    global _RENDERER_MOD
    if _RENDERER_MOD is not None:
        return _RENDERER_MOD
    name = "p2610a_dxf_renderer"
    if name in sys.modules:
        _RENDERER_MOD = sys.modules[name]
        return _RENDERER_MOD
    path = _V10 / "src" / "PhaseM.1_engineering_vision_dataset" / "dxf_renderer.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    _RENDERER_MOD = mod
    return mod


def _extent_tuple(extent: Any) -> Tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = extent
    return (float(xmin), float(ymin), float(xmax), float(ymax))


def render_crop(
    *,
    dxf_path: Path,
    output_path: Path,
    extent: Any,
    crop_type: str,
) -> Dict[str, Any]:
    ext = _extent_tuple(extent)
    max_px = DETAIL_MAX_PX if crop_type == "detail" else CONTEXT_MAX_PX
    mod = _load_dxf_renderer()
    xf = mod.render_dxf_region_to_png(
        Path(dxf_path),
        Path(output_path),
        ext,
        max_dim_px=max_px,
        dpi=RENDER_DPI,
        render_text=True,
    )
    return {
        "path": str(output_path),
        "crop_type": crop_type,
        "dxf_bbox": list(ext),
        "image_dimensions": [int(xf.img_w), int(xf.img_h)],
        "scale_px_per_mm": (
            float(xf.img_w) / max(ext[2] - ext[0], 1e-6),
            float(xf.img_h) / max(ext[3] - ext[1], 1e-6),
        ),
        "renderer": "PhaseM.1_engineering_vision_dataset.dxf_renderer.render_dxf_region_to_png",
        "renderer_version": RENDERER_VERSION,
        "dxf_xlim": list(xf.dxf_xlim),
        "dxf_ylim": list(xf.dxf_ylim),
        "y_axis": "dxf_up_image_down",
    }


__all__ = ["render_crop"]
