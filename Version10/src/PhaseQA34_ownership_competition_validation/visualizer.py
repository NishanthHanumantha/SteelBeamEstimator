"""
QA.3.4 visualisations (matplotlib).
MODEL_VERSION: 10.0.4
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_VERSION = "10.0.4"


def generate_all_visuals(
    *,
    out_dir: Path,
    global_stats: Dict[str, Any],
    beam_summaries: List[Dict[str, Any]],
    all_classified: List[Dict[str, Any]],
    neighbour_matrix: Dict[str, Any],
    priority_beams: List[str],
) -> Dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:
        paths["error"] = str(exc)
        return paths

    paths["sankey"] = str(_sankey(out_dir / "Sankey_ownership_flow.png", global_stats, plt))
    paths["competition_matrix"] = str(
        _beam_matrix(
            out_dir / "Beam_competition_matrix.png",
            neighbour_matrix.get("matrix") or {},
            priority_beams,
            plt,
            np,
        )
    )
    paths["network"] = str(
        _network(out_dir / "Competition_network.png", neighbour_matrix, plt)
    )
    paths["dropped_heatmap"] = str(
        _dropped_heatmap(
            out_dir / "Dropped_entity_heatmap.png", beam_summaries, plt, np
        )
    )
    paths["margin_hist"] = str(
        _margin_hist(out_dir / "Ownership_margin_histogram.png", all_classified, plt)
    )
    paths["scatter"] = str(
        _winner_loser_scatter(
            out_dir / "Winner_vs_loser_scatter.png", all_classified, plt
        )
    )
    paths["top20_dropped"] = str(
        _top20_dropped(out_dir / "Top20_disappearing_entities.png", all_classified, plt)
    )
    paths["beam_summary"] = str(
        _beam_summary_bars(out_dir / "Beam_competition_summary.png", beam_summaries, plt)
    )
    return paths


def _sankey(path: Path, stats: Dict[str, Any], plt) -> Path:
    # Approximate Sankey with stacked flow bars (no plotly dependency)
    stages = [
        ("Rejected", int(stats.get("total_rejected") or 0)),
        ("OwnedElsewhere", int(stats.get("owned_elsewhere") or 0)),
        ("Dropped", int(stats.get("dropped") or 0)),
        ("LeaderFail", int(stats.get("leader_failures") or 0)),
        ("GeometryFail", int(stats.get("geometry_failures") or 0)),
        ("EnvelopeFail", int(stats.get("envelope_failures") or 0)),
        ("ConflictFail", int(stats.get("conflict_failures") or 0)),
    ]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    xs = list(range(len(stages)))
    ys = [s[1] for s in stages]
    colors = ["#444", "#2ca02c", "#d62728", "#ff7f0e", "#1f77b4", "#9467bd", "#8c564b"]
    ax.bar(xs, ys, color=colors)
    ax.set_xticks(xs)
    ax.set_xticklabels([s[0] for s in stages], rotation=20, ha="right")
    for i, v in enumerate(ys):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)
    ax.set_title("Ownership Competition Flow (Sankey proxy)")
    ax.set_ylabel("Entity count")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _beam_matrix(path: Path, matrix: Dict[str, Any], beams: List[str], plt, np) -> Path:
    n = len(beams)
    data = np.zeros((n, n))
    for i, a in enumerate(beams):
        for j, b in enumerate(beams):
            if a == b:
                continue
            data[i, j] = float((matrix.get(a) or {}).get(b) or 0)
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(data, cmap="YlOrRd")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(beams, rotation=45, ha="right")
    ax.set_yticklabels(beams)
    ax.set_xlabel("Winning neighbour")
    ax.set_ylabel("Losing beam")
    ax.set_title("Beam Competition Matrix")
    fig.colorbar(im, ax=ax, fraction=0.046)
    for i in range(n):
        for j in range(n):
            if data[i, j] > 0:
                ax.text(j, i, int(data[i, j]), ha="center", va="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _network(path: Path, neighbour_matrix: Dict[str, Any], plt) -> Path:
    details = neighbour_matrix.get("details") or []
    # Aggregate edges loser->winner
    edges: Dict[tuple, int] = {}
    for d in details:
        w = d.get("winner")
        if not w:
            continue
        key = (d.get("loser"), w)
        edges[key] = edges.get(key, 0) + 1
    fig, ax = plt.subplots(figsize=(9, 6))
    if not edges:
        ax.text(0.5, 0.5, "No cross-beam winners among priority set", ha="center")
        ax.axis("off")
    else:
        # Simple circular layout
        nodes = sorted({n for e in edges for n in e})
        import math

        pos = {}
        for i, n in enumerate(nodes):
            ang = 2 * math.pi * i / max(len(nodes), 1)
            pos[n] = (math.cos(ang), math.sin(ang))
        for (a, b), w in edges.items():
            x0, y0 = pos[a]
            x1, y1 = pos[b]
            ax.annotate(
                "",
                xy=(x1, y1),
                xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color="steelblue", lw=0.5 + 0.3 * w),
            )
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ax.text(mx, my, str(w), fontsize=7, color="darkred")
        for n, (x, y) in pos.items():
            ax.scatter([x], [y], s=400, c="lightyellow", edgecolors="black", zorder=3)
            ax.text(x, y, n, ha="center", va="center", fontsize=8, zorder=4)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("Competition Network (Loser -> Winner)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _dropped_heatmap(path: Path, summaries: List[Dict[str, Any]], plt, np) -> Path:
    beams = [s["beam_id"] for s in summaries]
    cats = [
        "dropped",
        "leader_failures",
        "geometry_failures",
        "search_envelope_failures",
        "conflict_failures",
        "owned_elsewhere",
    ]
    data = np.array([[float(s.get(c) or 0) for c in cats] for s in summaries])
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(data, aspect="auto", cmap="Reds")
    ax.set_yticks(range(len(beams)))
    ax.set_yticklabels(beams)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=25, ha="right")
    ax.set_title("Dropped / Failure Heatmap by Beam")
    fig.colorbar(im, ax=ax, fraction=0.03)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, int(data[i, j]), ha="center", va="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _margin_hist(path: Path, classified: List[Dict[str, Any]], plt) -> Path:
    margins = []
    for c in classified:
        for r in c.get("rejected_records") or []:
            if r.get("margin") is not None:
                margins.append(float(r["margin"]))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if margins:
        ax.hist(margins, bins=20, color="steelblue", edgecolor="white")
    else:
        ax.text(0.5, 0.5, "No competition margins (no OwnedElsewhere)", ha="center")
    ax.set_xlabel("Ownership margin (winner - local)")
    ax.set_ylabel("Count")
    ax.set_title("Ownership Margin Histogram")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _winner_loser_scatter(path: Path, classified: List[Dict[str, Any]], plt) -> Path:
    xs, ys, labels = [], [], []
    for c in classified:
        for r in c.get("rejected_records") or []:
            if r.get("winning_score") is None:
                continue
            xs.append(float(r.get("local_score") or 0))
            ys.append(float(r.get("winning_score") or 0))
            labels.append(r.get("beam_id"))
    fig, ax = plt.subplots(figsize=(6.5, 6))
    if xs:
        ax.scatter(xs, ys, alpha=0.7, c="purple")
        m = max(max(xs), max(ys), 1)
        ax.plot([0, m], [0, m], "k--", alpha=0.4, label="equal score")
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No winner/loser pairs", ha="center", transform=ax.transAxes)
    ax.set_xlabel("Loser local score")
    ax.set_ylabel("Winner score")
    ax.set_title("Winner vs Loser Scatter")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _top20_dropped(path: Path, classified: List[Dict[str, Any]], plt) -> Path:
    items = []
    for c in classified:
        for d in c.get("dropped") or []:
            items.append(d)
    # Prefer annotations, then by reason frequency
    items = items[:20] if len(items) <= 20 else sorted(
        items, key=lambda x: (0 if x.get("entity_type") == "Annotation" else 1, str(x.get("text") or ""))
    )[:20]
    fig, ax = plt.subplots(figsize=(11, 7))
    if not items:
        ax.text(0.5, 0.5, "No dropped entities", ha="center")
        ax.axis("off")
    else:
        labels = [
            f"{d.get('beam_id')}:{d.get('entity_type')}:{str(d.get('text') or d.get('entity_id'))[:28]}"
            for d in items
        ]
        # categorical y
        ax.barh(range(len(labels)), [1] * len(labels), color="#d62728")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel("Dropped (1=yes)")
        ax.set_title("Top Disappearing Entities")
        # annotate reason
        for i, d in enumerate(items):
            ax.text(1.02, i, str(d.get("reason") or "")[:40], va="center", fontsize=6)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _beam_summary_bars(path: Path, summaries: List[Dict[str, Any]], plt) -> Path:
    beams = [s["beam_id"] for s in summaries]
    dropped = [s.get("dropped") or 0 for s in summaries]
    elsewhere = [s.get("owned_elsewhere") or 0 for s in summaries]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(beams))
    ax.bar(x, dropped, label="Dropped", color="#d62728")
    ax.bar(x, elsewhere, bottom=dropped, label="OwnedElsewhere", color="#2ca02c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(beams, rotation=45, ha="right")
    ax.set_ylabel("Rejected entities")
    ax.set_title("Beam Competition Summary")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
