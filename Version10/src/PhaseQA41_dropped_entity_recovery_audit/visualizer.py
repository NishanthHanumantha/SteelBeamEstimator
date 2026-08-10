"""
QA.4.1 diagnostic visualisations (Fourth Set audit population only).
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.5.0"


def generate_all_visuals(
    *,
    out_dir: Path,
    audits: List[Dict[str, Any]],
    patterns: List[Dict[str, Any]],
    matrix: Dict[str, Any],
    representatives: Dict[str, Any],
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

    paths["beam_distribution"] = str(_beam_dist(out_dir / "Beam_wise_dropped_distribution.png", audits, plt))
    paths["category_potential"] = str(
        _cat_pot(out_dir / "Recovery_potential_distribution.png", audits, plt)
    )
    paths["envelope_distance"] = str(
        _env_dist(out_dir / "Envelope_distance_distribution.png", audits, plt)
    )
    paths["pattern_freq"] = str(
        _pattern_freq(out_dir / "Failure_pattern_frequency.png", patterns, plt)
    )
    paths["priority_matrix"] = str(
        _priority(out_dir / "Recovery_priority_matrix.png", matrix, plt)
    )
    paths["envelope_scatter"] = str(
        _env_scatter(out_dir / "Dropped_vs_production_envelope.png", audits, plt)
    )
    paths["leader_examples"] = str(
        _leader_ex(out_dir / "Leader_chain_failure_examples.png", audits, plt)
    )
    paths["geometry_examples"] = str(
        _geom_ex(out_dir / "Geometry_failure_examples.png", audits, plt)
    )
    paths["representative_gallery"] = str(
        _gallery(out_dir / "Representative_case_gallery.png", representatives, plt)
    )
    return paths


def _beam_dist(path, audits, plt):
    from collections import Counter

    c = Counter(a["beam_id"] for a in audits)
    beams = sorted(c)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(beams, [c[b] for b in beams], color="#d62728")
    ax.set_title("Fourth Set — Beam-wise Dropped Entity Distribution (n=104)")
    ax.set_ylabel("Dropped count")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _cat_pot(path, audits, plt):
    from collections import defaultdict

    data = defaultdict(lambda: defaultdict(int))
    for a in audits:
        data[a.get("primary_audit_category")][a.get("recovery_potential")] += 1
    cats = list(data.keys())
    pots = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(cats))
    bottom = [0] * len(cats)
    colors = {"HIGH": "#2ca02c", "MEDIUM": "#ff7f0e", "LOW": "#d62728", "UNKNOWN": "#7f7f7f"}
    for p in pots:
        vals = [data[c].get(p, 0) for c in cats]
        ax.bar(x, vals, bottom=bottom, label=p, color=colors[p])
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xticks(list(x))
    ax.set_xticklabels([c.replace("_", "\n") for c in cats], fontsize=7)
    ax.legend()
    ax.set_title("Recovery Potential by Failure Category (diagnostic only)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _env_dist(path, audits, plt):
    dists = [
        (a.get("envelope_audit") or {}).get("min_distance_to_production_envelope")
        for a in audits
        if a.get("primary_audit_category") == "ENVELOPE_NEVER_CANDIDATE"
    ]
    dists = [d for d in dists if d is not None]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if dists:
        ax.hist(dists, bins=20, color="steelblue", edgecolor="white")
    ax.set_xlabel("Distance to production envelope (mm)")
    ax.set_ylabel("Count")
    ax.set_title("Envelope-dropped distance distribution")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _pattern_freq(path, patterns, plt):
    labels = [p["pattern_id"] for p in patterns]
    vals = [p["entity_count"] for p in patterns]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(labels[::-1], vals[::-1], color="#9467bd")
    ax.set_xlabel("Entity count")
    ax.set_title("Failure pattern frequency (Fourth Set dropped)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _priority(path, matrix, plt):
    rows = matrix.get("rows") or []
    labels = [r.get("label") or r.get("failure_category") for r in rows if r.get("entity_count")]
    counts = [r.get("entity_count") for r in rows if r.get("entity_count")]
    highs = [r.get("high_potential") for r in rows if r.get("entity_count")]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(labels))
    ax.bar(x, counts, label="Count", color="#1f77b4")
    ax.bar(x, highs, label="HIGH potential", color="#2ca02c", alpha=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend()
    ax.set_title("Recovery Priority Matrix (counts vs HIGH potential)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _env_scatter(path, audits, plt):
    # Plot centroids relative to their beam crop (normalized)
    fig, ax = plt.subplots(figsize=(8, 6))
    plotted = 0
    for a in audits:
        if a.get("primary_audit_category") != "ENVELOPE_NEVER_CANDIDATE":
            continue
        env = a.get("envelope_audit") or {}
        crop = env.get("crop_extent") or env.get("production_envelope")
        pt = env.get("entity_centroid")
        if not crop or not pt:
            continue
        # normalize into crop unit square
        x0, y0, x1, y1 = crop
        if x1 == x0 or y1 == y0:
            continue
        nx = (pt[0] - x0) / (x1 - x0)
        ny = (pt[1] - y0) / (y1 - y0)
        sp = env.get("spatial_relationship")
        color = {
            "NEAR_OUTSIDE": "orange",
            "MODERATE_OUTSIDE": "red",
            "FAR_OUTSIDE": "darkred",
            "BOUNDARY": "gold",
            "INSIDE": "green",
        }.get(sp, "gray")
        ax.scatter([nx], [ny], c=color, s=28, alpha=0.7)
        plotted += 1
    ax.axhline(0, color="gray", lw=0.5)
    ax.axhline(1, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.axvline(1, color="gray", lw=0.5)
    ax.set_title(f"Dropped centroids vs crop (normalized); n_plotted={plotted}")
    ax.set_xlabel("Normalized X in crop")
    ax.set_ylabel("Normalized Y in crop")
    ax.text(0.02, 0.02, "Box = production crop/envelope unit square", transform=ax.transAxes, fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _leader_ex(path, audits, plt):
    rows = [a for a in audits if a.get("primary_audit_category") == "LEADER_CHAIN_FAILURE"][:12]
    fig, ax = plt.subplots(figsize=(11, 6))
    labels = [f"{a['beam_id']}:{a['entity_id'][:16]}" for a in rows]
    dists = [
        ((a.get("leader_audit") or {}).get("terminal_distance_to_production_envelope") or 0)
        for a in rows
    ]
    if labels:
        ax.barh(labels[::-1], dists[::-1], color="#ff7f0e")
    ax.set_xlabel("Tip distance to production envelope (mm)")
    ax.set_title("Leader-chain failure examples (not recovered)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _geom_ex(path, audits, plt):
    rows = [a for a in audits if a.get("primary_audit_category") == "GEOMETRY_FAILURE"]
    fig, ax = plt.subplots(figsize=(9, 4))
    if not rows:
        ax.text(0.5, 0.5, "No geometry failures", ha="center")
        ax.axis("off")
    else:
        labels = [f"{a['beam_id']}:{a['entity_id'][:18]}" for a in rows]
        classes = [(a.get("geometry_audit") or {}).get("geometry_class") or "?" for a in rows]
        ax.barh(labels[::-1], [1] * len(labels), color="#8c564b")
        for i, c in enumerate(classes[::-1]):
            ax.text(1.02, i, c, va="center", fontsize=8)
        ax.set_title("Geometry failure examples (ALL)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _gallery(path, representatives, plt):
    blocks = []
    for key, title in [
        ("envelope_high", "Env HIGH"),
        ("envelope_medium", "Env MED"),
        ("leader_high", "Leader HIGH"),
        ("geometry_all", "Geometry ALL"),
    ]:
        for r in representatives.get(key) or []:
            blocks.append(f"{title}: {r.get('beam_id')} {r.get('entity_id')} pot={r.get('recovery_potential')}")
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.axis("off")
    ax.set_title("Representative Case Gallery (audit only — NOT recovered)")
    y = 0.95
    for line in blocks[:40]:
        ax.text(0.02, y, line, fontsize=8, family="monospace", transform=ax.transAxes)
        y -= 0.035
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
