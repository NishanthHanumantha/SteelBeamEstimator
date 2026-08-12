"""Package target-beam-complete crops from frozen P2.5.2.2 candidates."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    CROP_BEAM_CONTEXT_TARGET_COMPLETE,
    CROP_LOCAL_TARGET_COMPLETE,
    MODEL_VERSION,
    PHASE_ID,
    PROVENANCE_P2522,
    PROVENANCE_P2523,
)
from .geometry_complete import as_bbox, collect_critical_geometry
from .refine_complete import refine_target_beam_complete

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def load_p250_evidence(p250_beams_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = Path(p250_beams_root) / beam_id / "evidence.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _rejected_included(evidence: Optional[Dict[str, Any]]) -> bool:
    if not evidence:
        return False
    excluded = evidence.get("excluded_rejected_evidence") or {}
    rejected_bars = set(excluded.get("bars") or [])
    reinf = {str(b.get("reinforcement_id")) for b in (evidence.get("reinforcement") or [])}
    return bool(rejected_bars & reinf)


def _owned_and_reinf_boxes(
    evidence: Optional[Dict[str, Any]],
    *,
    center_x: float,
    center_y: float,
    described_ids: Optional[List[str]] = None,
) -> tuple:
    owned: List = []
    reinf: List = []
    described = set(described_ids or [])
    for og in (evidence or {}).get("owned_geometry") or []:
        bb = as_bbox(og.get("bbox"))
        if not bb:
            continue
        mid = (0.5 * (bb[0] + bb[2]), 0.5 * (bb[1] + bb[3]))
        if abs(mid[0] - center_x) <= 4500 and abs(mid[1] - center_y) <= 4500:
            owned.append(bb)
    for bar in (evidence or {}).get("reinforcement") or []:
        rid = str(bar.get("reinforcement_id") or "")
        bb = as_bbox(bar.get("bbox"))
        if not bb:
            continue
        if described and rid in described:
            reinf.append(bb)
            continue
        mid = (0.5 * (bb[0] + bb[2]), 0.5 * (bb[1] + bb[3]))
        if abs(mid[0] - center_x) <= 2500 and abs(mid[1] - center_y) <= 2500:
            reinf.append(bb)
    return owned, reinf


def _overall(a: str, b: str) -> str:
    order = {"PASS": 3, "PARTIAL": 2, "REVIEW": 1, "FAIL": 0}
    return a if order.get(a, -1) <= order.get(b, -1) else b


def package_target_complete_candidate(
    *,
    p2522_manifest: Dict[str, Any],
    p2521_collected: Dict[str, Any],
    p250_beams_root: Path,
    p2522_candidates_root: Path,
    out_candidates_root: Path,
    engine_root: Path,
    dxf_path: Path,
) -> Dict[str, Any]:
    cid = p2522_manifest["candidate_id"]
    beam_id = p2522_manifest["beam_id"]
    aid = p2522_manifest.get("annotation_id")
    out_dir = Path(out_candidates_root) / cid.replace("::", "__")
    out_dir.mkdir(parents=True, exist_ok=True)

    prov = out_dir / "provenance"
    prov.mkdir(parents=True, exist_ok=True)
    _dump(prov / "p2522_manifest.json", p2522_manifest)
    src_dir = Path(p2522_candidates_root) / cid.replace("::", "__")
    for name in ("local_render_safe.png", "beam_context_render_safe.png", "manifest.json"):
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, prov / name)

    evidence = load_p250_evidence(p250_beams_root, beam_id)
    rejected = _rejected_included(evidence)
    owned_geom = list((evidence or {}).get("owned_geometry") or [])

    ann_bbox = as_bbox(p2521_collected.get("annotation_bbox"))
    beam_bbox = as_bbox(p2521_collected.get("beam_bbox"))
    leaders = [b for b in (as_bbox(x) for x in (p2521_collected.get("leader_bboxes") or [])) if b]
    cx = float(p2521_collected.get("center_x") or (0.5 * (ann_bbox[0] + ann_bbox[2]) if ann_bbox else 0))
    cy = float(p2521_collected.get("center_y") or (0.5 * (ann_bbox[1] + ann_bbox[3]) if ann_bbox else 0))
    owned_boxes, reinf_boxes = _owned_and_reinf_boxes(
        evidence, center_x=cx, center_y=cy, described_ids=p2521_collected.get("described_ids")
    )

    local_crit = collect_critical_geometry(
        annotation_bbox=ann_bbox,
        beam_bbox=beam_bbox,
        leader_bboxes=leaders,
        owned_bboxes=owned_boxes,
        reinforcement_bboxes=reinf_boxes,
        center_x=cx,
        center_y=cy,
        context=False,
    )
    ctx_crit = collect_critical_geometry(
        annotation_bbox=ann_bbox,
        beam_bbox=beam_bbox,
        leader_bboxes=leaders,
        owned_bboxes=owned_boxes,
        reinforcement_bboxes=reinf_boxes,
        center_x=cx,
        center_y=cy,
        context=True,
    )

    local_extent = as_bbox((p2522_manifest.get("local_render_safe") or {}).get("crop_bbox"))
    ctx_extent = as_bbox((p2522_manifest.get("beam_context_render_safe") or {}).get("crop_bbox"))
    if not local_extent or not ctx_extent:
        result = {
            "candidate_id": cid,
            "beam_id": beam_id,
            "success": False,
            "error": "missing_p2522_crop_bbox",
            "overall_completeness": "FAIL",
        }
        _dump(out_dir / "manifest.json", result)
        return result

    local_res = refine_target_beam_complete(
        initial_extent=local_extent,
        out_path=out_dir / "local_target_complete.png",
        engine_root=engine_root,
        dxf_path=dxf_path,
        critical_beam_bbox=local_crit.get("critical_beam_bbox"),
        annotation_bbox=ann_bbox,
        leader_bboxes=leaders,
        owned_bboxes=owned_boxes,
        reinforcement_bboxes=reinf_boxes,
        beam_bbox=beam_bbox,
        owned_geometry=owned_geom,
        evidence=evidence,
        rejected_included=rejected,
    )
    ctx_res = refine_target_beam_complete(
        initial_extent=ctx_extent,
        out_path=out_dir / "beam_context_target_complete.png",
        engine_root=engine_root,
        dxf_path=dxf_path,
        critical_beam_bbox=ctx_crit.get("critical_beam_bbox"),
        annotation_bbox=ann_bbox,
        leader_bboxes=leaders,
        owned_bboxes=owned_boxes,
        reinforcement_bboxes=reinf_boxes,
        beam_bbox=beam_bbox,
        owned_geometry=owned_geom,
        evidence=evidence,
        rejected_included=rejected,
    )

    def _block(res: Dict[str, Any], crop_type: str, before: Any, crit: Dict[str, Any]) -> Dict[str, Any]:
        assess = res.get("assessment") or {}
        return {
            "crop_type": crop_type,
            "provenance": PROVENANCE_P2523,
            "previous_crop_bbox": list(before) if before else None,
            "final_crop_bbox": res.get("crop_bbox"),
            "target_beam_bbox": list(beam_bbox) if beam_bbox else None,
            "critical_beam_bbox": list(crit["critical_beam_bbox"]) if crit.get("critical_beam_bbox") else None,
            "target_beam_pixel_bbox": assess.get("target_beam_pixel_bbox"),
            "target_beam_geometry_present": assess.get("target_beam_geometry_present"),
            "target_beam_geometry_rendered": assess.get("target_beam_geometry_rendered"),
            "annotation_visible": assess.get("annotation_visible"),
            "leader_visible": assess.get("leader_visible"),
            "reinforcement_visible": assess.get("reinforcement_visible"),
            "beam_edge_margins_px": assess.get("beam_edge_margins_px"),
            "annotation_edge_margins_px": assess.get("annotation_edge_margins_px"),
            "unsafe_sides": assess.get("unsafe_sides"),
            "expansion_mm": res.get("total_expansion_mm"),
            "iterations_used": res.get("iterations_used"),
            "target_beam_visual_completeness": res.get("completeness_status"),
            "completeness_reason_codes": assess.get("reason_codes"),
            "rejected_physical_bar_excluded": assess.get("rejected_physical_bar_excluded"),
            "is_extreme": res.get("is_extreme"),
            "render_success": res.get("success"),
            "completeness_refined": res.get("completeness_refined"),
            "hit_max_iterations": res.get("hit_max_iterations"),
            "max_side_expansion_mm": res.get("max_side_expansion_mm"),
            "history": res.get("history"),
            "render": res.get("render"),
            "source_p2522_provenance": PROVENANCE_P2522,
        }

    local_block = _block(local_res, CROP_LOCAL_TARGET_COMPLETE, local_extent, local_crit)
    ctx_block = _block(ctx_res, CROP_BEAM_CONTEXT_TARGET_COMPLETE, ctx_extent, ctx_crit)
    overall = _overall(
        local_block.get("target_beam_visual_completeness") or "FAIL",
        ctx_block.get("target_beam_visual_completeness") or "FAIL",
    )

    result = {
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
        "candidate_id": cid,
        "beam_id": beam_id,
        "annotation_id": aid,
        "raw_text": p2522_manifest.get("raw_text"),
        "normalized_text": p2522_manifest.get("normalized_text"),
        "outcome": p2522_manifest.get("outcome"),
        "candidate_priority": p2522_manifest.get("candidate_priority"),
        "candidate_reason_codes": p2522_manifest.get("candidate_reason_codes"),
        "success": bool(local_res.get("success") and ctx_res.get("success")),
        "overall_completeness": overall,
        "rejected_evidence_included": rejected,
        "local_target_complete": local_block,
        "beam_context_target_complete": ctx_block,
        "claude_calls": 0,
        "engineering_changes": "NONE",
        "synthetic_geometry": "NONE",
    }
    _dump(out_dir / "manifest.json", result)
    _dump(
        out_dir / "provenance" / "completeness_diagnostics.json",
        {
            "local": local_block,
            "context": ctx_block,
            "overall": overall,
        },
    )
    _dump(prov / "source_manifest.json", {"candidate_id": cid, "source_phase": "P2.5.2.2"})
    return result


__all__ = ["package_target_complete_candidate"]
