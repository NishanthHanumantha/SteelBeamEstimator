"""
dxf_renderer.py — Render a DXF drawing to a lossless PNG using ezdxf.

Uses ezdxf's matplotlib backend for vector-quality rendering (no screenshots).
Preserves: beam lines, text, leaders, dimensions, callouts, symbols.

Returns a CoordTransform that maps DXF model-space coordinates to image pixels,
enabling precise beam cropping from the rendered image.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

MODEL_VERSION = "9.0.0"

# ── Rendering configuration ───────────────────────────────────────────────────
_FIG_W_IN = 30.0    # figure width  (inches)
_FIG_H_IN = 22.0    # figure height (inches)
_DPI      = 200     # rendering resolution — yields 6000 × 4400 px


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

    def dxf_to_pixel(self, dxf_x: float, dxf_y: float) -> Tuple[int, int]:
        """Convert DXF model-space coordinates to image pixel coordinates."""
        x_range = self.dxf_xlim[1] - self.dxf_xlim[0]
        y_range = self.dxf_ylim[1] - self.dxf_ylim[0]
        if x_range == 0 or y_range == 0:
            return 0, 0
        px = (dxf_x - self.dxf_xlim[0]) / x_range * self.img_w
        py = self.img_h - (dxf_y - self.dxf_ylim[0]) / y_range * self.img_h
        return int(px), int(py)

    def pixel_to_dxf(self, px: int, py: int) -> Tuple[float, float]:
        """Convert image pixel coordinates back to DXF model-space."""
        x_range = self.dxf_xlim[1] - self.dxf_xlim[0]
        y_range = self.dxf_ylim[1] - self.dxf_ylim[0]
        dxf_x = px / self.img_w * x_range + self.dxf_xlim[0]
        dxf_y = (1.0 - py / self.img_h) * y_range + self.dxf_ylim[0]
        return dxf_x, dxf_y

    @property
    def img_size(self) -> Tuple[int, int]:
        return self.img_w, self.img_h


def render_dxf_to_png(dxf_path: Path, output_path: Path) -> CoordTransform:
    """
    Render *dxf_path* to *output_path* (PNG) using ezdxf's matplotlib backend.

    The rendering is vector-quality:
      - No screenshot or rasterisation of the screen.
      - All DXF layers / entities are processed by ezdxf's frontend.
      - Background is white; linework is rendered at full DXF fidelity.

    Parameters
    ----------
    dxf_path    : path to the DXF file to render.
    output_path : destination PNG file path (parent directory is created).

    Returns
    -------
    CoordTransform — use .dxf_to_pixel() to convert any DXF coordinate
                     to the corresponding pixel in the saved image.

    Raises
    ------
    ImportError      — if matplotlib is not installed.
    FileNotFoundError— if dxf_path does not exist.
    """
    try:
        import ezdxf
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use("Agg")   # non-interactive backend (no GUI window)
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for DXF rendering.\n"
            "Install with:  pip install matplotlib"
        ) from exc

    if not dxf_path.exists():
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # Fill the entire figure with the axes (no whitespace margins)
    fig = plt.figure(figsize=(_FIG_W_IN, _FIG_H_IN))
    ax  = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_aspect("equal")
    ax.set_axis_off()

    ctx     = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(msp, finalize=True)

    # Capture DXF-space limits BEFORE saving (these are the data coordinates
    # visible in the axes, matching the rendered DXF content extents)
    xlim: Tuple[float, float] = ax.get_xlim()
    ylim: Tuple[float, float] = ax.get_ylim()

    fig.savefig(str(output_path), dpi=_DPI, facecolor="white")
    plt.close(fig)

    # Exact pixel dimensions of the saved figure
    img_w = int(math.ceil(_FIG_W_IN * _DPI))
    img_h = int(math.ceil(_FIG_H_IN * _DPI))

    return CoordTransform(
        dxf_xlim=xlim,
        dxf_ylim=ylim,
        img_w=img_w,
        img_h=img_h,
    )
