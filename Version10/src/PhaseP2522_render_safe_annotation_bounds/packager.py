"""Package render-safe crops for frozen P2.5.2.1 active candidates."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    CROP_BEAM_CONTEXT_RENDER_SAFE,
    CROP_LOCAL_RENDER_SAFE,
    MODEL_VERSION,
    PHASE_ID,
    PROVENANCE_P2521,
    PROVENANCE_P2522,
    READABILITY_PASS,
    READABILITY_PARTIAL,
    READABILITY_REVIEW,
)
from .geometry_safe import as_bbox
from .refine_safe import refine_render_safe_crop

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


def _overall(a: str, b: str) -> str:
    order = {
        READABILITY_PASS: 3,
        READABILITY_PARTIAL: 2,
        READABILITY_REVIEW: 1,
        "READABILITY_FAIL": 0,
    }
    return a if order.get(a, -1) <= order.get(b, -1) else b


def package_render_safe_candidate(
    *,
    p2521_manifest: Dict[str, Any],
    p250_beams_root: Path,
    p2521_candidates_root: Path,
    out_candidates_root: Path,
    engine_root: Path,
    dxf_path: Path,
) -> Dict[str, Any]:
    cid = p2521_manifest["candidate_id"]
    beam_id = p2521_manifest["beam_id"]
    aid = p2521_manifest.get("annotation_id")
    out_dir = Path(out_candidates_root) / cid.replace("::", "__")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Preserve P2521 outputs
    prov = out_dir / "provenance" / "P2521_REFINED_EVIDENCE"
    prov.mkdir(parents=True, exist_ok=True)
    src_dir = Path(p2521_candidates_root) / cid.replace("::", "__")
    copied = []
    for name in (
        "local_refined.png",
        "beam_context_refined.png",
        "refinement_manifest.json",
        "readability_qa.json",
        "local_original_p252.png",
        "beam_context_original_p252.png",
    ):
        src = src_dir / name
        if src.exists():
            dst = prov / name
            shutil.copy2(src, dst)
            copied.append(str(dst))

    evidence = load_p250_evidence(p250_beams_root, beam_id)
    rejected = _rejected_included(evidence)
    owned = list((evidence or {}).get("owned_geometry") or [])

    local_block_src = p2521_manifest.get("local_refined") or {}
    ctx_block_src = p2521_manifest.get("beam_context_refined") or {}
    collected = local_block_src.get("collected_geometry") or {}
    ann_bbox = as_bbox(collected.get("annotation_bbox"))
    beam_bbox = as_bbox(collected.get("beam_bbox"))
    leaders = [as_bbox(b) for b in (collected.get("leader_bboxes") or [])]
    leaders = [b for b in leaders if b]

    local_extent = as_bbox(local_block_src.get("crop_bbox"))
    ctx_extent = as_bbox(ctx_block_src.get("crop_bbox"))
    if not local_extent or not ctx_extent:
        result = {
            "candidate_id": cid,
            "beam_id": beam_id,
            "annotation_id": aid,
            "success": False,
            "error": "missing_p2521_crop_bbox",
            "overall_readability": READABILITY_REVIEW,
        }
        _dump(out_dir / "manifest.json", result)
        return result

    local_res = refine_render_safe_crop(
        initial_extent=local_extent,
        out_path=out_dir / "local_render_safe.png",
        engine_root=engine_root,
        dxf_path=dxf_path,
        annotation_bbox=ann_bbox,
        leader_bboxes=leaders,
        beam_bbox=beam_bbox,
        owned_geometry=owned,
        evidence=evidence,
        rejected_included=rejected,
    )
    ctx_res = refine_render_safe_crop(
        initial_extent=ctx_extent,
        out_path=out_dir / "beam_context_render_safe.png",
        engine_root=engine_root,
        dxf_path=dxf_path,
        annotation_bbox=ann_bbox,
        leader_bboxes=leaders,
        beam_bbox=beam_bbox,
        owned_geometry=owned,
        evidence=evidence,
        rejected_included=rejected,
    )

    def _block(res: Dict[str, Any], crop_type: str, before: Any) -> Dict[str, Any]:
        assess = res.get("assessment") or {}
        return {
            "crop_type": crop_type,
            "provenance": PROVENANCE_P2522,
            "initial_crop_bbox": res.get("initial_crop_bbox"),
            "crop_bbox": res.get("crop_bbox"),
            "p2521_crop_bbox": list(before) if before else None,
            "iterations_used": res.get("iterations_used"),
            "hit_max_iterations": res.get("hit_max_iterations"),
            "render_safety_refined": res.get("render_safety_refined"),
            "total_expansion_mm": res.get("total_expansion_mm"),
            "max_side_expansion_mm": res.get("max_side_expansion_mm"),
            "geometric_containment": res.get("geometric_containment"),
            "render_safe": res.get("render_safe"),
            "readability_status": res.get("readability_status"),
            "is_extreme": res.get("is_extreme"),
            "vertical_side": assess.get("vertical_side"),
            "margins_px": assess.get("margins_px"),
            "annotation_pixel_bbox": assess.get("annotation_pixel_bbox"),
            "leader_pixel_bbox": assess.get("leader_pixel_bbox"),
            "flags": assess.get("flags"),
            "history": res.get("history"),
            "render": res.get("render"),
        }

    local_block = _block(local_res, CROP_LOCAL_RENDER_SAFE, local_extent)
    ctx_block = _block(ctx_res, CROP_BEAM_CONTEXT_RENDER_SAFE, ctx_extent)
    overall = _overall(
        local_block.get("readability_status") or READABILITY_REVIEW,
        ctx_block.get("readability_status") or READABILITY_REVIEW,
    )

    result = {
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
        "candidate_id": cid,
        "beam_id": beam_id,
        "annotation_id": aid,
        "raw_text": p2521_manifest.get("raw_text"),
        "normalized_text": p2521_manifest.get("normalized_text"),
        "outcome": p2521_manifest.get("outcome"),
        "candidate_priority": p2521_manifest.get("candidate_priority"),
        "candidate_reason_codes": p2521_manifest.get("candidate_reason_codes"),
        "success": bool(local_res.get("success") and ctx_res.get("success")),
        "overall_readability": overall,
        "rejected_evidence_included": rejected,
        "local_render_safe": local_block,
        "beam_context_render_safe": ctx_block,
        "provenance": {
            "labels": [PROVENANCE_P2521, PROVENANCE_P2522],
            "p2521_copied": copied,
        },
        "claude_calls": 0,
        "engineering_changes": "NONE",
    }
    _dump(out_dir / "manifest.json", result)
    return result


__all__ = ["package_render_safe_candidate", "load_p250_evidence"]
