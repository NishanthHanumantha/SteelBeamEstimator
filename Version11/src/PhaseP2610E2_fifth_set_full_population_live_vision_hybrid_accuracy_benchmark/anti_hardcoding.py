"""Anti-hardcoding for E.2. No beam-ID outcome branches. No hardcoded population sizes."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.anti_hardcoding import (
    group_order_invariance,
    input_order_invariance,
    rename_invariance,
    sample_execute,
    vision_diameter_changes_weight,
)

from .artefact_reuse import decide_action, e2_result_reusable, historical_failure_eligible
from .checkpoint import load_checkpoint, write_checkpoint
from .config import KIND_HYBRID, PROV_BLOCKED, PROV_NEW, PROV_RETRIED, PROV_REUSED, STATUS_NOT_READY, STATUS_READY
from .eligibility import classify_eligibility
from .visual_sources import _is_fifth_path

_RUNTIME = (
    "population.py",
    "visual_sources.py",
    "eligibility.py",
    "live_caller.py",
    "artefact_reuse.py",
    "checkpoint.py",
    "vision_loop.py",
    "subset_kpis.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_IF_BEAM = re.compile(r"if\s+(beam_id|beam)\s*==")
_HARD_COUNTS = re.compile(r"\b(143|187)\b")


def source_guard(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for name in _RUNTIME:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _BEAM_ID_RE.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "beam_id_literal"})
        for m in _IF_BEAM.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "beam_id_branch"})
        for m in _HARD_COUNTS.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "hardcoded_population_count"})
    return {"ok": len(hits) == 0, "hits": hits, "beam_id_special_cases": bool(hits)}


def other_set_excluded() -> Dict[str, Any]:
    fourth = Path("C:/data/output/PhaseQA30_unseen_benchmark/Fourth_Set_Drawings/RenderedCrops/shared_renders/x_render.png")
    fifth = Path("C:/data/output/PhaseQA30_unseen_benchmark/Fifth_Set_Drawings/RenderedCrops/shared_renders/x_render.png")
    return {"ok": (not _is_fifth_path(fourth)) and _is_fifth_path(fifth)}


def historical_api_retry() -> Dict[str, Any]:
    hist = {"usable": False, "error_class": "api_failure", "unusable_reason": "API_FAILURE"}
    return {"ok": historical_failure_eligible(hist) is True}


def reuse_and_stale() -> Dict[str, Any]:
    good = {"complete": True, "called": True, "semantic_usable": True, "visual": {"sha256": "abc"}}
    stale = {"complete": True, "called": True, "semantic_usable": True, "visual": {"sha256": "old"}}
    api = {"complete": True, "called": True, "semantic_usable": False, "failure_category": "API_FAILED", "visual": {"sha256": "abc"}}
    return {
        "ok": e2_result_reusable(good, source_sha="abc")
        and (not e2_result_reusable(stale, source_sha="new"))
        and (not e2_result_reusable(api, source_sha="abc"))
    }


def eligibility_policy() -> Dict[str, Any]:
    ready = classify_eligibility(STATUS_READY)
    blocked = classify_eligibility(STATUS_NOT_READY)
    return {"ok": ready.get("eligible") is True and blocked.get("eligible") is False and blocked.get("blocked") is True}


def checkpoint_resume(tmp: Path) -> Dict[str, Any]:
    ids = ["T01", "T02", "ZX99"]
    write_checkpoint(tmp, beam_ids=ids, completed_ids=["T01"], status="IN_PROGRESS")
    ck = load_checkpoint(tmp)
    return {"ok": ck.get("complete") is False and ck.get("pending_ids") == ["T02", "ZX99"]}


def decide_paths() -> Dict[str, Any]:
    blocked = decide_action(eligible=False, e2_row=None, source_sha=None, historical=None)
    fresh = decide_action(eligible=True, e2_row=None, source_sha="x", historical=None)
    retry = decide_action(eligible=True, e2_row=None, source_sha="x", historical={"error_class": "api_failure", "usable": False})
    reuse = decide_action(
        eligible=True,
        e2_row={"complete": True, "called": True, "semantic_usable": True, "visual": {"sha256": "x"}},
        source_sha="x",
        historical=None,
    )
    return {
        "ok": blocked["provenance"] == PROV_BLOCKED
        and fresh["provenance"] == PROV_NEW
        and retry["provenance"] == PROV_RETRIED
        and reuse["provenance"] == PROV_REUSED
    }


def hybrid_vs_fallback_label() -> Dict[str, Any]:
    vis = sample_execute("T01", diameter=20, vision_usable=True)
    det = sample_execute("T01")
    return {"ok": vis.get("provenance_kind") == KIND_HYBRID and det.get("vision_used") is False}


def run_anti_hardcoding(*, package_dir: Path, tmp: Path) -> Dict[str, Any]:
    parts = [
        source_guard(package_dir),
        other_set_excluded(),
        historical_api_retry(),
        reuse_and_stale(),
        eligibility_policy(),
        checkpoint_resume(tmp),
        decide_paths(),
        rename_invariance(),
        input_order_invariance(),
        group_order_invariance(),
        vision_diameter_changes_weight(),
        hybrid_vs_fallback_label(),
    ]
    return {"ok": all(p.get("ok") for p in parts), "parts": parts}


__all__ = [
    "checkpoint_resume",
    "decide_paths",
    "eligibility_policy",
    "historical_api_retry",
    "hybrid_vs_fallback_label",
    "other_set_excluded",
    "reuse_and_stale",
    "run_anti_hardcoding",
    "sample_execute",
    "source_guard",
]
