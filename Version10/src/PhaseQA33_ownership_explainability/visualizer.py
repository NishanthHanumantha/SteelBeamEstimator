"""
Ownership explainability visual outputs (matplotlib, additive only).
MODEL_VERSION: 10.0.3
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "10.0.3"


def _rect(ax, bbox, **kwargs):
    if not bbox or len(bbox) < 4:
        return
    x0, y0, x1, y1 = bbox
    from matplotlib.patches import Rectangle

    ax.add_patch(
        Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=kwargs.pop("fill", False),
            **kwargs,
        )
    )


def generate_beam_visuals(
    record: Dict[str, Any],
    *,
    envelope_dir: Path,
    competing_dir: Path,
    flow_dir: Path,
) -> Dict[str, Any]:
    beam_id = record["beam_id"]
    paths: Dict[str, Any] = {"beam_id": beam_id, "error": None}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        paths["error"] = f"matplotlib_unavailable: {exc}"
        return paths

    envelope_dir.mkdir(parents=True, exist_ok=True)
    competing_dir.mkdir(parents=True, exist_ok=True)
    flow_dir.mkdir(parents=True, exist_ok=True)

    try:
        paths.update(
            _envelope_overlay(record, envelope_dir / f"{beam_id}_candidate_envelope.png", plt)
        )
        paths.update(
            _owned_rejected(
                record, envelope_dir / f"{beam_id}_owned_vs_rejected.png", plt
            )
        )
        paths.update(
            _competing_map(
                record, competing_dir / f"{beam_id}_competing_beams.png", plt
            )
        )
        paths.update(
            _score_heatmap(
                record, envelope_dir / f"{beam_id}_ownership_score_heatmap.png", plt
            )
        )
        paths.update(
            _decision_flow(
                record, flow_dir / f"{beam_id}_entity_flow.png", plt
            )
        )
        paths["decision_tree_summary_md"] = _decision_tree_text(record)
    except Exception as exc:
        paths["error"] = str(exc)
    return paths


def _envelope_overlay(record: Dict[str, Any], path: Path, plt) -> Dict[str, str]:
    d = record.get("stage1_candidate_discovery") or {}
    zones = d.get("envelope_zones") or {}
    fig, ax = plt.subplots(figsize=(10, 7))
    search = d.get("ownership_search_envelope")
    _rect(ax, search, edgecolor="black", linewidth=2, label="search envelope")
    _rect(ax, _zone_bbox(zones.get("crop_extent")), edgecolor="blue", linewidth=1.5, label="crop")
    _rect(
        ax,
        _zone_bbox(zones.get("concrete_envelope")),
        edgecolor="green",
        linewidth=1.5,
        label="concrete",
    )
    _rect(
        ax,
        _zone_bbox(zones.get("annotation_reach")),
        edgecolor="orange",
        linewidth=1.5,
        linestyle="--",
        label="annotation_reach",
    )
    for e in d.get("nearby_entities") or []:
        pt = e.get("point")
        if not pt:
            continue
        color = "lime" if e.get("candidate") else "red"
        ax.scatter(pt[0], pt[1], c=color, s=18, alpha=0.7)
    ax.set_aspect("equal")
    ax.set_title(f"{record['beam_id']} Candidate Envelope Overlay")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return {"candidate_envelope_overlay": str(path)}


def _owned_rejected(record: Dict[str, Any], path: Path, plt) -> Dict[str, str]:
    scoring = record.get("stage2_ownership_scoring") or {}
    discovery = record.get("stage1_candidate_discovery") or {}
    pts = {e["entity_id"]: e.get("point") for e in discovery.get("nearby_entities") or []}
    fig, ax = plt.subplots(figsize=(10, 7))
    _rect(
        ax,
        discovery.get("ownership_search_envelope"),
        edgecolor="gray",
        linewidth=1,
        label="search",
    )
    for s in scoring.get("t18_scored_entities") or []:
        pt = pts.get(s["entity_id"])
        if not pt:
            continue
        color = "green" if s.get("accepted") else "red"
        ax.scatter(pt[0], pt[1], c=color, s=40, alpha=0.8)
        ax.annotate(
            f"{s.get('total_ownership_score')}",
            (pt[0], pt[1]),
            fontsize=6,
            alpha=0.8,
        )
    ax.set_aspect("equal")
    ax.set_title(f"{record['beam_id']} Owned (green) vs Rejected (red)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return {"owned_vs_rejected": str(path)}


def _competing_map(record: Dict[str, Any], path: Path, plt) -> Dict[str, str]:
    texts = (record.get("stage3_competing_beams") or {}).get("by_annotation_text") or {}
    comps = (record.get("stage3_competing_beams") or {}).get("by_entity") or {}
    fig, ax = plt.subplots(figsize=(10, 6))
    if texts:
        labels = []
        counts = []
        for text, c in list(texts.items())[:30]:
            labels.append(str(text)[:24])
            counts.append(int(c.get("beam_count") or 0))
        y = range(len(labels))
        ax.barh(list(y), counts, color="steelblue")
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel("Beams considering same annotation text")
        ax.set_title(f"{record['beam_id']} Competing Beam Ownership Map (by text)")
    else:
        multi = [
            (eid, c)
            for eid, c in comps.items()
            if len(c.get("competing_beams") or []) >= 2
        ]
        if not multi:
            ax.text(
                0.5,
                0.5,
                "No multi-beam competitions for this beam",
                ha="center",
                va="center",
            )
            ax.axis("off")
        else:
            labels = []
            margins = []
            winners = []
            for eid, c in multi[:30]:
                labels.append(str(eid)[:18])
                winners.append(c.get("winning_beam") or "?")
                margins.append(float(c.get("margin") or 0))
            y = range(len(labels))
            ax.barh(list(y), margins, color="steelblue")
            ax.set_yticks(list(y))
            ax.set_yticklabels(
                [f"{l} -> {w}" for l, w in zip(labels, winners)], fontsize=7
            )
            ax.set_xlabel("Score margin")
            ax.set_title(f"{record['beam_id']} Competing Beam Ownership Map")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return {"competing_beam_map": str(path)}


def _score_heatmap(record: Dict[str, Any], path: Path, plt) -> Dict[str, str]:
    scoring = record.get("stage2_ownership_scoring") or {}
    discovery = record.get("stage1_candidate_discovery") or {}
    pts = {e["entity_id"]: e.get("point") for e in discovery.get("nearby_entities") or []}
    xs, ys, cs = [], [], []
    for s in scoring.get("t18_scored_entities") or []:
        pt = pts.get(s["entity_id"])
        if not pt:
            continue
        xs.append(pt[0])
        ys.append(pt[1])
        cs.append(float(s.get("total_ownership_score") or 0.0))
    fig, ax = plt.subplots(figsize=(10, 7))
    _rect(ax, discovery.get("ownership_search_envelope"), edgecolor="gray", linewidth=1)
    if xs:
        sc = ax.scatter(xs, ys, c=cs, cmap="RdYlGn", s=50, vmin=0, vmax=1)
        fig.colorbar(sc, ax=ax, label="ownership_score")
    ax.set_aspect("equal")
    ax.set_title(f"{record['beam_id']} Ownership Score Heatmap")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return {"ownership_score_heatmap": str(path)}


def _decision_flow(record: Dict[str, Any], path: Path, plt) -> Dict[str, str]:
    cov = record.get("stage5_coverage") or {}
    stages = [
        ("Nearby", int(cov.get("entities_inside_search_envelope") or 0)),
        ("Candidate", int(cov.get("entities_considered") or 0)),
        ("Scored", int(cov.get("entities_scored") or 0)),
        ("Owned", int(cov.get("entities_owned") or 0)),
        ("Rejected", int(cov.get("entities_rejected") or 0)),
        ("Owned elsewhere", int(cov.get("entities_owned_elsewhere") or 0)),
    ]
    fig, ax = plt.subplots(figsize=(9, 3.5))
    xs = list(range(len(stages)))
    ys = [s[1] for s in stages]
    ax.plot(xs, ys, marker="o", linewidth=2, color="darkblue")
    for i, (name, val) in enumerate(stages):
        ax.annotate(f"{name}\n{val}", (i, val), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([s[0] for s in stages])
    ax.set_ylabel("Entity count")
    ax.set_title(f"{record['beam_id']} Entity Flow: Nearby -> Candidate -> Scored -> Owned/Rejected")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return {"entity_flow_diagram": str(path)}


def _decision_tree_text(record: Dict[str, Any]) -> str:
    lines = [f"### {record['beam_id']} Decision Tree Summary", ""]
    traces = (record.get("stage4_decision_traces") or {}).get("traces") or []
    # Prefer rejected annotations and a few owned samples
    rejected = [t for t in traces if t.get("outcome") == "REJECTED"][:8]
    owned = [t for t in traces if t.get("outcome") == "OWNED"][:4]
    for t in rejected + owned:
        lines.append(f"**{t.get('entity_id')}** ({t.get('entity_type')}) text={t.get('text')}")
        lines.append("")
        for step in t.get("decision_path") or []:
            lines.append(f"  - {step}")
        lines.append(f"  => **{t.get('outcome')}**")
        lines.append("")
    return "\n".join(lines)


def _zone_bbox(z: Any) -> Optional[List[float]]:
    if not z:
        return None
    if isinstance(z, (list, tuple)) and len(z) >= 4:
        return list(map(float, z[:4]))
    if isinstance(z, dict):
        try:
            return [
                float(z.get("x0", z.get("xmin"))),
                float(z.get("y0", z.get("ymin"))),
                float(z.get("x1", z.get("xmax"))),
                float(z.get("y1", z.get("ymax"))),
            ]
        except Exception:
            return None
    return None
