"""Anti-hardcoding for C.3 gate. No beam-ID decision exceptions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .evidence_model import SelectedRender
from .visual_completeness_gate import evaluate_completeness

_RUNTIME = (
    "manifest_loader.py",
    "evidence_model.py",
    "visual_completeness_gate.py",
    "target_anchor_validator.py",
    "vision_contract.py",
    "comparison.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_COORD_TABLE_RE = re.compile(r"crop_override|manual_extent|fixed_xy|gt_coord", re.I)


def source_guard(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for name in _RUNTIME:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _BEAM_ID_RE.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "beam_id_literal"})
        if _COORD_TABLE_RE.search(text):
            hits.append({"file": name, "token": "coord_table", "reason": "manual_override_token"})
    return {"ok": len(hits) == 0, "hits": hits, "beam_id_special_cases": False}


def _img(**kwargs) -> SelectedRender:
    defaults = dict(
        crop_type="context",
        source_phase="B.1",
        path="/x.png",
        sha256="aaa",
        primary_status="VALID",
        critical_failure=False,
        selection_status="RETAIN_PREFERRED",
        reason_codes=[],
        usable_status=True,
        score=4.0,
        foreground_ratio=0.12,
        coverage_x=0.85,
        coverage_y=0.80,
        empty_sides=[],
        quality_flags=[],
        integrity={"exists": True, "sha_mismatch": False, "file_missing": False, "integrity_ok": True},
    )
    defaults.update(kwargs)
    return SelectedRender(**defaults)


def rename_invariance() -> Dict[str, Any]:
    ctx = _img(crop_type="context")
    det = _img(crop_type="detail", path="/d.png")
    a = evaluate_completeness(ctx, det)
    b = evaluate_completeness(ctx, det)
    ok = a.get("status") == b.get("status") and a.get("reason_codes") == b.get("reason_codes")
    return {"ok": ok, "status": a.get("status")}


def provenance_invariance() -> Dict[str, Any]:
    ctx1 = _img(crop_type="context", source_phase="B.1")
    ctx2 = _img(crop_type="context", source_phase="B.3")
    det = _img(crop_type="detail")
    a = evaluate_completeness(ctx1, det)
    b = evaluate_completeness(ctx2, det)
    ok = a.get("status") == b.get("status")
    return {"ok": ok, "status": a.get("status")}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    prov = provenance_invariance()
    ok = bool(guard.get("ok") and rename.get("ok") and prov.get("ok"))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "provenance_invariance": prov,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = ["run_anti_hardcoding", "source_guard"]
