"""Anti-hardcoding for E.3. No beam-ID outcome branches. No hardcoded population sizes."""
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

from .artefact_reuse import decide_action, row_reusable
from .config import KIND_FALLBACK, KIND_HYBRID, PROV_NEW, PROV_NOT_AVAILABLE, PROV_RETRIED, PROV_REUSED
from .pooling import pool_kpi_blocks, weight_accuracy_percent
from .sets import classify_folder_name, is_excluded_set

_RUNTIME = (
    "population.py",
    "visual_sources.py",
    "artefact_reuse.py",
    "vision_loop.py",
    "pooling.py",
    "metrics.py",
    "sets.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_IF_BEAM = re.compile(r"if\s+(beam_id|beam)\s*==")
_HARD_COUNTS = re.compile(r"\b(143|187|76|63|61|605|4169)\b")


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


def first_set_excluded() -> Dict[str, Any]:
    return {
        "ok": is_excluded_set("First")
        and classify_folder_name("First Set Drawings") == "First"
        and not is_excluded_set("Second")
    }


def pooled_not_average() -> Dict[str, Any]:
    a = {
        "beam_n": 1,
        "beam_d": 4,
        "bar_n": 1,
        "bar_d": 4,
        "correct_n": 1,
        "correct_d": 1,
        "diameter_n": 1,
        "diameter_d": 1,
        "hybrid_total_kg": 90,
        "benchmark_total_kg": 100,
    }
    b = {
        "beam_n": 2,
        "beam_d": 2,
        "bar_n": 2,
        "bar_d": 2,
        "correct_n": 2,
        "correct_d": 2,
        "diameter_n": 2,
        "diameter_d": 2,
        "hybrid_total_kg": 10,
        "benchmark_total_kg": 1000,
    }
    pooled = pool_kpi_blocks([a, b])
    beam_ok = abs(float(pooled["beam_identification_percent"]) - 50.0) < 1e-9
    avg_steel = (
        float(weight_accuracy_percent(90, 100)) + float(weight_accuracy_percent(10, 1000))
    ) / 2.0
    steel_ok = abs(float(pooled["weight_accuracy_percent"]) - float(weight_accuracy_percent(100, 1100))) < 1e-9
    not_avg = abs(float(pooled["weight_accuracy_percent"]) - avg_steel) > 1.0
    return {"ok": beam_ok and steel_ok and not_avg, "pooled": pooled, "unweighted_steel_mean": avg_steel}


def e2_reuse_and_reject() -> Dict[str, Any]:
    good = {
        "complete": True,
        "called": True,
        "semantic_usable": True,
        "extracted": {"usable": True},
        "visual": {"sha256": "abc"},
    }
    stale = dict(good)
    stale["visual"] = {"sha256": "old"}
    api = {
        "complete": True,
        "called": True,
        "semantic_usable": False,
        "failure_category": "API_FAILED",
        "visual": {"sha256": "abc"},
    }
    reuse = decide_action(
        set_key="Fifth",
        eligible=True,
        e3_row=None,
        e2_row=good,
        source_sha="abc",
        historical=None,
        e2_reuse_allowed=True,
    )
    reject = decide_action(
        set_key="Fifth",
        eligible=True,
        e3_row=None,
        e2_row=stale,
        source_sha="new",
        historical=None,
        e2_reuse_allowed=True,
    )
    blocked = decide_action(
        set_key="Second",
        eligible=False,
        e3_row=None,
        e2_row=None,
        source_sha=None,
        historical=None,
        e2_reuse_allowed=False,
    )
    live = decide_action(
        set_key="Fourth",
        eligible=True,
        e3_row=None,
        e2_row=None,
        source_sha="x",
        historical=None,
        e2_reuse_allowed=False,
    )
    retry = decide_action(
        set_key="Fourth",
        eligible=True,
        e3_row=None,
        e2_row=None,
        source_sha="x",
        historical={"error_class": "api_failure", "usable": False},
        e2_reuse_allowed=False,
    )
    return {
        "ok": row_reusable(good, source_sha="abc")
        and (not row_reusable(stale, source_sha="new"))
        and (not row_reusable(api, source_sha="abc"))
        and reuse["provenance"] == PROV_REUSED
        and reject["action"] == "LIVE"
        and blocked["provenance"] == PROV_NOT_AVAILABLE
        and live["provenance"] == PROV_NEW
        and retry["provenance"] == PROV_RETRIED
    }


def hybrid_vs_fallback_label() -> Dict[str, Any]:
    vis = sample_execute("T01", diameter=20, vision_usable=True)
    det = sample_execute("T01")
    return {"ok": vis.get("provenance_kind") == KIND_HYBRID and det.get("provenance_kind") == KIND_FALLBACK}


def vision_main_extra_authority() -> Dict[str, Any]:
    vis = sample_execute("T01", diameter=20, vision_usable=True)
    groups = vis.get("groups") or vis.get("hybrid_semantic", {}).get("reinforcement_groups") or []
    roles = []
    hybrid = vis.get("hybrid_semantic") if isinstance(vis.get("hybrid_semantic"), dict) else {}
    for g in hybrid.get("reinforcement_groups") or []:
        rec = g.get("role") if isinstance(g.get("role"), dict) else {}
        roles.append(rec.get("value") or rec.get("vision_value") or g.get("role"))
    return {"ok": vis.get("vision_used") is True and vis.get("provenance_kind") == KIND_HYBRID, "roles": roles}


def spacer_preserved() -> Dict[str, Any]:
    vis = sample_execute("T01", diameter=20, vision_usable=True)
    det = sample_execute("T01")
    vs = float(vis.get("spacer_weight_kg") or 0)
    ds = float(det.get("spacer_weight_kg") or 0)
    return {"ok": vs > 0 and abs(vs - ds) < 1e-6, "vision_spacer_kg": vs, "det_spacer_kg": ds}


def ambiguous_not_forced() -> Dict[str, Any]:
    vis = sample_execute("T01", diameter=20, vision_usable=True)
    hybrid = vis.get("hybrid_semantic") if isinstance(vis.get("hybrid_semantic"), dict) else {}
    forced = 0
    for g in hybrid.get("reinforcement_groups") or []:
        if g.get("forced") is True or g.get("force_match") is True:
            forced += 1
    withheld = vis.get("withheld_ambiguous") or hybrid.get("withheld") or []
    return {"ok": forced == 0, "forced": forced, "withheld": len(withheld) if isinstance(withheld, list) else withheld}


def duplicate_discovery_stable() -> Dict[str, Any]:
    a = classify_folder_name("qa2_Fourth_Set_Drawings_20260806_121946")
    b = classify_folder_name("qa2_Fourth_Set_Drawings_20260806_121946")
    return {"ok": a == b == "Fourth"}


def run_anti_hardcoding(*, package_dir: Path, tmp: Path) -> Dict[str, Any]:
    parts = [
        source_guard(package_dir),
        first_set_excluded(),
        pooled_not_average(),
        e2_reuse_and_reject(),
        hybrid_vs_fallback_label(),
        vision_main_extra_authority(),
        spacer_preserved(),
        ambiguous_not_forced(),
        duplicate_discovery_stable(),
        rename_invariance(),
        input_order_invariance(),
        group_order_invariance(),
        vision_diameter_changes_weight(),
    ]
    return {"ok": all(p.get("ok") for p in parts), "parts": parts}


__all__ = [
    "ambiguous_not_forced",
    "duplicate_discovery_stable",
    "e2_reuse_and_reject",
    "first_set_excluded",
    "hybrid_vs_fallback_label",
    "pooled_not_average",
    "run_anti_hardcoding",
    "source_guard",
    "spacer_preserved",
    "vision_main_extra_authority",
]
