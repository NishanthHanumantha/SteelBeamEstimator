"""Package refined visual evidence for one frozen P2.5.2 Vision candidate."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP250_beam_evidence_crop_qa.renderer import render_engineering_crop

from .config import (
    CROP_BEAM_CONTEXT_REFINED,
    CROP_LOCAL_REFINED,
    MODEL_VERSION,
    PHASE_ID,
    PROVENANCE_P250,
    PROVENANCE_P252,
    PROVENANCE_P2521,
    READABILITY_REVIEW_REQUIRED,
)
from .refine import select_best_crop

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def load_evidence(p250_beams_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = Path(p250_beams_root) / beam_id / "evidence.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _preserve_originals(
    *,
    out_dir: Path,
    p252_candidate_dir: Path,
    p250_beam_dir: Path,
) -> Dict[str, Any]:
    """Copy original P252 / P250 visuals without overwriting them in-place."""
    provenance = out_dir / "provenance"
    p252_dir = provenance / "P252_EVIDENCE"
    p250_dir = provenance / "ORIGINAL_P250_EVIDENCE"
    p252_dir.mkdir(parents=True, exist_ok=True)
    p250_dir.mkdir(parents=True, exist_ok=True)

    copied = {"p252": [], "p250": []}
    for name in ("local_crop.png", "beam_context_crop.png", "evidence_overlay.png", "manifest.json"):
        src = p252_candidate_dir / name
        if src.exists():
            dst = p252_dir / name
            shutil.copy2(src, dst)
            copied["p252"].append(str(dst))
    for name in ("engineering_crop.png", "evidence_overlay.png", "evidence.json"):
        src = p250_beam_dir / name
        if src.exists():
            dst = p250_dir / name
            shutil.copy2(src, dst)
            copied["p250"].append(str(dst))
    return {
        "labels": [PROVENANCE_P250, PROVENANCE_P252, PROVENANCE_P2521],
        "copied": copied,
    }


def refine_and_package_candidate(
    *,
    p252_manifest: Dict[str, Any],
    p250_beams_root: Path,
    p252_candidates_root: Path,
    out_candidates_root: Path,
    engine_root: Path,
    dxf_path: Path,
) -> Dict[str, Any]:
    """
    Refine local + beam-context crops for one ACTIVE Vision candidate.
    Does not alter P2.5.2 selection / classification.
    """
    cid = p252_manifest["candidate_id"]
    beam_id = p252_manifest["beam_id"]
    aid = p252_manifest.get("annotation_id")
    out_dir = Path(out_candidates_root) / cid.replace("::", "__")
    out_dir.mkdir(parents=True, exist_ok=True)

    p252_dir = Path(p252_candidates_root) / cid.replace("::", "__")
    p250_dir = Path(p250_beams_root) / beam_id
    evidence = load_evidence(p250_beams_root, beam_id)
    provenance = _preserve_originals(
        out_dir=out_dir, p252_candidate_dir=p252_dir, p250_beam_dir=p250_dir
    )

    if evidence is None or not aid:
        result = {
            "candidate_id": cid,
            "beam_id": beam_id,
            "annotation_id": aid,
            "raw_text": p252_manifest.get("raw_text"),
            "outcome": p252_manifest.get("outcome"),
            "candidate_priority": p252_manifest.get("candidate_priority"),
            "success": False,
            "overall_readability": READABILITY_REVIEW_REQUIRED,
            "error": "missing_evidence_or_annotation",
            "provenance": provenance,
        }
        _dump(out_dir / "refinement_manifest.json", result)
        return result

    local_sel = select_best_crop(
        evidence, annotation_id=str(aid), crop_kind=CROP_LOCAL_REFINED
    )
    ctx_sel = select_best_crop(
        evidence, annotation_id=str(aid), crop_kind=CROP_BEAM_CONTEXT_REFINED
    )

    owned = list(evidence.get("owned_geometry") or [])
    render_meta = {}

    def _render(sel: Dict[str, Any], filename: str) -> Dict[str, Any]:
        bbox = sel.get("crop_bbox")
        out_path = out_dir / filename
        if not bbox or len(bbox) < 4:
            return {"success": False, "error": "missing_crop_bbox", "path": str(out_path)}
        extent = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
        meta = render_engineering_crop(
            engine_root=Path(engine_root),
            dxf_path=Path(dxf_path),
            extent=extent,
            out_path=out_path,
            owned_geometry=owned,
            evidence=evidence,
        )
        return meta

    local_render = _render(local_sel, "local_refined.png")
    ctx_render = _render(ctx_sel, "beam_context_refined.png")
    render_meta = {"local_refined": local_render, "beam_context_refined": ctx_render}

    # Optional: also copy original P252 local as side-by-side reference at top level
    src_local = p252_dir / "local_crop.png"
    if src_local.exists():
        shutil.copy2(src_local, out_dir / "local_original_p252.png")
    src_ctx = p252_dir / "beam_context_crop.png"
    if src_ctx.exists():
        shutil.copy2(src_ctx, out_dir / "beam_context_original_p252.png")

    def _crop_block(sel: Dict[str, Any], render: Dict[str, Any], crop_type: str) -> Dict[str, Any]:
        selected = sel.get("selected") or {}
        return {
            "crop_type": crop_type,
            "provenance": PROVENANCE_P2521,
            "refinement_iteration": sel.get("refinement_iteration"),
            "strategy": sel.get("strategy"),
            "crop_bbox": sel.get("crop_bbox"),
            "source_coordinates": {
                "extent_mm": sel.get("crop_bbox"),
                "dxf_xlim": render.get("dxf_xlim"),
                "dxf_ylim": render.get("dxf_ylim"),
            },
            "readability_status": sel.get("readability_status"),
            "readability": (selected.get("readability") or {}),
            "metrics": (selected.get("metrics") or {}),
            "iterations_evaluated": [
                {
                    "iteration": it.get("iteration"),
                    "strategy": it.get("strategy"),
                    "crop_bbox": it.get("crop_bbox"),
                    "readability_status": (it.get("readability") or {}).get(
                        "readability_status"
                    ),
                }
                for it in (sel.get("iterations") or [])
            ],
            "render": {
                "success": render.get("success"),
                "path": render.get("path"),
                "img_w": render.get("img_w"),
                "img_h": render.get("img_h"),
                "error": render.get("error"),
            },
            "collected_geometry": sel.get("collected"),
        }

    local_block = _crop_block(local_sel, local_render, CROP_LOCAL_REFINED)
    ctx_block = _crop_block(ctx_sel, ctx_render, CROP_BEAM_CONTEXT_REFINED)

    # Overall = worse of the two
    from .readability import overall_candidate_readability

    overall = overall_candidate_readability(
        local_block.get("readability_status") or READABILITY_REVIEW_REQUIRED,
        ctx_block.get("readability_status") or READABILITY_REVIEW_REQUIRED,
    )

    result = {
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
        "candidate_id": cid,
        "beam_id": beam_id,
        "annotation_id": aid,
        "raw_text": p252_manifest.get("raw_text"),
        "normalized_text": p252_manifest.get("normalized_text"),
        "outcome": p252_manifest.get("outcome"),  # frozen from P252
        "candidate_priority": p252_manifest.get("candidate_priority"),
        "candidate_reason_codes": p252_manifest.get("candidate_reason_codes"),
        "p252_crop_qa_status": p252_manifest.get("crop_qa_status"),
        "p252_crop_bounds": p252_manifest.get("crop_bounds"),
        "success": bool(local_render.get("success") and ctx_render.get("success")),
        "overall_readability": overall,
        "local_refined": local_block,
        "beam_context_refined": ctx_block,
        "provenance": provenance,
        "claude_calls": 0,
        "engineering_changes": "NONE",
    }
    _dump(out_dir / "refinement_manifest.json", result)
    _dump(
        out_dir / "readability_qa.json",
        {
            "candidate_id": cid,
            "overall_readability": overall,
            "local": local_block.get("readability"),
            "beam_context": ctx_block.get("readability"),
            "local_metrics": local_block.get("metrics"),
            "beam_context_metrics": ctx_block.get("metrics"),
        },
    )
    return result


__all__ = ["refine_and_package_candidate", "load_evidence"]
