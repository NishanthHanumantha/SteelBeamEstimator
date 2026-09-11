"""Generate P2.6.10-B.1 context/detail crops into a run-isolated evidence package."""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseP2610A_beam_region_crop_audit.cropper import render_crop
from PhaseP2610A_beam_region_crop_audit.title_localizer import choose_mark, collect_beam_titles
from PhaseP2610B_adaptive_beam_detail_crop.completeness import evaluate_completeness
from PhaseP2610B_adaptive_beam_detail_crop.envelope import build_adaptive_regions
from PhaseP2610B2_render_quality_directional_recovery.quality import validate_render
from PhaseP2610C1C2_evidence_inventory_candidate_selection.config import SOURCE_B1
from PhaseP2610C1C2_evidence_inventory_candidate_selection.inventory import _candidate
from PhaseP2610C1C2_evidence_inventory_candidate_selection.selector import select_for_type
from PhaseW5_production_hybrid_shadow.config import T1_RENDER_REL

from .config import (
    CLASS_COMPATIBILITY,
    CLASS_FALLBACK,
    CLASS_PRIMARY,
    CLASS_UNAVAILABLE,
    EVIDENCE_REL,
    MIN_RENDER_BYTES,
    SOURCE_MIXED,
    SOURCE_P2610_PRIMARY,
    SOURCE_T1_COMPAT,
    SOURCE_W6_COMPAT,
    STATUS_EVIDENCE_UNAVAILABLE,
)

logger = logging.getLogger("steel_webapp.hybrid_production")

SOURCE_W6_PHASE = "W.6"
SOURCE_T1_PHASE = "T1"


def evidence_root(staging: Path) -> Path:
    return Path(staging) / EVIDENCE_REL


def beam_dir(staging: Path, beam_id: str) -> Path:
    return evidence_root(staging) / str(beam_id)


def manifest_path(staging: Path, beam_id: str) -> Path:
    return beam_dir(staging, beam_id) / "evidence_manifest.json"


def selected_png(staging: Path, beam_id: str, crop_type: str) -> Path:
    return beam_dir(staging, beam_id) / crop_type / "selected.png"


def _hybrid_mode() -> str:
    return (os.environ.get("HYBRID_MODE") or "").strip().lower() or "unset"


def _usable_file(path: Optional[Path]) -> bool:
    return bool(path and Path(path).is_file() and Path(path).stat().st_size >= MIN_RENDER_BYTES)


def _copy_selected(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Path(src)
    dest = Path(dest)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def _safe_validate(path: Optional[Path], crop_type: str) -> Dict[str, Any]:
    try:
        return validate_render(Path(path) if path else None, crop_type=crop_type)
    except Exception as exc:
        return {
            "primary_status": "RENDER_MISSING",
            "visually_usable": False,
            "critical_failure": True,
            "flags": ["VALIDATOR_EXCEPTION", type(exc).__name__],
            "foreground_ratio": 0.0,
            "coverage_x": 0.0,
            "coverage_y": 0.0,
        }


def _is_critical(q: Dict[str, Any]) -> bool:
    status = str(q.get("primary_status") or "")
    return status in {
        "EMPTY_RENDER",
        "BLACK_RENDER",
        "LOW_INFORMATION_RENDER",
        "RENDER_MISSING",
    } or bool(q.get("critical_failure"))


def _candidate_from_path(
    *,
    source_phase: str,
    crop_type: str,
    path: Optional[Path],
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        return _candidate(
            source_phase=source_phase,
            crop_type=crop_type,
            path=path,
            diagnostics=diagnostics or {},
        )
    except Exception as exc:
        return {
            "source_phase": source_phase,
            "crop_type": crop_type,
            "path": str(path) if path else None,
            "exists": _usable_file(path),
            "candidate_status": "AVAILABLE" if _usable_file(path) else "MISSING",
            "critical_failure": True,
            "usable_status": False,
            "primary_status": "RENDER_MISSING",
            "score": -1.0,
            "foreground_ratio": 0.0,
            "coverage_x": 0.0,
            "coverage_y": 0.0,
            "quality_flags": ["CANDIDATE_EXCEPTION", type(exc).__name__],
            "empty_sides": [],
            "sha256": None,
        }


def _c3_gate(ctx_sel: Dict[str, Any], det_sel: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from PhaseP2610C3_visual_completeness_claude_shadow.evidence_model import SelectedRender
        from PhaseP2610C3_visual_completeness_claude_shadow.visual_completeness_gate import (
            evaluate_completeness as c3_gate,
        )
    except Exception as exc:
        return {
            "status": "GATE_UNAVAILABLE",
            "sufficient_for_target_interpretation": True,
            "reason_codes": [f"C3_IMPORT:{type(exc).__name__}"],
        }

    def _side(crop_type: str, sel: Dict[str, Any]) -> SelectedRender:
        selected = sel.get("selected") or {}
        return SelectedRender(
            crop_type=crop_type,
            source_phase=selected.get("source_phase"),
            path=selected.get("path"),
            sha256=selected.get("sha256"),
            primary_status=selected.get("primary_status"),
            critical_failure=bool(selected.get("critical_failure")),
            selection_status=sel.get("selection_status"),
            reason_codes=list(sel.get("selection_reason_codes") or []),
            usable_status=bool(selected.get("usable_status")),
            score=float(selected.get("score") or -1.0),
            foreground_ratio=float(selected.get("foreground_ratio") or 0.0),
            coverage_x=float(selected.get("coverage_x") or 0.0),
            coverage_y=float(selected.get("coverage_y") or 0.0),
            empty_sides=list(selected.get("empty_sides") or []),
            quality_flags=list(selected.get("quality_flags") or []),
            integrity={
                "exists": bool(selected.get("exists")),
                "integrity_ok": bool(selected.get("exists")) and not selected.get("critical_failure"),
                "file_missing": not bool(selected.get("exists")),
            },
        )

    return c3_gate(_side("context", ctx_sel), _side("detail", det_sel))


class DxfSession:
    """Load the run reinforcement DXF once. Never logs secrets."""

    def __init__(self, staging: Path):
        self.staging = Path(staging)
        self.dxf: Optional[Path] = None
        self.msp: Any = None
        self.titles: List[Dict[str, Any]] = []
        self.error: Optional[str] = None
        folder = self.staging / "reinforcement"
        if folder.is_dir():
            dxfs = sorted(folder.glob("*.dxf"))
            self.dxf = dxfs[0] if dxfs else None
        if self.dxf is None or not self.dxf.is_file():
            self.error = "REINFORCEMENT_DXF_MISSING"
            return
        try:
            import ezdxf

            doc = ezdxf.readfile(str(self.dxf))
            self.msp = doc.modelspace()
            self.titles = collect_beam_titles(self.msp)
        except Exception as exc:
            self.error = type(exc).__name__
            logger.warning("W.8 DXF session failed error_type=%s", type(exc).__name__)
            self.msp = None
            self.titles = []

    def drawing_identity(self) -> Optional[str]:
        return self.dxf.name if self.dxf else None


def _render_p2610_pair(
    session: DxfSession,
    beam_id: str,
    dest_dir: Path,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "ok": False,
        "reason": None,
        "context_path": None,
        "detail_path": None,
        "context_extent": None,
        "detail_extent": None,
        "context_render": None,
        "detail_render": None,
        "completeness": None,
        "mark": None,
    }
    if session.msp is None or session.dxf is None:
        out["reason"] = session.error or "REINFORCEMENT_DXF_MISSING"
        return out
    mark = choose_mark(session.msp, session.titles, beam_id)
    if mark is None:
        out["reason"] = "TITLE_MARK_MISSING"
        return out
    out["mark"] = {
        "beam_id": mark.get("beam_id"),
        "x": mark.get("x"),
        "y": mark.get("y"),
        "depth_mm": mark.get("depth_mm"),
        "width_mm": mark.get("width_mm"),
        "candidate_count": mark.get("candidate_count"),
    }
    try:
        regions = build_adaptive_regions(
            msp=session.msp, beam_id=beam_id, mark=mark, titles=session.titles
        )
    except Exception as exc:
        out["reason"] = f"ADAPTIVE_REGIONS:{type(exc).__name__}"
        logger.warning(
            "W.8 adaptive regions failed beam_id=%s error_type=%s",
            beam_id,
            type(exc).__name__,
        )
        return out
    ctx_ext = regions.get("context_extent")
    det_ext = regions.get("detail_extent")
    out["context_extent"] = list(ctx_ext) if ctx_ext else None
    out["detail_extent"] = list(det_ext) if det_ext else None
    cand_dir = dest_dir / "_candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    ctx_png = cand_dir / "p2610b1_context.png"
    det_png = cand_dir / "p2610b1_detail.png"
    try:
        out["context_render"] = render_crop(
            dxf_path=session.dxf, output_path=ctx_png, extent=ctx_ext, crop_type="context"
        )
        out["context_path"] = str(ctx_png) if _usable_file(ctx_png) else None
    except Exception as exc:
        out["reason"] = f"CONTEXT_RENDER:{type(exc).__name__}"
        logger.warning(
            "W.8 context render failed beam_id=%s error_type=%s",
            beam_id,
            type(exc).__name__,
        )
        return out
    try:
        out["detail_render"] = render_crop(
            dxf_path=session.dxf, output_path=det_png, extent=det_ext, crop_type="detail"
        )
        out["detail_path"] = str(det_png) if _usable_file(det_png) else None
    except Exception as exc:
        out["reason"] = f"DETAIL_RENDER:{type(exc).__name__}"
        logger.warning(
            "W.8 detail render failed beam_id=%s error_type=%s",
            beam_id,
            type(exc).__name__,
        )
        return out
    if not out["context_path"] or not out["detail_path"]:
        out["reason"] = "P2610_RENDER_EMPTY"
        return out
    adapted = regions.get("adaptive") or {}
    try:
        out["completeness"] = evaluate_completeness(
            beam_id=beam_id,
            extent=det_ext,
            mark=mark,
            outline=adapted.get("outline"),
            evidence=list(adapted.get("evidence") or []),
            titles=session.titles,
        )
    except Exception as exc:
        out["completeness"] = {"complete": None, "error_type": type(exc).__name__}
    out["ok"] = True
    return out


def _render_w6(staging: Path, beam_id: str) -> Dict[str, Any]:
    from PhaseW6_hybrid_production_authority.visuals import render_w6_envelope_crop

    return render_w6_envelope_crop(staging, beam_id)


def _t1_path(staging: Path, beam_id: str) -> Optional[Path]:
    path = Path(staging) / T1_RENDER_REL / f"{beam_id}_crop.png"
    return path if _usable_file(path) else None


def _visual_source(ctx_phase: str, det_phase: str) -> str:
    if ctx_phase == SOURCE_B1 and det_phase == SOURCE_B1:
        return SOURCE_P2610_PRIMARY
    if ctx_phase == SOURCE_W6_PHASE and det_phase == SOURCE_W6_PHASE:
        return SOURCE_W6_COMPAT
    if ctx_phase == SOURCE_T1_PHASE and det_phase == SOURCE_T1_PHASE:
        return SOURCE_T1_COMPAT
    if ctx_phase == det_phase:
        if ctx_phase == SOURCE_B1:
            return SOURCE_P2610_PRIMARY
        if ctx_phase == SOURCE_W6_PHASE:
            return SOURCE_W6_COMPAT
        return SOURCE_T1_COMPAT
    return SOURCE_MIXED


def _class_for_source(source: str) -> str:
    if source == SOURCE_P2610_PRIMARY:
        return CLASS_PRIMARY
    if source in (SOURCE_W6_COMPAT, SOURCE_T1_COMPAT, SOURCE_MIXED):
        return CLASS_COMPATIBILITY
    return CLASS_UNAVAILABLE


def _install_pair(
    staging: Path,
    beam_id: str,
    context_src: Path,
    detail_src: Path,
) -> Tuple[Path, Path]:
    ctx = _copy_selected(context_src, selected_png(staging, beam_id, "context"))
    det = _copy_selected(detail_src, selected_png(staging, beam_id, "detail"))
    return ctx, det


def _reuse_existing(staging: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    man_path = manifest_path(staging, beam_id)
    ctx = selected_png(staging, beam_id, "context")
    det = selected_png(staging, beam_id, "detail")
    if not man_path.is_file():
        return None
    try:
        man = json.loads(man_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(man, dict):
        return None
    if man.get("available") is False:
        return {
            "ok": False,
            "available": False,
            "beam_id": beam_id,
            "evidence_class": man.get("evidence_class") or CLASS_UNAVAILABLE,
            "visual_source": man.get("visual_source"),
            "context_path": None,
            "detail_path": None,
            "path": None,
            "fallback_status": man.get("fallback_status") or CLASS_UNAVAILABLE,
            "fallback_reason": man.get("fallback_reason"),
            "manifest": man,
            "reason": man.get("reason") or STATUS_EVIDENCE_UNAVAILABLE,
            "reused": True,
        }
    if not (_usable_file(ctx) and _usable_file(det)):
        return None
    source = man.get("visual_source") or SOURCE_P2610_PRIMARY
    ctx_sel = man.get("selected_context_evidence") or {}
    det_sel = man.get("selected_detail_evidence") or {}
    return {
        "ok": True,
        "available": True,
        "beam_id": beam_id,
        "evidence_class": man.get("evidence_class") or _class_for_source(str(source)),
        "visual_source": source,
        "context_source": ctx_sel.get("source_phase") or source,
        "detail_source": det_sel.get("source_phase") or source,
        "context_path": str(ctx),
        "detail_path": str(det),
        "path": str(ctx),
        "fallback_status": man.get("fallback_status") or "NONE",
        "fallback_reason": man.get("fallback_reason"),
        "manifest": man,
        "reason": None,
        "reused": True,
    }


def build_beam_evidence(
    *,
    staging: Path,
    beam_id: str,
    session: DxfSession,
) -> Dict[str, Any]:
    """
    Produce selected context + detail for one beam.

    PRIMARY: P2.6.10-B.1 adaptive context/detail.
    COMPATIBILITY/FALLBACK: W.6 envelope or T1 OpenCV crop, never silent.
    """
    staging = Path(staging)
    reused = _reuse_existing(staging, beam_id)
    if reused is not None:
        return reused
    dest = beam_dir(staging, beam_id)
    dest.mkdir(parents=True, exist_ok=True)
    attempted: List[str] = []
    candidates_considered: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    p2610 = _render_p2610_pair(session, beam_id, dest)
    if p2610.get("ok"):
        attempted.append("P2610B1_ADAPTIVE")
        candidates_considered.append(
            {
                "source_phase": SOURCE_B1,
                "context_path": p2610.get("context_path"),
                "detail_path": p2610.get("detail_path"),
                "reason": "generated",
            }
        )
    else:
        attempted.append(f"P2610B1_ADAPTIVE:{p2610.get('reason')}")

    w6: Dict[str, Any] = {"ok": False}
    t1 = _t1_path(staging, beam_id)

    def _finish(
        *,
        context_src: Path,
        detail_src: Path,
        ctx_phase: str,
        det_phase: str,
        evidence_class: str,
        fallback_status: str,
        fallback_reason: Optional[str],
        selection: Optional[Dict[str, Any]],
        completeness_status: Optional[str],
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx_dest, det_dest = _install_pair(staging, beam_id, context_src, detail_src)
        source = _visual_source(ctx_phase, det_phase)
        q_ctx = _safe_validate(ctx_dest, "context")
        q_det = _safe_validate(det_dest, "detail")
        manifest = {
            "beam_id": beam_id,
            "source_dxf": session.drawing_identity(),
            "evidence_candidates_considered": candidates_considered,
            "selected_context_evidence": {
                "path": str(ctx_dest),
                "source_phase": ctx_phase,
                "crop_coordinates": (p2610.get("context_extent") if ctx_phase == SOURCE_B1 else None),
                "rendering_scale": ((p2610.get("context_render") or {}).get("scale_px_per_mm") if ctx_phase == SOURCE_B1 else None),
                "image_dimensions": ((p2610.get("context_render") or {}).get("image_dimensions") if ctx_phase == SOURCE_B1 else None),
                "renderer": "PhaseM.1_engineering_vision_dataset.dxf_renderer.render_dxf_region_to_png",
                "primary_status": q_ctx.get("primary_status"),
            },
            "selected_detail_evidence": {
                "path": str(det_dest),
                "source_phase": det_phase,
                "crop_coordinates": (p2610.get("detail_extent") if det_phase == SOURCE_B1 else None),
                "rendering_scale": ((p2610.get("detail_render") or {}).get("scale_px_per_mm") if det_phase == SOURCE_B1 else None),
                "image_dimensions": ((p2610.get("detail_render") or {}).get("image_dimensions") if det_phase == SOURCE_B1 else None),
                "renderer": "PhaseM.1_engineering_vision_dataset.dxf_renderer.render_dxf_region_to_png",
                "primary_status": q_det.get("primary_status"),
            },
            "renderer_generation_method": source,
            "selection_reason": (selection or {}).get("selection_reason_codes")
            or [fallback_reason or evidence_class],
            "completeness_status": completeness_status,
            "spatial_completeness": p2610.get("completeness"),
            "fallback_status": fallback_status,
            "fallback_reason": fallback_reason,
            "timestamp": now,
            "hybrid_mode": _hybrid_mode(),
            "evidence_class": evidence_class,
            "visual_source": source,
            "attempted_evidence_sources": attempted,
            "context_and_detail_distinct": str(ctx_dest.resolve()) != str(det_dest.resolve())
            and ctx_dest.stat().st_size != det_dest.stat().st_size
            if ctx_dest.is_file() and det_dest.is_file()
            else True,
            "claude_image_contract": {
                "context_images": 1,
                "detail_images": 1,
                "multiple_detail_supported_in_request": False,
            },
            "available": True,
        }
        if extra:
            manifest.update(extra)
        return {
            "ok": True,
            "available": True,
            "beam_id": beam_id,
            "evidence_class": evidence_class,
            "visual_source": source,
            "context_source": source if ctx_phase == det_phase else _visual_source(ctx_phase, ctx_phase),
            "detail_source": source if ctx_phase == det_phase else _visual_source(det_phase, det_phase),
            "context_path": str(ctx_dest),
            "detail_path": str(det_dest),
            "path": str(ctx_dest),
            "fallback_status": fallback_status,
            "fallback_reason": fallback_reason,
            "manifest": manifest,
            "reason": None,
        }

    if p2610.get("ok"):
        ctx_cands = [
            _candidate_from_path(
                source_phase=SOURCE_B1,
                crop_type="context",
                path=Path(p2610["context_path"]),
                diagnostics={"generation": "P2610B1"},
            )
        ]
        det_cands = [
            _candidate_from_path(
                source_phase=SOURCE_B1,
                crop_type="detail",
                path=Path(p2610["detail_path"]),
                diagnostics={"generation": "P2610B1"},
            )
        ]
        ctx_critical = bool(ctx_cands[0].get("critical_failure"))
        det_critical = bool(det_cands[0].get("critical_failure"))
        if ctx_critical or det_critical:
            w6 = _render_w6(staging, beam_id)
            attempted.append("W6_ENVELOPE" if w6.get("ok") else f"W6_ENVELOPE:{w6.get('reason')}")
            if w6.get("ok") and _usable_file(Path(w6["path"])):
                candidates_considered.append(
                    {"source_phase": SOURCE_W6_PHASE, "path": w6.get("path"), "reason": "challenger"}
                )
                w6p = Path(w6["path"])
                ctx_cands.append(
                    _candidate_from_path(
                        source_phase=SOURCE_W6_PHASE, crop_type="context", path=w6p
                    )
                )
                det_cands.append(
                    _candidate_from_path(
                        source_phase=SOURCE_W6_PHASE, crop_type="detail", path=w6p
                    )
                )
            if t1:
                attempted.append("T1_OPENCV")
                candidates_considered.append(
                    {"source_phase": SOURCE_T1_PHASE, "path": str(t1), "reason": "challenger"}
                )
                ctx_cands.append(
                    _candidate_from_path(
                        source_phase=SOURCE_T1_PHASE, crop_type="context", path=t1
                    )
                )
                det_cands.append(
                    _candidate_from_path(
                        source_phase=SOURCE_T1_PHASE, crop_type="detail", path=t1
                    )
                )
        ctx_sel = select_for_type(ctx_cands)
        det_sel = select_for_type(det_cands)
        gate = _c3_gate(ctx_sel, det_sel)
        ctx_picked = ctx_sel.get("selected") or {}
        det_picked = det_sel.get("selected") or {}
        ctx_path = Path(ctx_picked["path"]) if ctx_picked.get("path") else None
        det_path = Path(det_picked["path"]) if det_picked.get("path") else None
        blocking = str(gate.get("status") or "") == "VISION_NOT_READY"
        if (
            ctx_path
            and det_path
            and _usable_file(ctx_path)
            and _usable_file(det_path)
            and not blocking
        ):
            ctx_phase = str(ctx_picked.get("source_phase") or SOURCE_B1)
            det_phase = str(det_picked.get("source_phase") or SOURCE_B1)
            source = _visual_source(ctx_phase, det_phase)
            evidence_class = _class_for_source(source)
            fallback = "NONE" if evidence_class == CLASS_PRIMARY else CLASS_COMPATIBILITY
            return _finish(
                context_src=ctx_path,
                detail_src=det_path,
                ctx_phase=ctx_phase,
                det_phase=det_phase,
                evidence_class=evidence_class,
                fallback_status=fallback,
                fallback_reason=None if fallback == "NONE" else "C1C2_SELECTED_NON_PRIMARY",
                selection={
                    "selection_reason_codes": list(ctx_sel.get("selection_reason_codes") or [])
                    + list(det_sel.get("selection_reason_codes") or []),
                },
                completeness_status=str(gate.get("status") or "SELECTED"),
                extra={"c3_gate": {k: gate.get(k) for k in ("status", "reason_codes", "sufficient_for_target_interpretation")}},
            )
        attempted.append(f"P2610_GATE:{gate.get('status')}")

    if not w6.get("ok"):
        w6 = _render_w6(staging, beam_id)
        attempted.append("W6_ENVELOPE" if w6.get("ok") else f"W6_ENVELOPE:{w6.get('reason')}")
        if w6.get("ok"):
            candidates_considered.append(
                {"source_phase": SOURCE_W6_PHASE, "path": w6.get("path"), "reason": "fallback"}
            )

    if w6.get("ok") and _usable_file(Path(w6["path"])):
        path = Path(w6["path"])
        return _finish(
            context_src=path,
            detail_src=path,
            ctx_phase=SOURCE_W6_PHASE,
            det_phase=SOURCE_W6_PHASE,
            evidence_class=CLASS_FALLBACK,
            fallback_status=CLASS_FALLBACK,
            fallback_reason=p2610.get("reason") or "P2610_PRIMARY_NOT_USABLE",
            selection={"selection_reason_codes": ["W6_COMPATIBILITY_FALLBACK"]},
            completeness_status="W6_COMPATIBILITY",
        )

    if t1:
        attempted.append("T1_OPENCV")
        candidates_considered.append(
            {"source_phase": SOURCE_T1_PHASE, "path": str(t1), "reason": "fallback"}
        )
        return _finish(
            context_src=t1,
            detail_src=t1,
            ctx_phase=SOURCE_T1_PHASE,
            det_phase=SOURCE_T1_PHASE,
            evidence_class=CLASS_COMPATIBILITY,
            fallback_status=CLASS_COMPATIBILITY,
            fallback_reason=p2610.get("reason") or "P2610_PRIMARY_UNAVAILABLE_T1_PRESENT",
            selection={"selection_reason_codes": ["T1_COMPATIBILITY_FALLBACK"]},
            completeness_status="T1_COMPATIBILITY",
        )

    manifest = {
        "beam_id": beam_id,
        "source_dxf": session.drawing_identity(),
        "evidence_candidates_considered": candidates_considered,
        "selected_context_evidence": None,
        "selected_detail_evidence": None,
        "renderer_generation_method": None,
        "selection_reason": [STATUS_EVIDENCE_UNAVAILABLE],
        "completeness_status": STATUS_EVIDENCE_UNAVAILABLE,
        "fallback_status": CLASS_UNAVAILABLE,
        "fallback_reason": p2610.get("reason") or session.error or "NO_USABLE_EVIDENCE",
        "timestamp": now,
        "hybrid_mode": _hybrid_mode(),
        "evidence_class": CLASS_UNAVAILABLE,
        "visual_source": None,
        "attempted_evidence_sources": attempted,
        "available": False,
    }
    return {
        "ok": False,
        "available": False,
        "beam_id": beam_id,
        "evidence_class": CLASS_UNAVAILABLE,
        "visual_source": None,
        "context_path": None,
        "detail_path": None,
        "path": None,
        "fallback_status": CLASS_UNAVAILABLE,
        "fallback_reason": manifest["fallback_reason"],
        "manifest": manifest,
        "reason": STATUS_EVIDENCE_UNAVAILABLE,
    }


__all__ = [
    "DxfSession",
    "beam_dir",
    "build_beam_evidence",
    "evidence_root",
    "manifest_path",
    "selected_png",
]
