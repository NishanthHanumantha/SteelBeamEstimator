"""Anti-hardcoding for D.4. No beam-ID outcome branches."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from .beam_calculator import calculate_beam
from .engineering_adapter import weight_kg

_RUNTIME = (
    "population_loader.py",
    "engineering_adapter.py",
    "group_calculator.py",
    "beam_calculator.py",
    "baseline_loader.py",
    "benchmark_truth_loader.py",
    "accuracy_metrics.py",
    "diameter_metrics.py",
    "contribution_analyzer.py",
    "ambiguity_handler.py",
    "stirrup_adapter.py",
    "spacer_adapter.py",
    "provenance_audit.py",
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


def _field(value, source="VISION"):
    return {
        "value": value,
        "source": source,
        "fallback_used": False,
        "vision_value": value if source == "VISION" else None,
        "deterministic_value": 16 if value == 20 and source == "VISION" else value,
        "conflict_detected": source == "VISION" and value == 20,
        "resolution_reason": "VISION_PREFERRED_VALID",
    }


def sample_bound(beam_id: str = "T01", *, diameter=20, count=2, role="MAIN", origin="MATCHED", ambiguous=False, cut=4000.0) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "geometry": {"available": True, "width_mm": 200.0, "depth_mm": 500.0, "span_mm": 4000.0},
        "groups": [
            {
                "beam_id": beam_id,
                "group_id": "G1",
                "origin": origin,
                "ambiguous": ambiguous,
                "possible_duplicate": False,
                "semantic": {
                    "layer": "TOP",
                    "role": role,
                    "bar_count": count,
                    "diameter": diameter,
                    "specification": f"{count}-Y{diameter}",
                    "support_scope": "FULL_SPAN",
                    "field_records": {
                        "layer": _field("TOP"),
                        "role": _field(role),
                        "bar_count": _field(count),
                        "diameter": _field(diameter),
                        "specification": _field(f"{count}-Y{diameter}"),
                    },
                    "longer_bar_likely_main_hook": "ARCHITECTURE_HOOK_ONLY",
                },
                "engineering_binding": {
                    "binding_status": "AMBIGUOUS" if ambiguous else "BOUND",
                    "instance_cut_length_reference": None if origin == "VISION_ONLY_GROUP" else cut,
                    "beam_geometry_reference": {"span_mm": 4000.0},
                    "section_geometry_reference": {"width_mm": 200.0, "depth_mm": 500.0},
                    "span_reference": {"kind": "FULL_SPAN", "span_mm": 4000.0},
                    "cut_length_rule_reference": "DETERMINISTIC_LONGITUDINAL_CUT_LENGTH_RULE",
                    "development_length_reference": "DETERMINISTIC_DEVELOPMENT_LENGTH_RULE",
                    "hook_bend_reference": "DETERMINISTIC_HOOK_BEND_RULE",
                },
            }
        ],
        "stirrups": [
            {
                "origin": "VISION_ONLY_GROUP",
                "semantic_identification": {"value": "2L-Y8@100C/C", "source": "VISION", "conflict_detected": False},
                "semantic_identification_authority": "VISION_PREFERRED",
                "engineering_calculation_authority": "DETERMINISTIC_ENGINEERING",
            }
        ],
        "spacers": {
            "source": "DETERMINISTIC",
            "groups": [{"physical_group_id": "SP1", "diameter": 12, "bar_count": 2, "cut_length_mm": 120.0, "role": "SPACER"}],
        },
    }


def rename_invariance() -> Dict[str, Any]:
    a = calculate_beam(bound=sample_bound("T01"), r13_model={})
    b = calculate_beam(bound=sample_bound("ZX99"), r13_model={})
    return {"ok": a["groups"][0]["weight_kg"] == b["groups"][0]["weight_kg"] and a["groups"][0]["diameter_mm"] == 20}


def input_order_invariance() -> Dict[str, Any]:
    from .beam_calculator import calculate_population

    b1 = sample_bound("T01")
    b2 = sample_bound("T02", diameter=16, count=3)
    a = calculate_population([b1, b2], {})
    b = calculate_population([b2, b1], {})
    return {"ok": [r["beam_id"] for r in a] == [r["beam_id"] for r in b] == ["T01", "T02"]}


def group_order_invariance() -> Dict[str, Any]:
    bound = sample_bound("T01")
    g2 = deepcopy(bound["groups"][0])
    g2["group_id"] = "G2"
    g2["semantic"]["diameter"] = 16
    g2["semantic"]["field_records"]["diameter"] = _field(16)
    g2["engineering_binding"]["instance_cut_length_reference"] = 3000.0
    a = deepcopy(bound)
    a["groups"] = [bound["groups"][0], g2]
    b = deepcopy(bound)
    b["groups"] = [g2, bound["groups"][0]]
    ca = calculate_beam(bound=a, r13_model={})
    cb = calculate_beam(bound=b, r13_model={})
    wa = round(sum(g["weight_kg"] or 0 for g in ca["groups"]), 4)
    wb = round(sum(g["weight_kg"] or 0 for g in cb["groups"]), 4)
    return {"ok": wa == wb}


def diameter_override_changes_weight() -> Dict[str, Any]:
    a = calculate_beam(bound=sample_bound("T01", diameter=16), r13_model={})
    b = calculate_beam(bound=sample_bound("T01", diameter=20), r13_model={})
    return {"ok": (a["groups"][0]["weight_kg"] or 0) < (b["groups"][0]["weight_kg"] or 0)}


def repeatability() -> Dict[str, Any]:
    bound = sample_bound("T01")
    a = calculate_beam(bound=bound, r13_model={})
    b = calculate_beam(bound=bound, r13_model={})
    return {"ok": json.dumps(a["groups"], sort_keys=True, default=str) == json.dumps(b["groups"], sort_keys=True, default=str)}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    order = input_order_invariance()
    groups = group_order_invariance()
    dia = diameter_override_changes_weight()
    rep = repeatability()
    ok = all(x.get("ok") for x in (guard, rename, order, groups, dia, rep))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "input_order_invariance": order,
        "group_order_invariance": groups,
        "synthetic_diameter_weight_change": dia,
        "repeatability": rep,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = [
    "diameter_override_changes_weight",
    "group_order_invariance",
    "input_order_invariance",
    "rename_invariance",
    "repeatability",
    "run_anti_hardcoding",
    "sample_bound",
    "source_guard",
]
