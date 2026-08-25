"""Discover Hybrid visual evidence. Prefers W.8 packages, then T1, then W.6 crops."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import MIN_RENDER_BYTES, T1_RENDER_REL, VISUAL_SOURCE

W6_CROP_REL = "data/output/PhaseW6_hybrid_semantic_resolution/crops"
W8_EVIDENCE_REL = "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence"


def crop_path(staging: Path, beam_id: str) -> Path:
    ctx = Path(staging) / W8_EVIDENCE_REL / str(beam_id) / "context" / "selected.png"
    if ctx.is_file():
        return ctx
    t1 = Path(staging) / T1_RENDER_REL / f"{beam_id}_crop.png"
    if t1.is_file():
        return t1
    return Path(staging) / W6_CROP_REL / f"{beam_id}_crop.png"


def _load_manifest(staging: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = Path(staging) / W8_EVIDENCE_REL / str(beam_id) / "evidence_manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _row_from_package(staging: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    man = _load_manifest(staging, beam_id)
    ctx = Path(staging) / W8_EVIDENCE_REL / str(beam_id) / "context" / "selected.png"
    det = Path(staging) / W8_EVIDENCE_REL / str(beam_id) / "detail" / "selected.png"
    if man is not None and man.get("available") is False:
        return {
            "beam_id": str(beam_id),
            "available": False,
            "reason": man.get("fallback_reason") or man.get("completeness_status") or "EVIDENCE_UNAVAILABLE",
            "path": str(ctx),
            "context_path": str(ctx) if ctx.is_file() else None,
            "detail_path": str(det) if det.is_file() else None,
            "bytes": ctx.stat().st_size if ctx.is_file() else 0,
            "source": man.get("visual_source") or "EVIDENCE_UNAVAILABLE",
            "context_source": (man.get("selected_context_evidence") or {}).get("source_phase"),
            "detail_source": (man.get("selected_detail_evidence") or {}).get("source_phase"),
            "evidence_class": man.get("evidence_class") or "UNAVAILABLE",
            "fallback_status": man.get("fallback_status"),
            "fallback_reason": man.get("fallback_reason"),
            "evidence_manifest": str(
                Path(staging) / W8_EVIDENCE_REL / str(beam_id) / "evidence_manifest.json"
            ),
        }
    if not (ctx.is_file() and det.is_file()):
        return None
    size = ctx.stat().st_size
    if size < MIN_RENDER_BYTES or det.stat().st_size < MIN_RENDER_BYTES:
        return {
            "beam_id": str(beam_id),
            "available": False,
            "reason": "LOW_INFORMATION_RENDER",
            "path": str(ctx),
            "context_path": str(ctx),
            "detail_path": str(det),
            "bytes": size,
            "source": (man or {}).get("visual_source") or "W8_EVIDENCE",
            "evidence_class": (man or {}).get("evidence_class"),
            "fallback_status": (man or {}).get("fallback_status"),
            "fallback_reason": (man or {}).get("fallback_reason"),
        }
    source = (man or {}).get("visual_source") or "W8_EVIDENCE"
    ctx_src = source
    det_src = source
    if man:
        ctx_sel = man.get("selected_context_evidence") or {}
        det_sel = man.get("selected_detail_evidence") or {}
        if ctx_sel.get("source_phase") == "B.1":
            ctx_src = "P2610B1_ADAPTIVE_CONTEXT_DETAIL"
        elif ctx_sel.get("source_phase") == "W.6":
            ctx_src = "W6_ENVELOPE_RENDER"
        elif ctx_sel.get("source_phase") == "T1":
            ctx_src = VISUAL_SOURCE
        if det_sel.get("source_phase") == "B.1":
            det_src = "P2610B1_ADAPTIVE_CONTEXT_DETAIL"
        elif det_sel.get("source_phase") == "W.6":
            det_src = "W6_ENVELOPE_RENDER"
        elif det_sel.get("source_phase") == "T1":
            det_src = VISUAL_SOURCE
    return {
        "beam_id": str(beam_id),
        "available": True,
        "reason": None,
        "path": str(ctx),
        "context_path": str(ctx),
        "detail_path": str(det),
        "bytes": size,
        "source": source,
        "context_source": ctx_src,
        "detail_source": det_src,
        "evidence_class": (man or {}).get("evidence_class") or "PRIMARY",
        "fallback_status": (man or {}).get("fallback_status") or "NONE",
        "fallback_reason": (man or {}).get("fallback_reason"),
        "evidence_manifest": str(
            Path(staging) / W8_EVIDENCE_REL / str(beam_id) / "evidence_manifest.json"
        ),
    }


def discover_visuals(staging: Path, *, beam_ids: List[str]) -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    available = 0
    missing = 0
    too_small = 0
    w8_count = 0
    for bid in beam_ids:
        packed = _row_from_package(staging, str(bid))
        if packed is not None:
            by_id[str(bid)] = packed
            w8_count += 1
            if packed.get("available"):
                available += 1
            elif packed.get("reason") == "LOW_INFORMATION_RENDER":
                too_small += 1
            else:
                missing += 1
            continue
        t1 = Path(staging) / T1_RENDER_REL / f"{str(bid)}_crop.png"
        w6 = Path(staging) / W6_CROP_REL / f"{str(bid)}_crop.png"
        if t1.is_file():
            path = t1
            source = VISUAL_SOURCE
        elif w6.is_file():
            path = w6
            source = "W6_ENVELOPE_RENDER"
        else:
            path = t1
            source = VISUAL_SOURCE
        if not path.is_file():
            missing += 1
            by_id[str(bid)] = {
                "beam_id": str(bid),
                "available": False,
                "reason": "RENDER_MISSING",
                "path": str(path),
                "context_path": str(path),
                "detail_path": str(path),
                "bytes": 0,
                "source": source,
            }
            continue
        size = path.stat().st_size
        if size < MIN_RENDER_BYTES:
            too_small += 1
            by_id[str(bid)] = {
                "beam_id": str(bid),
                "available": False,
                "reason": "LOW_INFORMATION_RENDER",
                "path": str(path),
                "context_path": str(path),
                "detail_path": str(path),
                "bytes": size,
                "source": source,
            }
            continue
        available += 1
        by_id[str(bid)] = {
            "beam_id": str(bid),
            "available": True,
            "reason": None,
            "path": str(path),
            "context_path": str(path),
            "detail_path": str(path),
            "bytes": size,
            "source": source,
            "context_source": source,
            "detail_source": source,
            "evidence_class": "COMPATIBILITY",
            "fallback_status": "COMPATIBILITY",
            "fallback_reason": "W8_PACKAGE_ABSENT",
        }
    return {
        "ok": True,
        "available_count": available,
        "missing_count": missing,
        "too_small_count": too_small,
        "w8_package_count": w8_count,
        "by_id": by_id,
        "discovery_method": "W8_EVIDENCE_OR_T1_OR_W6",
        "render_dir": str(Path(staging) / T1_RENDER_REL),
        "evidence_dir": str(Path(staging) / W8_EVIDENCE_REL),
    }


def eligible_beam_ids(visual: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for bid, row in sorted((visual.get("by_id") or {}).items()):
        if row.get("available"):
            out.append(str(bid))
    return out
