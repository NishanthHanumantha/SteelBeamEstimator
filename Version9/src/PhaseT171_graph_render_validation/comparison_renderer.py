"""
T1.7.1 — Side-by-side comparison + difference report.
MODEL_VERSION: 9.4.1
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

MODEL_VERSION = "9.4.1"


def make_side_by_side(
    original: Path,
    graph_aware: Path,
    dest: Path,
    *,
    title_left: str = "Original Render",
    title_right: str = "Graph-Aware Render",
    beam_id: str = "",
) -> Dict[str, Any]:
    """Identical-height side-by-side PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    import numpy as np

    original = Path(original)
    graph_aware = Path(graph_aware)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    img_l = Image.open(original).convert("RGB")
    img_r = Image.open(graph_aware).convert("RGB")
    # Match height
    h = max(img_l.height, img_r.height)
    def _resize_h(im: Image.Image, th: int) -> Image.Image:
        if im.height == th:
            return im
        w = max(1, int(im.width * th / im.height))
        return im.resize((w, th), Image.Resampling.BILINEAR)

    img_l = _resize_h(img_l, h)
    img_r = _resize_h(img_r, h)
    gap = 12
    canvas = Image.new("RGB", (img_l.width + gap + img_r.width, h + 36), (255, 255, 255))
    canvas.paste(img_l, (0, 36))
    canvas.paste(img_r, (img_l.width + gap, 36))

    arr = np.array(canvas)
    fig_w = canvas.width / 100
    fig_h = canvas.height / 100
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(arr)
    ax.set_axis_off()
    ax.text(
        img_l.width / 2,
        14,
        f"{beam_id} — {title_left}" if beam_id else title_left,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#333333",
    )
    ax.text(
        img_l.width + gap + img_r.width / 2,
        14,
        f"{beam_id} — {title_right}" if beam_id else title_right,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#333333",
    )
    fig.savefig(str(dest), dpi=100, facecolor="white")
    plt.close(fig)
    return {"path": str(dest), "width": canvas.width, "height": canvas.height + 0}


def _norm_text(t: str) -> str:
    t = (t or "").upper().replace("%%U", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _classify_label(text: str) -> Optional[str]:
    u = _norm_text(text)
    if "SIDE FACE" in u or "SIDE.FACE" in u:
        return "Side Face"
    if re.search(r"\bLD\b", u) or "DEVELOPMENT" in u:
        return "Ld"
    if re.search(r"\dL\s*[-–]?\s*[YTH]?\d", u.replace(" ", "")) or (
        "@" in u and "C/C" in u
    ):
        return "Stirrup"
    if re.search(r"\d\s*[-–]?\s*[YTH]?\s*\d{1,2}\b", u) and "FACE" not in u:
        return "Top/Long Bar"
    return None


def build_difference_report(
    beam_id: str,
    graph_payload: Dict[str, Any],
    ownership_rows: List[Dict[str, Any]],
    overlay_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Deterministic difference: annotations present in the graph vs those
    already represented by T1.6 HIGH text/MTEXT ownership (proxy for
    'originally visible' in ownership-filtered / dense crops).
    """
    nodes = [n for n in (graph_payload.get("nodes") or []) if n.get("beam_id") == beam_id]
    edges = [e for e in (graph_payload.get("edges") or []) if e.get("beam_id") == beam_id]

    graph_anns = [n for n in nodes if n.get("type") == "Annotation"]
    graph_texts = [
        _norm_text((n.get("attributes") or {}).get("clean_text") or "")
        for n in graph_anns
    ]
    graph_texts = [t for t in graph_texts if t]

    # Original-visible proxy: annotations with MATCHES_ENTITY to OwnedEntity,
    # or HIGH TEXT/MTEXT ownership roles that look like bar labels.
    matched_ann_ids: Set[str] = set()
    for e in edges:
        if e.get("type") != "MATCHES_ENTITY":
            continue
        src = e.get("source_id")
        tgt = next((n for n in nodes if n["id"] == e.get("target_id")), None)
        src_n = next((n for n in nodes if n["id"] == src), None)
        if src_n and src_n.get("type") == "Annotation" and tgt and tgt.get("type") == "OwnedEntity":
            matched_ann_ids.add(src)

    original_texts = []
    for n in graph_anns:
        if n["id"] in matched_ann_ids:
            original_texts.append(
                _norm_text((n.get("attributes") or {}).get("clean_text") or "")
            )
    # Also count HIGH owned text entities as originally visible labels
    owned_text_count = sum(
        1
        for r in ownership_rows
        if r.get("ownership") == "HIGH"
        and r.get("type") in ("TEXT", "MTEXT")
    )

    original_set = {t for t in original_texts if t}
    graph_set = set(graph_texts)
    newly = sorted(graph_set - original_set)
    # Friendly labels for newly visible
    newly_labels = []
    seen_lab: Set[str] = set()
    for t in newly:
        lab = _classify_label(t) or t[:40]
        if lab not in seen_lab:
            newly_labels.append(lab)
            seen_lab.add(lab)

    # Validation flags from graph semantics
    flags = {
        "top_bar_callout": False,
        "side_face": False,
        "ld": False,
        "stirrup": False,
        "physical_bar_chain": False,
        "leader_chain": False,
        "multi_leader": False,
        "semantics_connected": False,
    }
    for t in graph_texts:
        lab = _classify_label(t)
        if lab == "Top/Long Bar":
            flags["top_bar_callout"] = True
        if lab == "Side Face":
            flags["side_face"] = True
        if lab == "Ld":
            flags["ld"] = True
        if lab == "Stirrup":
            flags["stirrup"] = True

    n_bars = sum(1 for n in nodes if n.get("type") == "PhysicalBar")
    n_leaders = sum(1 for n in nodes if n.get("type") == "Leader")
    flags["physical_bar_chain"] = n_bars > 0
    chain_count = sum(
        1
        for e in edges
        if e.get("type") == "ATTACHED_TO"
        and any(
            ee.get("source_id") == e.get("target_id")
            and ee.get("type") == "POINTS_TO"
            for ee in edges
        )
    )
    flags["leader_chain"] = chain_count >= 1
    flags["multi_leader"] = chain_count >= 2

    # All semantic nodes have INTERPRETS → annotation
    sem_nodes = [
        n
        for n in nodes
        if n.get("type")
        in (
            "SemanticFact",
            "DevelopmentLength",
            "SideFaceReinforcement",
            "StirrupNote",
            "SpacerBar",
        )
    ]
    connected = 0
    for s in sem_nodes:
        if any(
            e.get("source_id") == s["id"] and e.get("type") == "INTERPRETS"
            for e in edges
        ):
            connected += 1
    flags["semantics_connected"] = (
        connected == len(sem_nodes) and len(sem_nodes) > 0
    )

    # Beam-specific expected checks (only require what's on the drawing)
    required = ["top_bar_callout", "stirrup", "physical_bar_chain", "leader_chain", "semantics_connected"]
    # Side-face / Ld only required if present in graph texts
    if flags["side_face"] or any("SIDE FACE" in t for t in graph_texts):
        required.append("side_face")
    if flags["ld"] or any(re.search(r"\bLD\b", t) for t in graph_texts):
        required.append("ld")
    if flags["multi_leader"] or chain_count >= 2:
        required.append("multi_leader")

    missing_checks = [k for k in required if not flags.get(k)]
    validation = "PASS" if not missing_checks else "FAIL"

    return {
        "beam": beam_id,
        "model_version": MODEL_VERSION,
        "original_annotations": max(len(original_set), owned_text_count),
        "graph_annotations": len(graph_anns),
        "original_texts": sorted(original_set),
        "graph_texts": graph_texts,
        "newly_visible": newly_labels,
        "newly_visible_raw": newly,
        "missing": missing_checks,
        "validation": validation,
        "flags": flags,
        "leader_bar_chains": chain_count,
        "physical_bars": n_bars,
        "leaders": n_leaders,
        "overlay_counts": overlay_counts or {},
        "semantic_count": len(sem_nodes),
        "semantics_connected": connected,
    }


def write_difference_report(report: Dict[str, Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
