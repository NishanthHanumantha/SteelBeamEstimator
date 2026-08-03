"""
dxf_renderer.py — Render a DXF drawing to a lossless PNG using ezdxf.

Uses ezdxf's matplotlib backend for vector-quality rendering (no screenshots).
Preserves: beam lines, text, leaders, dimensions, callouts, symbols.

Returns a CoordTransform that maps DXF model-space coordinates to image pixels,
enabling precise beam cropping from the rendered image.

Track 1 (9.3.0): optional layer filter, text on/off, DPI override — additive;
default call remains full-drawing text-on render (M.1 training behaviour).

MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Set, Tuple

MODEL_VERSION = "9.3.2"

# ── Rendering configuration ───────────────────────────────────────────────────
_FIG_W_IN = 30.0    # figure width  (inches)
_FIG_H_IN = 22.0    # figure height (inches)
_DPI      = 200     # rendering resolution — yields 6000 × 4400 px

_TEXT_TYPES = frozenset({
    "TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "MULTILEADER", "LEADER",
})


@dataclass
class CoordTransform:
    """
    Linear affine transform between DXF model-space and image pixel coordinates.

    DXF uses: X increases right, Y increases up.
    Image uses: X increases right, Y increases down (PIL convention).
    """
    dxf_xlim: Tuple[float, float]   # (x_min, x_max) of rendered DXF content
    dxf_ylim: Tuple[float, float]   # (y_min, y_max) of rendered DXF content
    img_w:    int                   # image width  (pixels)
    img_h:    int                   # image height (pixels)

    def dxf_to_pixel(self, dxf_x: float, dxf_y: float) -> Tuple[float, float]:
        """Convert DXF model-space coordinates to image pixel coordinates (float)."""
        x_range = self.dxf_xlim[1] - self.dxf_xlim[0]
        y_range = self.dxf_ylim[1] - self.dxf_ylim[0]
        if x_range == 0 or y_range == 0:
            return 0.0, 0.0
        px = (dxf_x - self.dxf_xlim[0]) / x_range * self.img_w
        py = self.img_h - (dxf_y - self.dxf_ylim[0]) / y_range * self.img_h
        return px, py

    def pixel_to_dxf(self, px: float, py: float) -> Tuple[float, float]:
        """Convert image pixel coordinates back to DXF model-space."""
        x_range = self.dxf_xlim[1] - self.dxf_xlim[0]
        y_range = self.dxf_ylim[1] - self.dxf_ylim[0]
        dxf_x = px / self.img_w * x_range + self.dxf_xlim[0]
        dxf_y = (1.0 - py / self.img_h) * y_range + self.dxf_ylim[0]
        return dxf_x, dxf_y

    @property
    def img_size(self) -> Tuple[int, int]:
        return self.img_w, self.img_h


def _normalize_layers(layers: Optional[Sequence[str]]) -> Optional[Set[str]]:
    if not layers:
        return None
    return {str(x).strip().upper() for x in layers if str(x).strip()}


def render_dxf_to_png(
    dxf_path: Path,
    output_path: Path,
    *,
    dpi: Optional[int] = None,
    fig_w_in: Optional[float] = None,
    fig_h_in: Optional[float] = None,
    include_layers: Optional[Sequence[str]] = None,
    exclude_layers: Optional[Sequence[str]] = None,
    render_text: bool = True,
) -> CoordTransform:
    """
    Render *dxf_path* to *output_path* (PNG) using ezdxf's matplotlib backend.

    Parameters
    ----------
    dxf_path       : path to the DXF file to render.
    output_path    : destination PNG file path (parent directory is created).
    dpi            : override default DPI (200).
    fig_w_in/h_in  : override figure size inches.
    include_layers : if set, only entities on these layers are drawn.
    exclude_layers : layers to skip (applied after include filter).
    render_text    : False → suppress TEXT/MTEXT/DIMENSION/LEADER etc. (geometry-only).

    Returns
    -------
    CoordTransform — use .dxf_to_pixel() / .pixel_to_dxf() for round-trip mapping.
    """
    try:
        import ezdxf
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for DXF rendering.\n"
            "Install with:  pip install matplotlib"
        ) from exc

    if not dxf_path.exists():
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    use_dpi = int(dpi or _DPI)
    use_w = float(fig_w_in or _FIG_W_IN)
    use_h = float(fig_h_in or _FIG_H_IN)

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    inc = _normalize_layers(include_layers)
    exc_layers = _normalize_layers(exclude_layers)

    def _entity_ok(entity) -> bool:
        dxftype = entity.dxftype()
        if not render_text and dxftype in _TEXT_TYPES:
            return False
        layer = str(entity.dxf.layer or "").upper()
        if inc is not None and layer not in inc:
            return False
        if exc_layers is not None and layer in exc_layers:
            return False
        return True

    fig = plt.figure(figsize=(use_w, use_h))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_aspect("equal")
    ax.set_axis_off()

    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    frontend = Frontend(ctx, backend)

    # Always use draw_layout + filter_func. The per-entity draw_entity loop
    # (pre-9.3.2) left geometry-only renders blank (no ink / collapsed axes),
    # which made the OpenCV fallback receive empty PNGs. filter_func is the
    # supported ezdxf path for layer/text suppression.
    frontend.draw_layout(msp, finalize=True, filter_func=_entity_ok)

    xlim: Tuple[float, float] = ax.get_xlim()
    ylim: Tuple[float, float] = ax.get_ylim()

    fig.savefig(str(output_path), dpi=use_dpi, facecolor="white")
    plt.close(fig)

    # Prefer actual PNG pixel size over figsize*dpi — matplotlib may write a
    # different raster size depending on backend/aspect; OpenCV crop + mm/px
    # scale must match the file on disk or pitch extraction is meaningless.
    try:
        from PIL import Image as _PILImage

        with _PILImage.open(output_path) as _im:
            img_w, img_h = _im.size
    except Exception:
        img_w = int(math.ceil(use_w * use_dpi))
        img_h = int(math.ceil(use_h * use_dpi))

    return CoordTransform(
        dxf_xlim=xlim,
        dxf_ylim=ylim,
        img_w=int(img_w),
        img_h=int(img_h),
    )
