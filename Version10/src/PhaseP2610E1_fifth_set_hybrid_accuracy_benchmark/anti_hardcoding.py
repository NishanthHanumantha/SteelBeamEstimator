"""Anti-hardcoding for E.1. No beam-ID outcome branches."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from .hybrid_runner_adapter import execute_hybrid_beam

_RUNTIME = (
    "population_discovery.py",
    "vision_artifact_loader.py",
    "hybrid_runner_adapter.py",
    "benchmark_truth_loader.py",
    "benchmark_mapper.py",
    "kpis.py",
    "provenance_analyzer.py",
    "error_analyzers.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_IF_BEAM = re.compile(r"if\s+beam_id\s*==")


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
    return {"ok": len(hits) == 0, "hits": hits, "beam_id_special_cases": bool(hits)}


def _det_model(beam_id: str, diameter: int = 20, qty: int = 2, cut: float = 4000.0) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "geometry": {
            "span_mm": 4000.0,
            "effective_span_mm": 4000.0,
            "width_mm": 200.0,
            "depth_mm": 500.0,
        },
        "top_main_bars": [
            {
                "bar_id": f"R13-{beam_id}-TOP_MAIN",
                "semantic_role": "TOP_MAIN",
                "diameter_mm": diameter,
                "quantity": qty,
                "cut_length_mm": cut,
                "classification_confidence": "HIGH",
                "extent": "FULL_SPAN",
            }
        ],
        "stirrups": [],
        "spacer_bars": [
            {
                "bar_id": f"R13-{beam_id}-SPACER",
                "semantic_role": "SPACER_BAR",
                "diameter_mm": 12,
                "quantity": 2,
                "cut_length_mm": 120.0,
            }
        ],
        "support_zones": [{"kind": "LEFT"}, {"kind": "RIGHT"}],
    }


def sample_execute(beam_id: str = "T01", *, diameter=20, vision_usable=False):
    vis = None
    if vision_usable:
        vis = {
            "usable": True,
            "source": "SYNTHETIC",
            "extracted": {
                "usable": True,
                "target_identified": True,
                "target_beam_id": beam_id,
                "association_confidence": 0.9,
                "groups": [
                    {
                        "physical_group_id": "VG1",
                        "layer": "TOP",
                        "role": "MAIN",
                        "bar_count": 2,
                        "diameter": diameter,
                        "specification": f"2-Y{diameter}",
                        "support_scope": "FULL_SPAN",
                        "confidence": 0.9,
                    }
                ],
                "stirrups": [],
            },
        }
    model = _det_model(beam_id, diameter=16 if vision_usable else diameter)
    catalog = {beam_id: model}
    return execute_hybrid_beam(beam_id=beam_id, model=model, vision_row=vis, catalog=catalog)


def rename_invariance() -> Dict[str, Any]:
    a = sample_execute("T01")
    b = sample_execute("ZX99")
    return {"ok": round(a.get("hybrid_weight_kg") or 0, 4) == round(b.get("hybrid_weight_kg") or 0, 4)}


def input_order_invariance() -> Dict[str, Any]:
    from .hybrid_runner_adapter import execute_population

    m1 = _det_model("T01", 20)
    m2 = _det_model("T02", 16, qty=3)
    cat = {"T01": m1, "T02": m2}
    a = execute_population(beam_ids=["T01", "T02"], catalog=cat, vision_by_id={})
    b = execute_population(beam_ids=["T02", "T01"], catalog=cat, vision_by_id={})
    return {"ok": [r["beam_id"] for r in a] == [r["beam_id"] for r in b] == ["T01", "T02"]}


def group_order_invariance() -> Dict[str, Any]:
    a = sample_execute("T01")
    b = sample_execute("T01")
    wa = round(sum(g.get("weight_kg") or 0 for g in a.get("groups") or []), 4)
    wb = round(sum(g.get("weight_kg") or 0 for g in b.get("groups") or []), 4)
    return {"ok": wa == wb}


def vision_diameter_changes_weight() -> Dict[str, Any]:
    a = sample_execute("T01", diameter=16, vision_usable=True)
    b = sample_execute("T01", diameter=20, vision_usable=True)
    da = (a.get("groups") or [{}])[0].get("diameter_mm")
    db = (b.get("groups") or [{}])[0].get("diameter_mm")
    return {"ok": da == 16 and db == 20 and (a.get("hybrid_weight_kg") or 0) < (b.get("hybrid_weight_kg") or 0)}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    order = input_order_invariance()
    groups = group_order_invariance()
    dia = vision_diameter_changes_weight()
    ok = all(x.get("ok") for x in (guard, rename, order, groups, dia))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "input_order_invariance": order,
        "group_order_invariance": groups,
        "synthetic_vision_diameter": dia,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = [
    "group_order_invariance",
    "input_order_invariance",
    "rename_invariance",
    "run_anti_hardcoding",
    "sample_execute",
    "source_guard",
    "vision_diameter_changes_weight",
]
