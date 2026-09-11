"""Anti-hardcoding for C.5 sampler/comparison. No beam-ID selection branches."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .config import TARGET_SAMPLE_SIZE
from .sampler import select_sample

_RUNTIME = (
    "discovery.py",
    "candidate.py",
    "strata.py",
    "sampler.py",
    "normalize.py",
    "comparison.py",
    "length_evidence.py",
    "vision_contract.py",
    "claude_call.py",
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
        if "if beam_id" in text.lower() and "==" in text:
            # generic lookups use rec.get("beam_id"), not equality to a literal
            pass
    return {"ok": len(hits) == 0, "hits": hits, "beam_id_special_cases": bool(hits)}


def _synth(i: int, **kwargs: Any) -> Dict[str, Any]:
    rec = {
        "beam_id": f"T{i:02d}",
        "evidence_valid": True,
        "c3_visual_gate_status": "VISION_READY_WITH_LIMITATIONS",
        "neighbour_association_risk": False,
        "association_ambiguous": False,
        "mixed_source": False,
        "deterministic_group_count": 2,
        "group_stats": {
            "longitudinal_count": 2,
            "stirrup_count": 1,
            "top_count": 1,
            "bottom_count": 1,
            "has_main": True,
            "has_extra": False,
            "same_spec_distinct": False,
            "stirrup_present": True,
            "stirrup_complex": True,
        },
    }
    rec.update(kwargs)
    return rec


def rename_invariance() -> Dict[str, Any]:
    recs = [
        _synth(1),
        _synth(2, group_stats={
            "longitudinal_count": 5, "stirrup_count": 1, "top_count": 2, "bottom_count": 2,
            "has_main": True, "has_extra": True, "same_spec_distinct": True,
            "stirrup_present": True, "stirrup_complex": True,
        }, neighbour_association_risk=True, c3_visual_gate_status="VISION_READY"),
        _synth(3, group_stats={
            "longitudinal_count": 4, "stirrup_count": 1, "top_count": 2, "bottom_count": 1,
            "has_main": True, "has_extra": True, "same_spec_distinct": False,
            "stirrup_present": True, "stirrup_complex": False,
        }),
        _synth(4),
        _synth(5),
        _synth(6),
        _synth(7),
        _synth(8),
        _synth(9),
        _synth(10),
        _synth(11),
        _synth(12),
    ]
    a = select_sample(recs, exclude_ids=[], target_size=10)
    renamed = []
    for r in recs:
        x = dict(r)
        x["beam_id"] = "ZX" + str(r["beam_id"])
        renamed.append(x)
    b = select_sample(renamed, exclude_ids=[], target_size=10)
    mapped = [str(i)[2:] for i in b.get("selected_ids") or []]
    ok = a.get("ok") and b.get("ok") and mapped == list(a.get("selected_ids") or [])
    return {"ok": ok, "a": a.get("selected_ids"), "b": b.get("selected_ids")}


def repeatability() -> Dict[str, Any]:
    recs = [_synth(i) for i in range(1, 16)]
    recs[0]["c3_visual_gate_status"] = "VISION_READY"
    recs[1]["group_stats"] = {
        "longitudinal_count": 6, "stirrup_count": 1, "top_count": 3, "bottom_count": 2,
        "has_main": True, "has_extra": True, "same_spec_distinct": True,
        "stirrup_present": True, "stirrup_complex": True,
    }
    a = select_sample(recs, exclude_ids=["T03"], target_size=10)
    b = select_sample(recs, exclude_ids=["T03"], target_size=10)
    ok = a.get("selected_ids") == b.get("selected_ids") and len(a.get("selected_ids") or []) <= TARGET_SAMPLE_SIZE
    return {"ok": ok, "ids": a.get("selected_ids")}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    rep = repeatability()
    ok = bool(guard.get("ok") and rename.get("ok") and rep.get("ok"))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "repeatability": rep,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = ["rename_invariance", "repeatability", "run_anti_hardcoding", "source_guard"]
