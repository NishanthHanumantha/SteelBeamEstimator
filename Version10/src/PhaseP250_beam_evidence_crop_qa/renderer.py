"""
Render engineering crop + evidence overlay for a beam evidence pack.
Reuses M.1 render algorithm (read-only DXF) with a process-local DXF cache
so Fourth Set multi-beam runs do not re-parse the sheet every time.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config import RENDER_DPI, RENDER_MAX_DIM_PX, BBox

MODEL_VERSION = "10.6.0"

_TEXT_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}
_DOC_CACHE: Dict[str, Any] = {}
_RENDERER_MOD = None


def _load_dxf_renderer(engine_root: Path):
    global _RENDERER_MOD
    if _RENDERER_MOD is not None:
        return _RENDERER_MOD
    name = "p250_dxf_renderer"
    if name in sys.modules:
        _RENDERER_MOD = sys.modules[name]
        return _RENDERER_MOD
    path = (
        Path(engine_root)
        / "src"
        / "PhaseM.1_engineering_vision_dataset"
        / "dxf_renderer.py"
    )
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # Required for @dataclass on Python 3.14 when loading via importlib
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    _RENDERER_MOD = mod
    return mod


def _get_doc(dxf_path: Path):
    key = str(Path(dxf_path).resolve())
    if key not in _DOC_CACHE:
        import ezdxf

        _DOC_CACHE[key] = ezdxf.readfile(key)
    return _DOC_CACHE[key]


def render_engineering_crop(
    *,
    engine_root: Path,
    dxf_path: Path,
    extent: BBox,
    out_path: Path,
    max_dim_px: int = RENDER_MAX_DIM_PX,
    dpi: int = RENDER_DPI,
) -> Dict[str, Any]:
    """Clean DXF render with text/leaders — no diagnostic labels."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Ensure CoordTransform class is available from M.1 module
        mod = _load_dxf_renderer(engine_root)
        xf = _render_region_cached(
            mod,
            Path(dxf_path),
            out_path,
            extent,
            render_text=True,
            max_dim_px=max_dim_px,
            dpi=dpi,
        )
        return {
            "success": True,
            "path": str(out_path),
            "extent": list(extent),
            "img_w": getattr(xf, "img_w", None),
            "img_h": getattr(xf, "img_h", None),
            "dxf_xlim": list(getattr(xf, "dxf_xlim", ())),
            "dxf_ylim": list(getattr(xf, "dxf_ylim", ())),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "path": str(out_path),
            "error": str(exc),
            "extent": list(extent),
        }


def _render_region_cached(
    mod: Any,
    dxf_path: Path,
    output_path: Path,
    extent: Tuple[float, float, float, float],
    *,
    max_dim_px: int,
    min_dim_px: int = 400,
    dpi: int,
    render_text: bool,
):
    """
    Same behaviour as M.1 render_dxf_region_to_png, but reuses a cached Document.
    Does not mutate the DXF file.
    """
    from ezdxf import bbox as ezdxf_bbox
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not dxf_path.exists():
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    doc = _get_doc(dxf_path)
    msp = doc.modelspace()

    bbox_cache = ezdxf_bbox.Cache()
    margin = max((xmax - xmin), (ymax - ymin)) * 0.02

    def _entity_in_view(entity) -> bool:
        try:
            ext = ezdxf_bbox.extents([entity], cache=bbox_cache, fast=True)
        except Exception:
            return True
        if not ext.has_data:
            return True
        exmin, eymin = ext.extmin.x, ext.extmin.y
        exmax, eymax = ext.extmax.x, ext.extmax.y
        return not (
            exmax < xmin - margin
            or exmin > xmax + margin
            or eymax < ymin - margin
            or eymin > ymax + margin
        )

    def _entity_ok(entity) -> bool:
        dxftype = entity.dxftype()
        if not render_text and dxftype in _TEXT_TYPES:
            return False
        return _entity_in_view(entity)

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

        with _PILImage.open(output_path) as _im:
            img_w, img_h = _im.size
    except Exception:
        img_w = int(math.ceil(fig_w_in * dpi))
        img_h = int(math.ceil(fig_h_in * dpi))

    return mod.CoordTransform(
        dxf_xlim=(xmin, xmax),
        dxf_ylim=(ymin, ymax),
        img_w=int(img_w),
        img_h=int(img_h),
    )


def render_evidence_overlay(
    *,
    engineering_png: Path,
    evidence: Dict[str, Any],
    out_path: Path,
    extent: BBox,
) -> Dict[str, Any]:
    """
    Debug overlay on top of engineering crop.
    Labels: TARGET BEAM, ANN_*, LDR_*, R_*
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from PIL import Image

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    eng = Path(engineering_png)
    if not eng.exists():
        return {"success": False, "error": "missing_engineering_png", "path": str(out_path)}

    try:
        img = Image.open(eng)
        w, h = img.size
        xmin, ymin, xmax, ymax = extent
        xspan = max(xmax - xmin, 1e-6)
        yspan = max(ymax - ymin, 1e-6)

        def to_px(x: float, y: float) -> Tuple[float, float]:
            px = (x - xmin) / xspan * w
            py = h - (y - ymin) / yspan * h
            return px, py

        fig, ax = plt.subplots(figsize=(w / 100.0, h / 100.0), dpi=100)
        ax.imshow(img, extent=[0, w, h, 0])
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.set_axis_off()

        ax.add_patch(
            Rectangle((0, 0), w, h, fill=False, edgecolor="#FF6600", linewidth=2.0)
        )

        beam_id = evidence.get("beam_id") or "UNKNOWN"
        ax.text(
            8,
            18,
            f"TARGET BEAM: {beam_id}",
            color="#CC0000",
            fontsize=9,
            fontweight="bold",
            bbox=dict(facecolor="white", alpha=0.75, edgecolor="#CC0000", pad=2),
        )

        for i, b in enumerate(evidence.get("reinforcement") or []):
            g = b.get("geometry") or {}
            try:
                x0, y0 = float(g["start_x"]), float(g["y_position"])
                x1, y1 = float(g["end_x"]), float(g["y_position"])
            except Exception:
                continue
            p0, p1 = to_px(x0, y0), to_px(x1, y1)
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="#1F4E79", linewidth=1.8)
            rid = b.get("reinforcement_id") or f"R_{i}"
            short = rid.replace("BAR::SYN::", "R::").replace("BAR::", "R::")
            ax.text(p0[0], p0[1] - 6, short[-18:], color="#1F4E79", fontsize=6)

        for i, l in enumerate(evidence.get("leaders") or []):
            g = l.get("geometry") or {}
            try:
                tip = to_px(float(g["tip_x"]), float(g["tip_y"]))
                tail = to_px(float(g["tail_x"]), float(g["tail_y"]))
            except Exception:
                continue
            ax.plot([tip[0], tail[0]], [tip[1], tail[1]], color="#228B22", linewidth=1.4)
            lid = l.get("leader_id") or f"LEADER_{i}"
            ax.text(
                tail[0],
                tail[1] - 6,
                lid.replace("LDR::", "L::")[-14:],
                color="#228B22",
                fontsize=6,
            )

        for i, a in enumerate(evidence.get("annotations") or []):
            pos = a.get("position") or {}
            try:
                x, y = float(pos["x"]), float(pos["y"])
            except Exception:
                continue
            px, py = to_px(x, y)
            aid = a.get("annotation_id") or f"ANN_{i:03d}"
            txt = (a.get("raw_text") or "")[:24]
            ax.plot(px, py, "o", color="#000000", markersize=3)
            ax.text(
                px + 4,
                py - 4,
                f"{aid[-12:]}:{txt}",
                color="#000000",
                fontsize=6,
                bbox=dict(facecolor="white", alpha=0.65, edgecolor="none", pad=1),
            )

        exp = (evidence.get("evidence_window") or {}).get("expansion") or {}
        ax.text(
            8,
            h - 12,
            f"expanded={exp.get('expanded')} iters={exp.get('expansions')} "
            f"clipped={exp.get('still_clipped_count')}",
            color="#333333",
            fontsize=7,
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=1),
        )

        fig.savefig(str(out_path), dpi=100, bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
        return {"success": True, "path": str(out_path), "img_w": w, "img_h": h}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "path": str(out_path)}
