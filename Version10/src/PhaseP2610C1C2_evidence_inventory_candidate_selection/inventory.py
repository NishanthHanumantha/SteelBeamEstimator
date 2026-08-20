"""Read-only candidate discovery from existing B.1/B.2/B.3 artefacts. No DXF. No render."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610B2_render_quality_directional_recovery.quality import validate_render

from .config import (
    CRITICAL_STATUSES,
    P2610B1_OUTPUT_DIRNAME,
    P2610B2_OUTPUT_DIRNAME,
    P2610B3_OUTPUT_DIRNAME,
    SOURCE_B1,
    SOURCE_B2,
    SOURCE_B3,
)

_HASH_CACHE: Dict[str, str] = {}
_STAT_CACHE: Dict[str, Dict[str, Any]] = {}


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sha256_file(path: Path) -> Optional[str]:
    key = str(path.resolve()) if path.exists() else ""
    if not key:
        return None
    cached = _HASH_CACHE.get(key)
    if cached:
        return cached
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    _HASH_CACHE[key] = digest
    return digest


def png_stats(path: Path) -> Dict[str, Any]:
    key = str(path.resolve())
    cached = _STAT_CACHE.get(key)
    if cached is not None:
        return cached
    out = {"width_px": None, "height_px": None, "pixel_count": None, "file_size_bytes": path.stat().st_size}
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
            out["width_px"] = int(w)
            out["height_px"] = int(h)
            out["pixel_count"] = int(w) * int(h)
    except Exception:
        pass
    _STAT_CACHE[key] = out
    return out


def population_beam_ids(v10: Path) -> List[str]:
    root = Path(v10) / "data" / "output" / P2610B1_OUTPUT_DIRNAME / "validation"
    ids = sorted(p.stem for p in root.glob("*.json") if p.is_file())
    return ids


def _candidate(
    *,
    source_phase: str,
    crop_type: str,
    path: Optional[Path],
    diagnostics: Optional[Dict[str, Any]] = None,
    artefact_id: str = "canonical",
    prior_action: Optional[str] = None,
) -> Dict[str, Any]:
    exists = bool(path and Path(path).exists() and Path(path).stat().st_size > 200)
    rec: Dict[str, Any] = {
        "source_phase": source_phase,
        "crop_type": crop_type,
        "artefact_id": artefact_id,
        "path": str(path) if path else None,
        "exists": exists,
        "candidate_status": "AVAILABLE" if exists else "MISSING",
        "prior_action": prior_action,
        "sha256": None,
        "width_px": None,
        "height_px": None,
        "pixel_count": None,
        "file_size_bytes": None,
        "diagnostics": diagnostics or {},
        "quality_flags": [],
        "usable_status": False,
        "primary_status": "RENDER_MISSING",
        "critical_failure": True,
        "score": -1.0,
        "foreground_ratio": 0.0,
        "coverage_x": 0.0,
        "coverage_y": 0.0,
        "empty_sides": [],
    }
    if not exists:
        rec["quality_flags"] = ["FILE_MISSING"]
        return rec
    p = Path(path)
    rec["sha256"] = sha256_file(p)
    rec.update({k: v for k, v in png_stats(p).items() if v is not None or k == "file_size_bytes"})
    q = validate_render(p, crop_type=crop_type)
    rec["diagnostics"] = {**(diagnostics or {}), "validate_render": {
        "primary_status": q.get("primary_status"),
        "flags": q.get("flags"),
        "foreground_ratio": q.get("foreground_ratio"),
        "coverage_x": q.get("coverage_x"),
        "coverage_y": q.get("coverage_y"),
        "dark_ratio": q.get("dark_ratio"),
        "information_density": q.get("information_density"),
        "visually_usable": q.get("visually_usable"),
        "empty_sides": q.get("empty_sides"),
    }}
    rec["quality_flags"] = list(q.get("flags") or [])
    rec["usable_status"] = bool(q.get("visually_usable"))
    rec["primary_status"] = str(q.get("primary_status") or "RENDER_MISSING")
    rec["foreground_ratio"] = float(q.get("foreground_ratio") or 0.0)
    rec["coverage_x"] = float(q.get("coverage_x") or 0.0)
    rec["coverage_y"] = float(q.get("coverage_y") or 0.0)
    rec["empty_sides"] = list(q.get("empty_sides") or [])
    rec["critical_failure"] = rec["primary_status"] in CRITICAL_STATUSES
    rec["score"] = _score(rec)
    return rec


def _score(rec: Dict[str, Any]) -> float:
    if rec.get("critical_failure") or not rec.get("exists"):
        return -1.0
    s = 0.0
    s += float(rec.get("foreground_ratio") or 0.0) * 8.0
    s += float(rec.get("coverage_x") or 0.0) * 2.0
    s += float(rec.get("coverage_y") or 0.0) * 1.0
    if rec.get("usable_status"):
        s += 0.5
    if not rec.get("empty_sides"):
        s += 0.3
    return round(s, 4)


def inventory_beam(v10: Path, beam_id: str) -> Dict[str, Any]:
    b1 = Path(v10) / "data" / "output" / P2610B1_OUTPUT_DIRNAME
    b2 = Path(v10) / "data" / "output" / P2610B2_OUTPUT_DIRNAME
    b3 = Path(v10) / "data" / "output" / P2610B3_OUTPUT_DIRNAME
    b1j = _load_json(b1 / "validation" / f"{beam_id}.json") or {}
    b2j = _load_json(b2 / "diagnostics" / f"{beam_id}.json") or {}
    context: List[Dict[str, Any]] = []
    detail: List[Dict[str, Any]] = []

    context.append(_candidate(
        source_phase=SOURCE_B1,
        crop_type="context",
        path=b1 / "context" / f"{beam_id}.png",
        diagnostics={
            "completeness_status": b1j.get("completeness_status"),
            "failure_categories": b1j.get("failure_categories") or [],
            "p2610b_complete_flag": b1j.get("p2610b_complete_flag"),
        },
    ))
    detail.append(_candidate(
        source_phase=SOURCE_B1,
        crop_type="detail",
        path=b1 / "detail" / f"{beam_id}.png",
        diagnostics={
            "completeness_status": b1j.get("completeness_status"),
            "failure_categories": b1j.get("failure_categories") or [],
        },
    ))
    context.append(_candidate(
        source_phase=SOURCE_B2,
        crop_type="context",
        path=b2 / "context" / "final" / f"{beam_id}.png",
        diagnostics={
            "context_status": b2j.get("context_status"),
            "final_vision_usable": b2j.get("final_vision_usable"),
            "context_recovery_applied": b2j.get("context_recovery_applied"),
        },
        prior_action="b2_final",
    ))
    detail.append(_candidate(
        source_phase=SOURCE_B2,
        crop_type="detail",
        path=b2 / "detail" / "final" / f"{beam_id}.png",
        diagnostics={
            "detail_status": b2j.get("detail_status"),
            "final_vision_usable": b2j.get("final_vision_usable"),
        },
        prior_action="b2_final",
    ))

    b1_ctx_sha = context[0].get("sha256")
    b1_det_sha = detail[0].get("sha256")
    sel_ctx = b3 / "review" / beam_id / "selected" / "context.png"
    sel_det = b3 / "review" / beam_id / "selected" / "detail.png"
    cand_dir = b3 / "review" / beam_id / "b3_candidate"
    if sel_ctx.exists():
        c = _candidate(source_phase=SOURCE_B3, crop_type="context", path=sel_ctx, artefact_id="selected", prior_action="b3_selected")
        if c.get("sha256") and c["sha256"] == b1_ctx_sha:
            c["candidate_status"] = "DUPLICATE_OF_PREFERRED"
            c["prior_action"] = "b3_selected_duplicate_b1"
        context.append(c)
    if sel_det.exists():
        c = _candidate(source_phase=SOURCE_B3, crop_type="detail", path=sel_det, artefact_id="selected", prior_action="b3_selected")
        if c.get("sha256") and c["sha256"] == b1_det_sha:
            c["candidate_status"] = "DUPLICATE_OF_PREFERRED"
        detail.append(c)
    if cand_dir.exists():
        for png in sorted(cand_dir.glob("*.png")):
            kind = "detail" if png.name.lower().startswith("detail") else "context"
            c = _candidate(source_phase=SOURCE_B3, crop_type=kind, path=png, artefact_id=png.name, prior_action="b3_candidate")
            if kind == "context":
                if c.get("sha256") == b1_ctx_sha:
                    c["candidate_status"] = "DUPLICATE_OF_PREFERRED"
                context.append(c)
            else:
                if c.get("sha256") == b1_det_sha:
                    c["candidate_status"] = "DUPLICATE_OF_PREFERRED"
                detail.append(c)

    if not any(c.get("source_phase") == SOURCE_B3 and c.get("crop_type") == "context" for c in context):
        context.append(_candidate(source_phase=SOURCE_B3, crop_type="context", path=None, artefact_id="absent"))
    if not any(c.get("source_phase") == SOURCE_B3 and c.get("crop_type") == "detail" for c in detail):
        detail.append(_candidate(source_phase=SOURCE_B3, crop_type="detail", path=None, artefact_id="absent"))

    return {
        "beam_id": beam_id,
        "context_candidates": context,
        "detail_candidates": detail,
    }


__all__ = ["inventory_beam", "population_beam_ids", "sha256_file"]
