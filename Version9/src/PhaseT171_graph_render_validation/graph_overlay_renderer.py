"""
T1.7.1 — Separate validation renderer: base DXF crop + AnnotationGraph overlays.
MODEL_VERSION: 9.4.1

Does not modify PhaseM.1 / T1.6 renderers. Imports them as black boxes only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .renderer_snapshot import find_reinforcement_dxf, load_dxf_renderer, load_extent

MODEL_VERSION = "9.4.1"

# Deterministic overlay palette
COLORS = {
    "PhysicalBar": "#2ECC71",       # green
    "Leader": "#3498DB",            # blue
    "LeaderArrow": "#2980B9",
    "LeaderTarget": "#1ABC9C",
    "Annotation": "#E67E22",        # orange
    "Semantic": "#9B59B6",          # purple
    "DevelopmentLength": "#8E44AD",
    "SideFaceReinforcement": "#9B59B6",
    "StirrupNote": "#9B59B6",
    "SemanticFact": "#9B59B6",
    "SpacerBar": "#9B59B6",
    "Beam": "#7F8C8D",              # grey
    "Dimension": "#F1C40F",
    "chain": "#E74C3C",             # red for multi-leader chains
}


def _nodes_by_type(nodes: List[Dict[str, Any]], beam_id: str) -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {}
    for n in nodes:
        if n.get("beam_id") != beam_id:
            continue
        out.setdefault(n.get("type") or "Unknown", []).append(n)
    return out


def _index_edges(edges: List[Dict[str, Any]], beam_id: str):
    out: Dict[str, List[Dict]] = {}
    for e in edges:
        if e.get("beam_id") != beam_id:
            continue
        out.setdefault(e["source_id"], []).append(e)
        out.setdefault(e["target_id"], []).append(e)
    return out


def render_graph_aware(
    *,
    engine_root: Path,
    run_root: Path,
    output_root: Path,
    beam_id: str,
    graph_payload: Dict[str, Any],
    out_graph_aware: Path,
    out_overlay_only: Path,
    max_dim_px: int = 1200,
    dpi: int = 140,
) -> Dict[str, Any]:
    """
    Produce:
      - GraphAware_Render.png  : DXF base + coloured graph overlays + labels
      - Overlay_Render.png     : white canvas + overlays only (graph proof)
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, FancyBboxPatch
    from PIL import Image
    import numpy as np

    extent = load_extent(output_root, beam_id, engine_root)
    if not extent:
        return {"success": False, "error": "no_extent", "beam_id": beam_id}
    xmin, ymin, xmax, ymax = extent
    dxf = find_reinforcement_dxf(run_root)
    if not dxf:
        return {"success": False, "error": "no_dxf", "beam_id": beam_id}

    # --- Base render via black-box existing renderer ---
    out_graph_aware = Path(out_graph_aware)
    out_overlay_only = Path(out_overlay_only)
    out_graph_aware.parent.mkdir(parents=True, exist_ok=True)
    tmp_base = out_graph_aware.parent / f"_tmp_base_{beam_id}.png"
    mod = load_dxf_renderer(engine_root)
    mod.render_dxf_region_to_png(dxf, tmp_base, extent, render_text=True)

    nodes = graph_payload.get("nodes") or []
    edges = graph_payload.get("edges") or []
    by_type = _nodes_by_type(nodes, beam_id)
    edge_ix = _index_edges(edges, beam_id)

    w = max(xmax - xmin, 1e-6)
    h = max(ymax - ymin, 1e-6)
    aspect = w / h
    if aspect >= 1.0:
        tw, th = max_dim_px, max(400, round(max_dim_px / aspect))
    else:
        th, tw = max_dim_px, max(400, round(max_dim_px * aspect))

    def _draw_overlays(ax, *, label_annotations: bool = True) -> Dict[str, int]:
        counts = {
            "physical_bars": 0,
            "leaders": 0,
            "annotations": 0,
            "semantics": 0,
            "chains": 0,
        }
        # Beam envelope
        ax.add_patch(
            FancyBboxPatch(
                (xmin, ymin),
                w,
                h,
                boxstyle="square,pad=0",
                fill=False,
                edgecolor=COLORS["Beam"],
                linewidth=1.2,
                linestyle="--",
                alpha=0.8,
            )
        )

        # Physical bars
        for b in by_type.get("PhysicalBar", []):
            a = b.get("attributes") or {}
            try:
                x0, x1 = float(a["start_x"]), float(a["end_x"])
                y = float(a["y_position"])
            except Exception:
                continue
            ax.plot(
                [x0, x1],
                [y, y],
                color=COLORS["PhysicalBar"],
                linewidth=2.0,
                solid_capstyle="round",
                zorder=5,
            )
            counts["physical_bars"] += 1

        # Leaders
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
                color=COLORS["Leader"],
                linewidth=1.4,
                zorder=6,
            )
            ax.plot(
                tip[0],
                tip[1],
                marker=">",
                color=COLORS["LeaderArrow"],
                markersize=5,
                zorder=7,
            )
            ax.add_patch(
                Circle(
                    tip,
                    radius=max(w, h) * 0.004,
                    fill=True,
                    facecolor=COLORS["LeaderTarget"],
                    edgecolor="none",
                    zorder=7,
                )
            )
            counts["leaders"] += 1

        # Annotation → leader → bar chains (dashed)
        for ann in by_type.get("Annotation", []):
            a = ann.get("attributes") or {}
            try:
                ax_, ay_ = float(a["x"]), float(a["y"])
            except Exception:
                continue
            # ATTACHED_TO leaders
            for e in edge_ix.get(ann["id"], []):
                if e.get("type") != "ATTACHED_TO" or e.get("source_id") != ann["id"]:
                    continue
                lid = e["target_id"]
                Lnode = next(
                    (n for n in by_type.get("Leader", []) if n["id"] == lid), None
                )
                if not Lnode:
                    continue
                la = Lnode.get("attributes") or {}
                try:
                    tx, ty = float(la["tail_x"]), float(la["tail_y"])
                except Exception:
                    continue
                ax.plot(
                    [ax_, tx],
                    [ay_, ty],
                    color=COLORS["chain"],
                    linewidth=0.9,
                    linestyle=":",
                    alpha=0.85,
                    zorder=4,
                )
                counts["chains"] += 1

        # Annotations
        for ann in by_type.get("Annotation", []):
            a = ann.get("attributes") or {}
            try:
                ax_, ay_ = float(a["x"]), float(a["y"])
            except Exception:
                continue
            ax.plot(
                ax_,
                ay_,
                marker="o",
                color=COLORS["Annotation"],
                markersize=6,
                zorder=8,
            )
            counts["annotations"] += 1
            if label_annotations:
                txt = str(a.get("clean_text") or "")[:28]
                if txt:
                    ax.text(
                        ax_,
                        ay_ + h * 0.015,
                        txt,
                        color=COLORS["Annotation"],
                        fontsize=6,
                        ha="center",
                        va="bottom",
                        zorder=9,
                        bbox=dict(
                            boxstyle="round,pad=0.15",
                            facecolor="white",
                            edgecolor=COLORS["Annotation"],
                            alpha=0.75,
                            linewidth=0.5,
                        ),
                    )

        # Semantics
        sem_types = (
            "SemanticFact",
            "DevelopmentLength",
            "SideFaceReinforcement",
            "StirrupNote",
            "SpacerBar",
        )
        for st in sem_types:
            for s in by_type.get(st, []):
                sa = s.get("attributes") or {}
                # Find linked annotation coords via INTERPRETS edge
                ann_xy = None
                for e in edge_ix.get(s["id"], []):
                    if e.get("type") == "INTERPRETS" and e.get("source_id") == s["id"]:
                        ann = next(
                            (
                                n
                                for n in by_type.get("Annotation", [])
                                if n["id"] == e["target_id"]
                            ),
                            None,
                        )
                        if ann:
                            aa = ann.get("attributes") or {}
                            try:
                                ann_xy = (float(aa["x"]), float(aa["y"]))
                            except Exception:
                                pass
                if not ann_xy:
                    continue
                meaning = str(
                    sa.get("engineering_meaning") or sa.get("semantic_type") or st
                )
                color = COLORS.get(st, COLORS["Semantic"])
                ax.plot(
                    ann_xy[0],
                    ann_xy[1],
                    marker="s",
                    color=color,
                    markersize=4,
                    zorder=10,
                )
                ax.text(
                    ann_xy[0] + w * 0.01,
                    ann_xy[1] - h * 0.02,
                    meaning,
                    color=color,
                    fontsize=5.5,
                    fontweight="bold",
                    zorder=10,
                )
                counts["semantics"] += 1

        return counts

    # --- Overlay-only figure ---
    fig1 = plt.figure(figsize=(tw / dpi, th / dpi))
    ax1 = fig1.add_axes([0.0, 0.0, 1.0, 1.0])
    ax1.set_aspect("equal")
    ax1.set_xlim(xmin, xmax)
    ax1.set_ylim(ymin, ymax)
    ax1.set_axis_off()
    ax1.set_facecolor("white")
    counts = _draw_overlays(ax1, label_annotations=True)
    # Legend
    handles = [
        Line2D([0], [0], color=COLORS["PhysicalBar"], lw=2, label="PhysicalBar"),
        Line2D([0], [0], color=COLORS["Leader"], lw=1.5, label="Leader"),
        Line2D(
            [0],
            [0],
            marker="o",
            color=COLORS["Annotation"],
            lw=0,
            markersize=6,
            label="Annotation",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color=COLORS["Semantic"],
            lw=0,
            markersize=5,
            label="Semantic",
        ),
        Line2D(
            [0],
            [0],
            color=COLORS["chain"],
            lw=1,
            linestyle=":",
            label="Ann→Leader chain",
        ),
    ]
    ax1.legend(
        handles=handles,
        loc="lower right",
        fontsize=5,
        framealpha=0.85,
        borderpad=0.3,
    )
    fig1.savefig(str(out_overlay_only), dpi=dpi, facecolor="white")
    plt.close(fig1)

    # --- Graph-aware = base image + overlays in same DXF coords ---
    # Matplotlib DXF PNG has row0 at visual top (= ymax); match with origin='upper'.
    base_img = np.array(Image.open(tmp_base).convert("RGB"))
    bh, bw = base_img.shape[0], base_img.shape[1]
    fig2 = plt.figure(figsize=(bw / dpi, bh / dpi))
    ax2 = fig2.add_axes([0.0, 0.0, 1.0, 1.0])
    ax2.imshow(
        base_img,
        extent=[xmin, xmax, ymin, ymax],
        origin="upper",
        zorder=0,
        aspect="equal",
    )
    ax2.set_xlim(xmin, xmax)
    ax2.set_ylim(ymin, ymax)
    ax2.set_axis_off()
    counts2 = _draw_overlays(ax2, label_annotations=True)
    ax2.legend(
        handles=handles,
        loc="lower right",
        fontsize=5,
        framealpha=0.85,
        borderpad=0.3,
    )
    fig2.savefig(str(out_graph_aware), dpi=dpi, facecolor="white")
    plt.close(fig2)

    if tmp_base.exists():
        tmp_base.unlink()

    return {
        "success": True,
        "beam_id": beam_id,
        "extent": list(extent),
        "graph_aware": str(out_graph_aware),
        "overlay": str(out_overlay_only),
        "overlay_counts": counts2,
        "model_version": MODEL_VERSION,
    }
