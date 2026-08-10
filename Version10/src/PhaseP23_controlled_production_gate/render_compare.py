"""
Baseline vs controlled render comparison for affected beams.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseT181_beam_render_validation.comparison_engine import (
    make_diff_image,
    make_side_by_side,
)
from PhaseT181_beam_render_validation.ownership_renderer import render_owned_beam
from PhaseT182_adaptive_render_extent.render_extent_builder import (
    apply_extent_to_scoped_copy,
    build_render_extent,
)

from .config import MODEL_VERSION, PHASE_ID


def _file_hash(path: Path) -> Optional[str]:
    if not path or not Path(path).exists():
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _count_types(scoped: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for n in scoped.get("nodes") or []:
        t = str(n.get("type") or "Unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts


def compare_beam_renders(
    *,
    engine_root: Path,
    run_root: Path,
    output_root: Path,
    beam_id: str,
    baseline_scoped: Dict[str, Any],
    controlled_scoped: Dict[str, Any],
    render_dir: Path,
    baseline_render_src: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Write B16_baseline.png / controlled / side-by-side / diff into render_dir.
    Uses existing ownership_renderer + T182 extent builder (no parallel renderer).
    """
    render_dir = Path(render_dir)
    render_dir.mkdir(parents=True, exist_ok=True)

    baseline_png = render_dir / f"{beam_id}_baseline.png"
    controlled_png = render_dir / f"{beam_id}_controlled.png"
    side_png = render_dir / f"{beam_id}_side_by_side.png"
    diff_png = render_dir / f"{beam_id}_diff.png"

    # Baseline: prefer existing production adaptive render if available
    copied_baseline = False
    if baseline_render_src and Path(baseline_render_src).exists():
        shutil.copy2(baseline_render_src, baseline_png)
        copied_baseline = True
        base_rend = {"success": True, "source": "existing_t182_render"}
    else:
        base_extent = build_render_extent(beam_id, baseline_scoped)
        if not base_extent.get("success"):
            base_rend = {"success": False, "error": base_extent.get("error")}
        else:
            base_scoped = apply_extent_to_scoped_copy(
                baseline_scoped, base_extent["computed_render_bbox"]
            )
            base_rend = render_owned_beam(
                engine_root=engine_root,
                run_root=run_root,
                output_root=output_root,
                beam_id=beam_id,
                scoped=base_scoped,
                out_path=baseline_png,
            )

    ctrl_extent = build_render_extent(beam_id, controlled_scoped)
    if not ctrl_extent.get("success"):
        ctrl_rend = {"success": False, "error": ctrl_extent.get("error")}
    else:
        ctrl_scoped = apply_extent_to_scoped_copy(
            controlled_scoped, ctrl_extent["computed_render_bbox"]
        )
        ctrl_rend = render_owned_beam(
            engine_root=engine_root,
            run_root=run_root,
            output_root=output_root,
            beam_id=beam_id,
            scoped=ctrl_scoped,
            out_path=controlled_png,
        )

    side = {}
    diff = {}
    if baseline_png.exists() and controlled_png.exists():
        side = make_side_by_side(
            baseline_png, controlled_png, side_png, beam_id=beam_id
        )
        diff = make_diff_image(
            baseline_png, controlled_png, diff_png, beam_id=beam_id
        )

    base_types = _count_types(baseline_scoped)
    ctrl_types = _count_types(controlled_scoped)
    base_nodes = set(
        n.get("id") for n in (baseline_scoped.get("nodes") or []) if n.get("id")
    )
    ctrl_nodes = set(
        n.get("id") for n in (controlled_scoped.get("nodes") or []) if n.get("id")
    )
    newly_rendered = sorted(ctrl_nodes - base_nodes)
    removed = sorted(base_nodes - ctrl_nodes)

    leader_appeared = any(str(x).startswith("LDR::") for x in newly_rendered)
    ann_appeared = any(str(x).startswith("ANN") for x in newly_rendered)
    bar_appeared = any(str(x).startswith("BAR") for x in newly_rendered)

    # Neighbour beam IDs in newly rendered? (contamination signal)
    neighbour_leak = [
        nid
        for nid in newly_rendered
        if "::B" in str(nid) and f"::{beam_id}" not in str(nid) and "B16" not in str(nid)
    ]
    # Better: check node beam_id attribute
    neighbour_nodes = []
    for n in controlled_scoped.get("nodes") or []:
        if n.get("id") in newly_rendered and n.get("beam_id") not in (None, beam_id):
            neighbour_nodes.append(n.get("id"))

    improved = len(newly_rendered) > 0 and not neighbour_nodes and not removed
    worsened = bool(removed) or bool(neighbour_nodes)

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": beam_id,
        "baseline_render_success": bool(base_rend.get("success")) or copied_baseline,
        "controlled_render_success": bool(ctrl_rend.get("success")),
        "copied_baseline_from_production": copied_baseline,
        "paths": {
            "baseline": str(baseline_png) if baseline_png.exists() else None,
            "controlled": str(controlled_png) if controlled_png.exists() else None,
            "side_by_side": str(side_png) if side_png.exists() else None,
            "diff": str(diff_png) if diff_png.exists() else None,
        },
        "hashes": {
            "baseline": _file_hash(baseline_png),
            "controlled": _file_hash(controlled_png),
            "side_by_side": _file_hash(side_png),
            "diff": _file_hash(diff_png),
        },
        "baseline_type_counts": base_types,
        "controlled_type_counts": ctrl_types,
        "newly_rendered_entities": newly_rendered,
        "removed_entities": removed,
        "missing_expected_entities": [],
        "unexpected_entities": neighbour_nodes,
        "questions": {
            "did_missing_leader_appear": leader_appeared,
            "did_associated_annotation_appear": ann_appeared,
            "did_associated_bar_appear": bar_appeared,
            "did_unrelated_neighbour_annotations_appear": bool(neighbour_nodes),
            "did_crop_improve": improved,
            "did_crop_become_worse": worsened,
        },
        "side_by_side_meta": side,
        "diff_meta": diff,
        "neighbour_leak_ids": neighbour_leak + neighbour_nodes,
    }


def run_render_comparisons(
    *,
    engine_root: Path,
    run_root: Path,
    output_root: Path,
    affected_beams: Sequence[str],
    baseline_scoped_doc: Dict[str, Any],
    controlled_scoped_doc: Dict[str, Any],
    render_root: Path,
    baseline_render_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for bid in sorted(set(affected_beams)):
        bsc = (baseline_scoped_doc.get("by_beam") or {}).get(bid)
        csc = (controlled_scoped_doc.get("by_beam") or {}).get(bid)
        if not bsc or not csc:
            continue
        src = None
        if baseline_render_dir:
            cand = Path(baseline_render_dir) / f"{bid}_render.png"
            if cand.exists():
                src = cand
        rows.append(
            compare_beam_renders(
                engine_root=engine_root,
                run_root=run_root,
                output_root=output_root,
                beam_id=bid,
                baseline_scoped=bsc,
                controlled_scoped=csc,
                render_dir=render_root,
                baseline_render_src=src,
            )
        )
    # Hash structural render outcomes only (image bytes may vary slightly across runs)
    structural = [
        {
            "beam_id": r.get("beam_id"),
            "newly_rendered_entities": r.get("newly_rendered_entities"),
            "removed_entities": r.get("removed_entities"),
            "questions": r.get("questions"),
            "baseline_type_counts": r.get("baseline_type_counts"),
            "controlled_type_counts": r.get("controlled_type_counts"),
            "baseline_render_success": r.get("baseline_render_success"),
            "controlled_render_success": r.get("controlled_render_success"),
        }
        for r in rows
    ]
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "affected_beam_count": len(rows),
        "rows": rows,
        "render_manifest_hash": hashlib.sha256(json_bytes(structural)).hexdigest(),
        "any_neighbour_contamination": any(
            r.get("questions", {}).get("did_unrelated_neighbour_annotations_appear")
            for r in rows
        ),
        "any_crop_improved": any(
            r.get("questions", {}).get("did_crop_improve") for r in rows
        ),
    }


def json_bytes(obj: Any) -> bytes:
    import json

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
