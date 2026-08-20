"""B.3 overlay pipeline. Frozen-good beams are never rerendered. No beam-ID crop rules."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

from PhaseP2610B2_render_quality_directional_recovery.geometry import as_extent, intersect
from PhaseP2610B2_render_quality_directional_recovery.quality import (
    STATUS_BLACK,
    STATUS_EMPTY,
    STATUS_LOW_INFO,
    STATUS_MISSING,
    validate_render,
)
from PhaseP2610B2_render_quality_directional_recovery.timing import Timer

from .anchor import build_target_anchor
from .candidates import generate_candidates
from .config import CLASS_FROZEN, CLASS_REVIEW, CLASS_TARGET, OCCUPANCY_PAD_MM
from .context_builder import build_context_envelope
from .gate import evaluate_candidate, should_replace

RenderFn = Callable[..., Dict[str, Any]]
_BLANK = {STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING}


def file_fingerprint(path: Optional[Path]) -> Optional[str]:
    if path is None or not Path(path).exists():
        return None
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if Path(src).resolve() == Path(dst).resolve():
        return
    shutil.copy2(src, dst)


def freeze_baseline(
    *,
    beam_id: str,
    classification: str,
    reasons: Sequence[str],
    b1: Dict[str, Any],
    b2: Optional[Dict[str, Any]],
    ctx_quality: Dict[str, Any],
    det_quality: Dict[str, Any],
) -> Dict[str, Any]:
    ctx = Path(str(b1.get("context_crop_path") or ""))
    det = Path(str(b1.get("detail_crop_path") or ""))
    return {
        "beam_id": beam_id,
        "baseline_classification": classification,
        "frozen_good": classification == CLASS_FROZEN,
        "target_recovery": classification == CLASS_TARGET,
        "review_only": classification == CLASS_REVIEW,
        "classification_reasons": list(reasons),
        "baseline_context_source": "P2610B1",
        "baseline_detail_source": "P2610B1",
        "b1_context_path": str(ctx) if ctx.exists() else None,
        "b1_detail_path": str(det) if det.exists() else None,
        "b1_context_sha256": file_fingerprint(ctx if ctx.exists() else None),
        "b1_detail_sha256": file_fingerprint(det if det.exists() else None),
        "b1_context_bounds": b1.get("context_bounds"),
        "b1_detail_bounds": b1.get("detail_bounds"),
        "b2_usable": None if b2 is None else b2.get("final_vision_usable"),
        "target_geometry_bounds": None,
        "primary_direction": None,
        "target_start_end_coverage": None,
        "candidate_count": 0,
        "candidate_reason_codes": [],
        "selected_context_source": "P2610B1",
        "selected_detail_source": "P2610B1",
        "b3_action": "unchanged",
        "final_context_status": ctx_quality.get("primary_status"),
        "final_detail_status": det_quality.get("primary_status"),
        "final_reason": "FROZEN_BASELINE_REUSED" if classification == CLASS_FROZEN else "REVIEW_BASELINE_PRESERVED",
        "rerendered": False,
        "context_improved": False,
        "detail_improved": False,
        "fallback_to_baseline": False,
        "final_context_path": str(ctx) if ctx.exists() else None,
        "final_detail_path": str(det) if det.exists() else None,
        "selected_context_sha256": file_fingerprint(ctx if ctx.exists() else None),
        "selected_detail_sha256": file_fingerprint(det if det.exists() else None),
    }


def recover_beam(
    *,
    beam_id: str,
    msp: Any,
    mark: Dict[str, Any],
    titles: list,
    dxf_path: Path,
    out_root: Path,
    render_fn: RenderFn,
    classification: str,
    reasons: Sequence[str],
    b1: Dict[str, Any],
    b2: Optional[Dict[str, Any]],
    ctx_quality: Dict[str, Any],
    det_quality: Dict[str, Any],
) -> Dict[str, Any]:
    rec = freeze_baseline(
        beam_id=beam_id,
        classification=classification,
        reasons=reasons,
        b1=b1,
        b2=b2,
        ctx_quality=ctx_quality,
        det_quality=det_quality,
    )
    rec["target_recovery"] = True
    rec["frozen_good"] = False
    rec["review_only"] = False
    b1_ctx = Path(str(b1.get("context_crop_path") or ""))
    b1_det = Path(str(b1.get("detail_crop_path") or ""))
    b2_ctx = None
    if b2 and b2.get("context_crop_path"):
        p = Path(str(b2["context_crop_path"]))
        if p.exists():
            b2_ctx = p
    vis = out_root / "review" / beam_id
    if b1_ctx.exists():
        _copy(b1_ctx, vis / "baseline" / "context.png")
    if b1_det.exists():
        _copy(b1_det, vis / "baseline" / "detail.png")
    if b2_ctx:
        _copy(b2_ctx, vis / "b2" / "context.png")

    with Timer() as t_anchor:
        anchor = build_target_anchor(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
    envelope = build_context_envelope(anchor)
    rec["target_geometry_bounds"] = list(anchor["core"])
    rec["primary_direction"] = anchor["orientation"]
    rec["anchor_build_s"] = t_anchor.seconds
    rec["owned_evidence_count"] = anchor.get("owned_evidence_count")

    baseline_extent = b1.get("context_bounds") or envelope["extent"]
    baseline_eval = evaluate_candidate(extent=baseline_extent, anchor=anchor, quality=ctx_quality)
    rec["target_start_end_coverage"] = {
        "start_inside": baseline_eval["start_inside"],
        "end_inside": baseline_eval["end_inside"],
        "coverage": baseline_eval["target_coverage"],
        "occupancy": baseline_eval["target_occupancy"],
        "score": baseline_eval["score"],
    }

    cands = generate_candidates(
        anchor=anchor,
        context_envelope=envelope,
        baseline_extent=baseline_extent,
        baseline_quality=ctx_quality,
    )
    rec["candidate_count"] = len(cands)
    rec["candidate_reason_codes"] = [c["reason"] for c in cands]
    evaluations = []
    best = {"eval": baseline_eval, "path": b1_ctx if b1_ctx.exists() else None, "extent": baseline_extent, "source": "P2610B1", "reason": "BASELINE"}
    if b2 and b2.get("final_context_bounds"):
        b2q = (b2.get("context_diagnostic") or {}) if isinstance(b2.get("context_diagnostic"), dict) else ctx_quality
        b2_eval = evaluate_candidate(extent=b2["final_context_bounds"], anchor=anchor, quality=b2q)
        if should_replace(best["eval"], b2_eval, margin=0.0) or (
            b2_eval.get("score", 0) >= best["eval"].get("score", 0) and b2.get("final_vision_usable")
        ):
            if b2_eval.get("score", 0) > best["eval"].get("score", 0):
                best = {
                    "eval": b2_eval,
                    "path": b2_ctx,
                    "extent": b2["final_context_bounds"],
                    "source": "P2610B2",
                    "reason": "P2610B2_RETAINED",
                }

    for i, cand in enumerate(cands, start=1):
        out_png = vis / "b3_candidate" / f"context_{i}_{cand['reason']}.png"
        render_fn(dxf_path=dxf_path, output_path=out_png, extent=cand["extent"], crop_type="context")
        q = validate_render(out_png, extent=cand["extent"], crop_type="context")
        ev = evaluate_candidate(extent=cand["extent"], anchor=anchor, quality=q)
        row = {"index": i, **cand, "quality": q.get("primary_status"), "eval": ev}
        evaluations.append(row)
        if should_replace(best["eval"], ev):
            best = {"eval": ev, "path": out_png, "extent": cand["extent"], "source": "P2610B3", "reason": cand["reason"]}

    rec["candidate_evaluation"] = [
        {"index": r["index"], "reason": r["reason"], "extent": r["extent"], "quality": r["quality"], **r["eval"]}
        for r in evaluations
    ]
    rec["rerendered"] = True
    if best["source"] == "P2610B3":
        rec["b3_action"] = "improved"
        rec["context_improved"] = True
        rec["selected_context_source"] = "P2610B3"
        rec["final_reason"] = best["reason"]
        if best["path"]:
            _copy(Path(best["path"]), vis / "selected" / "context.png")
            rec["final_context_path"] = str(vis / "selected" / "context.png")
            rec["final_context_status"] = validate_render(best["path"], extent=best["extent"], crop_type="context").get("primary_status")
    elif best["source"] == "P2610B2":
        rec["b3_action"] = "unchanged"
        rec["selected_context_source"] = "P2610B2"
        rec["final_reason"] = "P2610B2_RETAINED"
        rec["final_context_path"] = str(b2_ctx) if b2_ctx else rec["b1_context_path"]
        rec["fallback_to_baseline"] = True
    else:
        rec["b3_action"] = "fallback_to_baseline"
        rec["selected_context_source"] = "P2610B1"
        rec["final_reason"] = "FALLBACK_TO_P2610B1"
        rec["fallback_to_baseline"] = True
        rec["final_context_path"] = rec["b1_context_path"]

    rec["final_context_bounds"] = list(as_extent(best["extent"]))
    rec["selected_context_sha256"] = file_fingerprint(Path(rec["final_context_path"]) if rec.get("final_context_path") else None)

    det_action = "unchanged"
    det_src = "P2610B1"
    det_path = b1_det if b1_det.exists() else None
    det_status = det_quality.get("primary_status")
    det_bounds = b1.get("detail_bounds")
    det_ok = str(det_status) not in _BLANK
    if det_bounds and len(det_bounds) == 4:
        if intersect(anchor["core"], det_bounds) is None:
            det_ok = False
    if not det_ok:
        ctx_e = as_extent(best["extent"])
        core = as_extent(anchor["core"])
        raw = (
            core[0] - OCCUPANCY_PAD_MM,
            core[1] - OCCUPANCY_PAD_MM,
            core[2] + OCCUPANCY_PAD_MM,
            core[3] + OCCUPANCY_PAD_MM,
        )
        det_e = (
            max(raw[0], ctx_e[0]),
            max(raw[1], ctx_e[1]),
            min(raw[2], ctx_e[2]),
            min(raw[3], ctx_e[3]),
        )
        if det_e[2] > det_e[0] + 80 and det_e[3] > det_e[1] + 80:
            det_png = vis / "b3_candidate" / "detail_occupancy.png"
            render_fn(dxf_path=dxf_path, output_path=det_png, extent=det_e, crop_type="detail")
            dq = validate_render(det_png, extent=det_e, crop_type="detail")
            if str(dq.get("primary_status")) not in _BLANK:
                det_action = "improved"
                det_src = "P2610B3"
                det_path = det_png
                det_status = dq.get("primary_status")
                rec["detail_improved"] = True
                _copy(det_png, vis / "selected" / "detail.png")
    rec["b3_detail_action"] = det_action
    rec["selected_detail_source"] = det_src
    rec["final_detail_status"] = det_status
    rec["final_detail_path"] = str(det_path) if det_path else rec.get("b1_detail_path")
    rec["selected_detail_sha256"] = file_fingerprint(Path(rec["final_detail_path"]) if rec.get("final_detail_path") else None)
    rec["context_first"] = True
    return rec


__all__ = ["file_fingerprint", "freeze_baseline", "recover_beam"]
