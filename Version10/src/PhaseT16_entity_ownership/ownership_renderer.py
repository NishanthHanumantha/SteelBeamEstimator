"""
T1.6 Step 5 — Ownership-filtered DXF rendering.
MODEL_VERSION: 9.3.6

Renders ONLY entities whose handles are in the allowed HIGH-ownership set.
Does not render an entity merely because it intersects the crop rectangle.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

MODEL_VERSION = "9.3.6"


def render_owned_entities_to_png(
    dxf_path: Path,
    output_path: Path,
    extent: Tuple[float, float, float, float],
    allowed_handles: Iterable[str],
    *,
    max_dim_px: int = 1200,
    min_dim_px: int = 400,
    dpi: int = 150,
    render_text: bool = True,
) -> Dict[str, Any]:
    """
    Ownership-driven local-extent render.

    filter_func keeps an entity only when:
      1. its handle is in allowed_handles (HIGH ownership), AND
      2. if render_text is False, it is not a text entity.
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
            "matplotlib/ezdxf required for ownership rendering"
        ) from exc

    allowed: Set[str] = {str(h).upper() for h in allowed_handles}
    text_types = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}

    xmin, ymin, xmax, ymax = extent
    w = max(xmax - xmin, 1e-6)
    h = max(ymax - ymin, 1e-6)
    aspect = w / h
    if aspect >= 1.0:
        target_img_w = max_dim_px
        target_img_h = max(min_dim_px, round(max_dim_px / aspect))
    else:
        target_img_h = max_dim_px
        target_img_w = max(min_dim_px, round(max_dim_px * aspect))

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    drawn = 0
    skipped = 0

    def _entity_ok(entity) -> bool:
        nonlocal drawn, skipped
        try:
            handle = str(entity.dxf.handle).upper()
        except Exception:
            skipped += 1
            return False
        if handle not in allowed:
            skipped += 1
            return False
        if not render_text and entity.dxftype() in text_types:
            skipped += 1
            return False
        drawn += 1
        return True

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig_w_in = target_img_w / dpi
    fig_h_in = target_img_h / dpi
    fig = plt.figure(figsize=(fig_w_in, fig_h_in))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    frontend = Frontend(ctx, backend)
    frontend.draw_layout(msp, finalize=False, filter_func=_entity_ok)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    fig.savefig(str(output_path), dpi=dpi, facecolor="white")
    plt.close(fig)

    try:
        from PIL import Image as _PILImage

        with _PILImage.open(output_path) as im:
            img_w, img_h = im.size
    except Exception:
        img_w = int(math.ceil(fig_w_in * dpi))
        img_h = int(math.ceil(fig_h_in * dpi))

    return {
        "img_w": img_w,
        "img_h": img_h,
        "dxf_xlim": (xmin, xmax),
        "dxf_ylim": (ymin, ymax),
        "entities_drawn": drawn,
        "entities_skipped_by_filter": skipped,
        "allowed_handle_count": len(allowed),
        "render_text": render_text,
    }


def render_ownership_overlay(
    dxf_path: Path,
    output_path: Path,
    extent: Tuple[float, float, float, float],
    ownership_rows: list,
    inventory_by_handle: Dict[str, Dict[str, Any]],
    *,
    max_dim_px: int = 1200,
    dpi: int = 120,
) -> None:
    """Simple matplotlib overlay: HIGH=green, MEDIUM=orange, LOW=gray segments."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    xmin, ymin, xmax, ymax = extent
    w = max(xmax - xmin, 1e-6)
    h = max(ymax - ymin, 1e-6)
    aspect = w / h
    if aspect >= 1.0:
        tw, th = max_dim_px, max(400, round(max_dim_px / aspect))
    else:
        th, tw = max_dim_px, max(400, round(max_dim_px * aspect))

    from matplotlib.patches import Rectangle

    colors = {"HIGH": "#00AA00", "MEDIUM": "#E67E22", "LOW": "#888888", "NONE": "#CCCCCC"}
    fig = plt.figure(figsize=(tw / dpi, th / dpi))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.add_patch(
        Rectangle(
            (xmin, ymin),
            xmax - xmin,
            ymax - ymin,
            fill=False,
            edgecolor="blue",
            linewidth=0.8,
            linestyle="--",
        )
    )

    for row in ownership_rows:
        own = row.get("ownership") or "NONE"
        if own not in ("HIGH", "MEDIUM", "LOW"):
            continue
        ent = inventory_by_handle.get(str(row["handle"]).upper())
        if not ent:
            continue
        color = colors.get(own, "#888888")
        sp, ep = ent.get("start_point"), ent.get("end_point")
        if sp and ep:
            ax.plot([sp[0], ep[0]], [sp[1], ep[1]], color=color, linewidth=0.7)
        elif ent.get("centroid"):
            ax.plot(ent["centroid"][0], ent["centroid"][1], ".", color=color, markersize=2)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path), dpi=dpi, facecolor="white")
    plt.close(fig)
