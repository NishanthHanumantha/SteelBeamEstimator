"""Context-first staged crop pipeline. Recovery only for suspects. No beam-ID logic."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PhaseP2610B_adaptive_beam_detail_crop.envelope import adaptive_detail_extent, build_adaptive_regions

from .candidates import generate_candidate_actions
from .config import DETAIL_INSET_FRAC
from .gates import needs_recovery
from .geometry import as_extent, height, intersect, width
from .orientation import dominant_orientation
from .quality import (
    STATUS_BLACK,
    STATUS_EMPTY,
    STATUS_LOW_INFO,
    STATUS_MISSING,
    validate_render,
)
from .recovery import apply_action
from .timing import Timer

RenderFn = Callable[..., Dict[str, Any]]

_RANK = {
    STATUS_MISSING: 6,
    STATUS_EMPTY: 5,
    STATUS_BLACK: 4,
    STATUS_LOW_INFO: 3,
    "LOW_CONTEXT_QUALITY": 2,
    "BORDER_CLIPPING_SUSPECT": 1,
    "VALID": 0,
}


def _copy_png(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if Path(src).resolve() == Path(dst).resolve():
        return
    shutil.copy2(src, dst)


def derive_detail_extent(
    context_extent: Sequence[float],
    adaptive: Sequence[float],
    mark: Dict[str, Any],
) -> Tuple[float, float, float, float]:
    ctx = as_extent(context_extent)
    ad = as_extent(adaptive)
    hit = intersect(ctx, ad)
    if hit is None:
        pad_x = width(ctx) * DETAIL_INSET_FRAC
        pad_y = height(ctx) * DETAIL_INSET_FRAC
        hit = (ctx[0] + pad_x, ctx[1] + pad_y, ctx[2] - pad_x, ctx[3] - pad_y)
    mx, my = float(mark["x"]), float(mark["y"])
    xmin, ymin, xmax, ymax = hit
    xmin = min(xmin, mx - 250.0)
    xmax = max(xmax, mx + 250.0)
    ymin = min(ymin, my - 180.0)
    ymax = max(ymax, my + 400.0)
    xmin = max(xmin, ctx[0])
    ymin = max(ymin, ctx[1])
    xmax = min(xmax, ctx[2])
    ymax = min(ymax, ctx[3])
    return as_extent((xmin, ymin, xmax, ymax))


def _critical_unresolved(diag: Dict[str, Any], *, crop_type: str = "context") -> bool:
    primary = diag.get("primary_status")
    if primary in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING):
        return True
    if crop_type == "context" and list(diag.get("empty_sides") or []):
        return True
    return False


def _vision_usable(ctx: Dict[str, Any], det: Dict[str, Any]) -> bool:
    if _critical_unresolved(ctx, crop_type="context"):
        return False
    if _critical_unresolved(det, crop_type="detail"):
        return False
    return bool(ctx.get("visually_usable") and det.get("visually_usable") and ctx.get("target_visible"))


def _score(diag: Dict[str, Any]) -> Tuple[int, float]:
    return (_RANK.get(str(diag.get("primary_status")), 2), -float(diag.get("foreground_ratio") or 0.0))


def _render_one(
    *,
    render_fn: RenderFn,
    dxf_path: Path,
    output_path: Path,
    extent: Sequence[float],
    crop_type: str,
    reuse_src: Optional[Path] = None,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if reuse_src and Path(reuse_src).exists() and Path(reuse_src).stat().st_size > 200:
        _copy_png(Path(reuse_src), output_path)
        return {
            "path": str(output_path),
            "crop_type": crop_type,
            "dxf_bbox": list(as_extent(extent)),
            "reused_existing_png": True,
        }
    return render_fn(dxf_path=dxf_path, output_path=output_path, extent=extent, crop_type=crop_type)


def _try_candidates(
    *,
    beam_id: str,
    mark: Dict[str, Any],
    titles: list,
    dxf_path: Path,
    render_fn: RenderFn,
    crop_type: str,
    orientation: str,
    baseline_extent: Sequence[float],
    baseline_diag: Dict[str, Any],
    baseline_path: Path,
    out_dir: Path,
    container: Optional[Sequence[float]] = None,
) -> Tuple[Any, Dict[str, Any], List[Dict[str, Any]], Path]:
    actions = generate_candidate_actions(baseline_diag, orientation=orientation, crop_type=crop_type)
    history: List[Dict[str, Any]] = []
    best_extent = as_extent(baseline_extent)
    best_diag = baseline_diag
    best_path = baseline_path
    seen = {tuple(round(v, 1) for v in best_extent)}
    for i, action in enumerate(actions, start=1):
        nxt = apply_action(
            as_extent(baseline_extent),
            action,
            diagnostic=baseline_diag,
            mark=mark,
            titles=titles,
            crop_type=crop_type,
            container=container,
        )
        key = tuple(round(v, 1) for v in nxt)
        rec = {
            "attempt": i,
            "reason": baseline_diag.get("primary_status"),
            "orientation": orientation,
            "action": action,
            "before_bounds": list(as_extent(baseline_extent)),
            "after_bounds": list(nxt),
            "result": "PENDING",
        }
        if key in seen:
            rec["result"] = "DUPLICATE_SKIPPED"
            rec["note"] = "cache_or_duplicate_extent"
            history.append(rec)
            continue
        seen.add(key)
        cand_path = out_dir / "recovery" / f"{beam_id}_{crop_type}_a{i}.png"
        _render_one(
            render_fn=render_fn,
            dxf_path=dxf_path,
            output_path=cand_path,
            extent=nxt,
            crop_type=crop_type,
        )
        diag = validate_render(cand_path, extent=nxt, crop_type=crop_type)
        rec["result"] = diag.get("primary_status")
        history.append(rec)
        if _score(diag) < _score(best_diag):
            best_diag = diag
            best_extent = nxt
            best_path = cand_path
    return best_extent, best_diag, history, best_path


def process_beam(
    *,
    beam_id: str,
    msp: Any,
    mark: Dict[str, Any],
    titles: list,
    dxf_path: Path,
    out_root: Path,
    render_fn: RenderFn,
    reuse_initial: Optional[Dict[str, Any]] = None,
    regions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    stages: List[str] = []
    timing: Dict[str, float] = {
        "context_render_s": 0.0,
        "detail_render_s": 0.0,
        "quality_s": 0.0,
        "recovery_s": 0.0,
        "reuse_copy_s": 0.0,
    }
    reuse_initial = reuse_initial or {}
    stages.append("INITIAL_CONTEXT")
    regions = regions or build_adaptive_regions(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
    ctx_extent = as_extent(regions["context_extent"])
    adaptive = regions.get("adaptive") or {}
    orientation = dominant_orientation(
        mark=mark,
        extent=ctx_extent,
        outline=adaptive.get("outline"),
        evidence=adaptive.get("evidence"),
    )
    ctx_init_path = out_root / "context" / "initial" / f"{beam_id}.png"
    ctx_final_path = out_root / "context" / "final" / f"{beam_id}.png"
    with Timer() as t_ctx:
        ctx_render = _render_one(
            render_fn=render_fn,
            dxf_path=dxf_path,
            output_path=ctx_init_path,
            extent=ctx_extent,
            crop_type="context",
            reuse_src=reuse_initial.get("context"),
        )
    if ctx_render.get("reused_existing_png"):
        timing["reuse_copy_s"] += t_ctx.seconds
    else:
        timing["context_render_s"] += t_ctx.seconds
    stages.append("VALIDATE_CONTEXT")
    with Timer() as t_q:
        ctx_diag = validate_render(ctx_init_path, extent=ctx_extent, crop_type="context")
    timing["quality_s"] += t_q.seconds
    ctx_diag["dominant_orientation"] = orientation
    ctx_initial_status = ctx_diag.get("primary_status")
    recover_ctx, ctx_reason = needs_recovery(ctx_diag, crop_type="context", orientation=orientation)
    ctx_valid_before = not recover_ctx
    ctx_history: List[Dict[str, Any]] = []
    ctx_current = ctx_extent
    if recover_ctx:
        stages.append("RECOVER_CONTEXT")
        with Timer() as t_rec:
            ctx_current, ctx_diag, ctx_history, best_path = _try_candidates(
                beam_id=beam_id,
                mark=mark,
                titles=titles,
                dxf_path=dxf_path,
                render_fn=render_fn,
                crop_type="context",
                orientation=orientation,
                baseline_extent=ctx_extent,
                baseline_diag=ctx_diag,
                baseline_path=ctx_init_path,
                out_dir=out_root / "context",
            )
        timing["recovery_s"] += t_rec.seconds
        _copy_png(best_path, ctx_final_path)
        stages.append("REVALIDATE_CONTEXT")
    else:
        _copy_png(ctx_init_path, ctx_final_path)
    stages.append("FREEZE_CONTEXT")
    ctx_valid_after = not _critical_unresolved(ctx_diag, crop_type="context")

    stages.append("DERIVE_DETAIL")
    if regions.get("detail_extent"):
        adapted_extent = as_extent(regions["detail_extent"])
    else:
        adapted_extent = as_extent(adaptive_detail_extent(msp=msp, beam_id=beam_id, mark=mark, titles=titles)["detail_extent"])
    det_extent = derive_detail_extent(ctx_current, adapted_extent, mark)
    det_init_path = out_root / "detail" / "initial" / f"{beam_id}.png"
    det_final_path = out_root / "detail" / "final" / f"{beam_id}.png"
    stages.append("RENDER_DETAIL")
    det_reuse = None
    if ctx_current == ctx_extent:
        b1b = reuse_initial.get("detail_bounds")
        if b1b and len(b1b) == 4 and max(abs(float(b1b[i]) - float(det_extent[i])) for i in range(4)) <= 12.0:
            det_reuse = reuse_initial.get("detail")
        elif reuse_initial.get("detail") and not b1b:
            det_reuse = None
    with Timer() as t_det:
        det_render = _render_one(
            render_fn=render_fn,
            dxf_path=dxf_path,
            output_path=det_init_path,
            extent=det_extent,
            crop_type="detail",
            reuse_src=det_reuse,
        )
    if det_render.get("reused_existing_png"):
        timing["reuse_copy_s"] += t_det.seconds
    else:
        timing["detail_render_s"] += t_det.seconds
    stages.append("VALIDATE_DETAIL")
    with Timer() as t_qd:
        det_diag = validate_render(det_init_path, extent=det_extent, crop_type="detail")
    timing["quality_s"] += t_qd.seconds
    det_initial_status = det_diag.get("primary_status")
    recover_det, det_reason = needs_recovery(det_diag, crop_type="detail", orientation=orientation)
    det_valid_before = not recover_det
    det_history: List[Dict[str, Any]] = []
    det_current = det_extent
    if recover_det:
        stages.append("RECOVER_DETAIL")
        with Timer() as t_rd:
            det_current, det_diag, det_history, best_path = _try_candidates(
                beam_id=beam_id,
                mark=mark,
                titles=titles,
                dxf_path=dxf_path,
                render_fn=render_fn,
                crop_type="detail",
                orientation=orientation,
                baseline_extent=det_extent,
                baseline_diag=det_diag,
                baseline_path=det_init_path,
                out_dir=out_root / "detail",
                container=ctx_current,
            )
        timing["recovery_s"] += t_rd.seconds
        _copy_png(best_path, det_final_path)
        stages.append("REVALIDATE_DETAIL")
    else:
        _copy_png(det_init_path, det_final_path)

    usable = _vision_usable(ctx_diag, det_diag)
    return {
        "beam_id": beam_id,
        "stages": stages,
        "dominant_orientation": orientation,
        "initial_context_bounds": list(ctx_extent),
        "final_context_bounds": list(ctx_current),
        "initial_detail_bounds": list(det_extent),
        "final_detail_bounds": list(det_current),
        "context_status": ctx_diag.get("primary_status"),
        "detail_status": det_diag.get("primary_status"),
        "context_initial_status": ctx_initial_status,
        "context_recovery_applied": bool(ctx_history),
        "context_final_status": ctx_diag.get("primary_status"),
        "context_recovery_reason": ctx_reason,
        "detail_initial_status": det_initial_status,
        "detail_recovery_applied": bool(det_history),
        "detail_recovery_reason": det_reason,
        "detail_final_status": det_diag.get("primary_status"),
        "context_flags": ctx_diag.get("flags") or [],
        "detail_flags": det_diag.get("flags") or [],
        "context_recovery_history": ctx_history,
        "detail_recovery_history": det_history,
        "context_diagnostic": ctx_diag,
        "detail_diagnostic": det_diag,
        "context_valid_before_recovery": ctx_valid_before,
        "context_valid_after_recovery": ctx_valid_after,
        "detail_valid_before_recovery": det_valid_before,
        "detail_valid_after_recovery": not _critical_unresolved(det_diag, crop_type="detail"),
        "context_recovery_attempt_count": len(ctx_history),
        "context_recovery_success": bool(ctx_history) and ctx_valid_after and not ctx_valid_before,
        "detail_recovery_attempt_count": len(det_history),
        "detail_recovery_success": bool(det_history) and (not _critical_unresolved(det_diag, crop_type="detail")) and not det_valid_before,
        "target_visible": bool(ctx_diag.get("target_visible") and det_diag.get("target_visible")),
        "longitudinal_complete": not (
            "HORIZONTAL_TRUNCATION_SUSPECT" in (ctx_diag.get("flags") or [])
            or "VERTICAL_TRUNCATION_SUSPECT" in (ctx_diag.get("flags") or [])
        ),
        "context_quality_pass": ctx_diag.get("primary_status") not in (
            STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING
        ),
        "final_vision_usable": bool(usable),
        "context_crop_path": str(ctx_final_path),
        "detail_crop_path": str(det_final_path),
        "context_initial_path": str(ctx_init_path),
        "detail_initial_path": str(det_init_path),
        "context_first": stages.index("VALIDATE_CONTEXT") < stages.index("RENDER_DETAIL"),
        "timing": timing,
    }


__all__ = ["derive_detail_extent", "process_beam"]
