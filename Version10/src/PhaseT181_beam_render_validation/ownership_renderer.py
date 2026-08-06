"""
T1.8.1 — Ownership render layer (wrapper; does not edit existing renderers).
MODEL_VERSION: 9.5.1

Renders ONLY nodes present in BeamScopedAnnotations.json.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .image_exporter import find_reinforcement_dxf, load_dxf_renderer, load_extent

MODEL_VERSION = "9.5.1"

# Prompt palette
COLOR_OUTLINE = "#000000"
COLOR_BARS = "#1F4E79"  # blue
COLOR_LEADERS = "#228B22"  # green
COLOR_TEXT = "#000000"
COLOR_CENTRELINE = "#555555"


def _by_type(nodes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for n in nodes:
        out.setdefault(n.get("type") or "Unknown", []).append(n)
    return out


def render_owned_beam(
    *,
    engine_root: Path,
    run_root: Path,
    output_root: Path,
    beam_id: str,
    scoped: Dict[str, Any],
    out_path: Path,
    inventory_by_handle: Optional[Dict[str, Dict[str, Any]]] = None,
    max_dim_px: int = 1400,
    dpi: int = 140,
) -> Dict[str, Any]:
    """
    Produce {beam}_render.png from scoped (owned) graph nodes only.
    Base = DXF geometry without text (black-box), overlays = owned entities.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyBboxPatch
    from PIL import Image
    import numpy as np

    extent = load_extent(output_root, beam_id, engine_root)
    # Prefer beam node extent if present
    for n in scoped.get("nodes") or []:
        if n.get("type") == "Beam":
            ext = (n.get("attributes") or {}).get("extent")
            if ext and len(ext) >= 4:
                extent = (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))
            break
    if not extent:
        return {"success": False, "error": "no_extent", "beam_id": beam_id}

    xmin, ymin, xmax, ymax = extent
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dxf = find_reinforcement_dxf(run_root)
    tmp_base = out_path.parent / f"_tmp_base_{beam_id}.png"
    base_ok = False
    if dxf:
        try:
            mod = load_dxf_renderer(engine_root)
            # No DXF text → neighbour annotation strings cannot leak into base
            mod.render_dxf_region_to_png(dxf, tmp_base, extent, render_text=False)
            base_ok = tmp_base.exists()
        except Exception as exc:  # noqa: BLE001
            base_ok = False
            base_err = str(exc)
    else:
        base_err = "no_dxf"

    nodes = list(scoped.get("nodes") or [])
    by_type = _by_type(nodes)

    # Centreline from Beam node
    axis = {}
    for n in by_type.get("Beam", []):
        axis = (n.get("attributes") or {}).get("axis") or {}
        break

    w = max(xmax - xmin, 1e-6)
    h = max(ymax - ymin, 1e-6)
    counts = {
        "annotations": 0,
        "leaders": 0,
        "bars": 0,
        "owned_entities_drawn": 0,
    }
    rendered_ann_texts: List[str] = []

    def _draw(ax) -> None:
        # Outline
        ax.add_patch(
            FancyBboxPatch(
                (xmin, ymin),
                w,
                h,
                boxstyle="square,pad=0",
                fill=False,
                edgecolor=COLOR_OUTLINE,
                linewidth=1.6,
                zorder=3,
            )
        )
        # Centreline
        try:
            x0 = float(axis.get("dxf_start_x") or xmin)
            x1 = float(axis.get("dxf_end_x") or xmax)
            cy = float(axis.get("mark_y") or axis.get("centroid_y") or (ymin + ymax) / 2)
            ax.plot(
                [x0, x1],
                [cy, cy],
                color=COLOR_CENTRELINE,
                linewidth=1.0,
                linestyle="--",
                zorder=4,
            )
        except Exception:
            pass

        # Beam ID label
        ax.text(
            xmin + w * 0.02,
            ymax - h * 0.04,
            beam_id,
            color=COLOR_OUTLINE,
            fontsize=11,
            fontweight="bold",
            zorder=20,
            bbox=dict(
                boxstyle="round,pad=0.2",
                facecolor="white",
                edgecolor=COLOR_OUTLINE,
                alpha=0.9,
                linewidth=0.8,
            ),
        )

        # Owned physical bars (blue)
        for b in by_type.get("PhysicalBar", []):
            a = b.get("attributes") or {}
            try:
                x0, x1 = float(a["start_x"]), float(a["end_x"])
                y = float(a["y_position"])
            except Exception:
                continue
            # Clip long continuous bars to beam extent for clarity
            x0c, x1c = max(min(x0, x1), xmin - 50), min(max(x0, x1), xmax + 50)
            ax.plot(
                [x0c, x1c],
                [y, y],
                color=COLOR_BARS,
                linewidth=2.2,
                solid_capstyle="round",
                zorder=5,
            )
            counts["bars"] += 1

        # OwnedEntity longitudinal lines (when PhysicalBar geom absent)
        inv = inventory_by_handle or {}
        for oe in by_type.get("OwnedEntity", []):
            a = oe.get("attributes") or {}
            role = str(a.get("role") or "")
            if role not in (
                "TOP_BAR",
                "BOTTOM_BAR",
                "LONGITUDINAL_BAR",
            ):
                continue
            handle = str(a.get("handle") or "").upper()
            ent = inv.get(handle) or {}
            sp, ep = ent.get("start_point"), ent.get("end_point")
            if not sp or not ep:
                continue
            try:
                x0, y0 = float(sp[0]), float(sp[1])
                x1, y1 = float(ep[0]), float(ep[1])
            except Exception:
                continue
            if abs(y1 - y0) > 80:
                continue  # non-horizontal
            y = 0.5 * (y0 + y1)
            x0c, x1c = max(min(x0, x1), xmin - 50), min(max(x0, x1), xmax + 50)
            if x1c - x0c < 20:
                continue
            ax.plot(
                [x0c, x1c],
                [y, y],
                color=COLOR_BARS,
                linewidth=2.0,
                solid_capstyle="round",
                zorder=5,
                alpha=0.85,
            )
            counts["owned_entities_drawn"] += 1
            counts["bars"] += 1

        # Leaders (green)
        for L in by_type.get("Leader", []):
            a = L.get("attributes") or {}
            try:
                tip = (float(a["tip_x"]), float(a["tip_y"]))
                tail = (float(a["tail_x"]), float(a["tail_y"]))
            except Exception:
                continue
            ax.plot(
                [tail[0], tip[0]],
                [tail[1], tip[1]],
                color=COLOR_LEADERS,
                linewidth=1.5,
                zorder=6,
            )
            ax.plot(
                tip[0],
                tip[1],
                marker=">",
                color=COLOR_LEADERS,
                markersize=5,
                zorder=7,
            )
            counts["leaders"] += 1

        # Annotations (black text)
        for ann in by_type.get("Annotation", []):
            a = ann.get("attributes") or {}
            try:
                ax_, ay_ = float(a["x"]), float(a["y"])
            except Exception:
                continue
            txt = str(a.get("clean_text") or "")
            rendered_ann_texts.append(txt)
            ax.plot(ax_, ay_, marker="o", color=COLOR_TEXT, markersize=5, zorder=8)
            counts["annotations"] += 1
            if txt:
                display = txt if len(txt) <= 36 else txt[:33] + "..."
                ax.text(
                    ax_,
                    ay_ + h * 0.012,
                    display,
                    color=COLOR_TEXT,
                    fontsize=6.5,
                    ha="center",
                    va="bottom",
                    zorder=9,
                    bbox=dict(
                        boxstyle="round,pad=0.15",
                        facecolor="white",
                        edgecolor="#333333",
                        alpha=0.85,
                        linewidth=0.5,
                    ),
                )

    # Compose figure
    if base_ok:
        base_img = np.array(Image.open(tmp_base).convert("RGB"))
        bh, bw = base_img.shape[0], base_img.shape[1]
        fig = plt.figure(figsize=(bw / dpi, bh / dpi))
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.imshow(
            base_img,
            extent=[xmin, xmax, ymin, ymax],
            origin="upper",
            zorder=0,
            aspect="equal",
        )
    else:
        aspect = w / h
        if aspect >= 1.0:
            tw, th = max_dim_px, max(400, round(max_dim_px / aspect))
        else:
            th, tw = max_dim_px, max(400, round(max_dim_px * aspect))
        fig = plt.figure(figsize=(tw / dpi, th / dpi))
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_facecolor("white")

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_axis_off()
    _draw(ax)
    handles = [
        Line2D([0], [0], color=COLOR_OUTLINE, lw=1.5, label="Outline"),
        Line2D([0], [0], color=COLOR_BARS, lw=2, label="Owned bars"),
        Line2D([0], [0], color=COLOR_LEADERS, lw=1.5, label="Owned leaders"),
        Line2D(
            [0],
            [0],
            marker="o",
            color=COLOR_TEXT,
            lw=0,
            markersize=5,
            label="Owned annotations",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="lower right",
        fontsize=5,
        framealpha=0.9,
        borderpad=0.3,
    )
    fig.savefig(str(out_path), dpi=dpi, facecolor="white")
    plt.close(fig)

    if tmp_base.exists():
        try:
            tmp_base.unlink()
        except OSError:
            pass

    return {
        "success": True,
        "beam_id": beam_id,
        "path": str(out_path),
        "extent": list(extent),
        "base_geometry": base_ok,
        "counts": counts,
        "rendered_annotation_texts": rendered_ann_texts,
        "model_version": MODEL_VERSION,
        **({} if base_ok else {"base_warning": locals().get("base_err")}),
    }
