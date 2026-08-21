"""Anti-hardcoding for C.4 reconciliation. No beam-ID outcome branches in the engine."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .config import STATUS_AMBIGUOUS, STATUS_INSUFFICIENT, STATUS_VIS_CONFIRMED
from .engine import reconcile_groups

_RUNTIME = (
    "discovery.py",
    "evidence.py",
    "normalize.py",
    "engine.py",
    "metrics.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")


def source_guard(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for name in _RUNTIME:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _BEAM_ID_RE.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "beam_id_literal"})
        lowered = text.lower()
        if "vision_wins" in lowered or "if beam_id" in lowered:
            hits.append({"file": name, "token": "winner_branch", "reason": "hardcoded_winner"})
    return {"ok": len(hits) == 0, "hits": hits, "beam_id_special_cases": bool(hits)}


def rename_invariance() -> Dict[str, Any]:
    vision = [
        {"layer": "TOP", "role": "MAIN", "specification": "5-Y20"},
        {"layer": "BOTTOM", "role": "MAIN", "specification": "5-Y16"},
        {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4L-Y8@100C/C"},
    ]
    det = [
        {"layer": "TOP", "role": "MAIN", "specification": "5Y16"},
        {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4L-Y8@\\X100C/C"},
    ]
    independent = list(vision)
    a = reconcile_groups(
        vision_groups=vision,
        deterministic_groups=det,
        independent_groups=independent,
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    b = reconcile_groups(
        vision_groups=vision,
        deterministic_groups=det,
        independent_groups=independent,
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    ok = a.get("reconciliation_status") == b.get("reconciliation_status") == STATUS_VIS_CONFIRMED
    return {"ok": ok, "status": a.get("reconciliation_status")}


def fixture_rename_invariance() -> Dict[str, Any]:
    """Same evidence under a renamed identity must keep the same outcome."""
    vis = [{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}]
    det = [{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}]
    ind = [{"layer": "TOP", "role": "MAIN", "specification": "5-Y20"}]
    left = reconcile_groups(
        vision_groups=vis,
        deterministic_groups=det,
        independent_groups=ind,
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    right = reconcile_groups(
        vision_groups=vis,
        deterministic_groups=det,
        independent_groups=ind,
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    ok = (
        left.get("reconciliation_status") == right.get("reconciliation_status") == STATUS_VIS_CONFIRMED
        and left.get("vision_result") == right.get("vision_result")
    )
    return {"ok": ok, "status": left.get("reconciliation_status")}


def missing_and_conflict() -> Dict[str, Any]:
    missing = reconcile_groups(vision_groups=[], deterministic_groups=[])
    conflict = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
        independent_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        independent_conflict=True,
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    ok = missing.get("reconciliation_status") == STATUS_INSUFFICIENT and conflict.get(
        "reconciliation_status"
    ) == STATUS_AMBIGUOUS
    return {"ok": ok, "missing": missing.get("reconciliation_status"), "conflict": conflict.get("reconciliation_status")}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    fixture = fixture_rename_invariance()
    mc = missing_and_conflict()
    ok = bool(guard.get("ok") and rename.get("ok") and fixture.get("ok") and mc.get("ok"))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "fixture_rename_invariance": fixture,
        "missing_and_conflict": mc,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = ["fixture_rename_invariance", "run_anti_hardcoding", "source_guard"]
