"""Anti-hardcoding for D.3. No beam-ID outcome branches."""
from __future__ import annotations

import json
import random
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from .engineering_rule_binder import default_rule_catalog
from .hybrid_binding_engine import bind_beam, bind_population
from .provenance import semantic_snapshot

_RUNTIME = (
    "input_loader.py",
    "hybrid_binding_engine.py",
    "geometry_binder.py",
    "support_binder.py",
    "engineering_rule_binder.py",
    "compatibility_validator.py",
    "binding_status.py",
    "provenance.py",
    "diagnostics.py",
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


def _field(value: Any, source: str = "VISION") -> Dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "confidence": 0.9,
        "fallback_used": False,
        "vision_value": value if source == "VISION" else None,
        "deterministic_value": value if source == "DETERMINISTIC" else None,
        "conflict_detected": False,
        "resolution_reason": "VISION_PREFERRED_VALID" if source == "VISION" else "DETERMINISTIC_ONLY_GROUP",
        "validation_reason": "VISION_ACCEPTED",
    }


def _group(
    *,
    gid: str,
    origin: str,
    layer: str = "TOP",
    role: str = "MAIN",
    count: int = 5,
    diameter: int = 20,
    spec: str = "5-Y20",
    scope: str = "FULL_SPAN",
    cut=None,
    vision_id: str = None,
    det_id: str = None,
    source: str = None,
) -> Dict[str, Any]:
    src = source or ("DETERMINISTIC" if origin == "DETERMINISTIC_ONLY_GROUP" else "VISION")
    return {
        "group_id": gid,
        "origin": origin,
        "layer": _field(layer, src),
        "role": _field(role, src),
        "bar_count": _field(count, src),
        "diameter": _field(diameter, src),
        "specification": _field(spec, src),
        "support_scope": _field(scope, src),
        "deterministic_engineering": {
            "geometry_reference": "DETERMINISTIC_AUTHORITY",
            "cut_length_reference": cut if cut is not None else "UNAVAILABLE",
            "development_length_reference": "DETERMINISTIC_AUTHORITY",
            "anchorage_reference": "DETERMINISTIC_AUTHORITY",
            "hook_reference": "DETERMINISTIC_AUTHORITY",
            "source": "DETERMINISTIC",
            "authority": "DETERMINISTIC_ENGINEERING",
        },
        "relative_span_length": "LONGER",
        "longer_bar_likely_main_hook": "ARCHITECTURE_HOOK_ONLY",
        "provenance": {
            "vision_available": origin != "DETERMINISTIC_ONLY_GROUP",
            "deterministic_available": origin != "VISION_ONLY_GROUP",
            "conflict_detected": False,
            "resolution_reason": origin,
            "vision_id": vision_id or gid,
            "deterministic_id": det_id,
            "match_score": 10 if origin == "MATCHED" else None,
        },
    }


def sample_model() -> Dict[str, Any]:
    return {
        "geometry": {
            "width_mm": 200.0,
            "depth_mm": 500.0,
            "effective_span_mm": 4000.0,
            "clear_span_mm": 4000.0,
            "geometry_source": "FRAMING_PLAN_LINE",
        },
        "support_zones": [
            {"support_id": "SL", "support_type": "LEFT_SUPPORT", "position_fraction": 0.0},
            {"support_id": "SR", "support_type": "RIGHT_SUPPORT", "position_fraction": 1.0},
        ],
        "development_length_regions": [{"region_id": "DL1", "location": "LEFT_SUPPORT"}],
        "stirrups": [{"specification": "2L-Y8"}],
        "spacer_bars": [{"specification": "2Y12"}],
    }


def sample_hybrid(beam_id: str = "T01", groups: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    gs = groups or [_group(gid="G1", origin="MATCHED", cut=7200, det_id="D1")]
    return {
        "beam_id": beam_id,
        "target_identity": _field(beam_id, "VISION"),
        "reinforcement_groups": gs,
        "stirrups": {
            "items": [
                {
                    "origin": "VISION_ONLY_GROUP",
                    "semantic_identification": _field("2L-Y8@100C/C"),
                    "engineering_calculation_reference": {
                        "source": "DETERMINISTIC",
                        "authority": "DETERMINISTIC_ENGINEERING",
                        "cut_length_mm": "UNAVAILABLE",
                    },
                }
            ],
            "semantic_identification_authority": "VISION_PREFERRED",
            "engineering_calculation_authority": "DETERMINISTIC_ENGINEERING",
        },
        "spacers": {
            "source": "DETERMINISTIC",
            "authority": "DETERMINISTIC_ENGINEERING",
            "groups": [{"physical_group_id": "SP1", "role": "SPACER", "diameter": 12}],
        },
        "group_matching": {
            "matched": sum(1 for g in gs if g.get("origin") == "MATCHED"),
            "vision_only": sum(1 for g in gs if g.get("origin") == "VISION_ONLY_GROUP"),
            "deterministic_only": sum(1 for g in gs if g.get("origin") == "DETERMINISTIC_ONLY_GROUP"),
            "ambiguous": 0,
            "possible_duplicates": [],
            "pairs": [],
            "ambiguous_records": [],
        },
        "possible_duplicate_groups": [],
        "successfully_resolved": True,
    }


def _bind(beam_id: str, hybrid: Dict[str, Any], model: Dict[str, Any] = None, rules=None):
    catalog = {beam_id: deepcopy(model if model is not None else sample_model())}
    return bind_beam(hybrid=hybrid, catalog=catalog, rule_catalog=rules if rules is not None else default_rule_catalog())


def rename_invariance() -> Dict[str, Any]:
    groups = [_group(gid="G1", origin="MATCHED", cut=7200), _group(gid="G2", origin="VISION_ONLY_GROUP", layer="BOTTOM", spec="3-Y16", count=3, diameter=16)]
    a = _bind("T01", sample_hybrid("T01", groups))
    b = _bind("ZX99", sample_hybrid("ZX99", deepcopy(groups)))
    sa = [(g["origin"], g["engineering_binding"]["binding_status"], g["semantic"]["diameter"], g["semantic"]["role"]) for g in a["groups"]]
    sb = [(g["origin"], g["engineering_binding"]["binding_status"], g["semantic"]["diameter"], g["semantic"]["role"]) for g in b["groups"]]
    return {"ok": sa == sb}


def input_order_invariance() -> Dict[str, Any]:
    h1 = sample_hybrid("T01", [_group(gid="G1", origin="MATCHED", cut=1)])
    h2 = sample_hybrid("T02", [_group(gid="G1", origin="VISION_ONLY_GROUP")])
    catalog = {"T01": sample_model(), "T02": sample_model()}
    a = bind_population(hybrids=[h1, h2], catalog=catalog)
    b = bind_population(hybrids=[h2, h1], catalog=catalog)
    return {"ok": [r["beam_id"] for r in a] == [r["beam_id"] for r in b] == ["T01", "T02"]}


def group_order_invariance() -> Dict[str, Any]:
    g1 = _group(gid="G1", origin="MATCHED", cut=7200)
    g2 = _group(gid="G2", origin="VISION_ONLY_GROUP", layer="BOTTOM", spec="3-Y16", count=3, diameter=16, role="EXTRA")
    a = _bind("T01", sample_hybrid("T01", [g1, g2]))
    b = _bind("T01", sample_hybrid("T01", [g2, g1]))
    ka = [(g["group_id"], g["engineering_binding"]["binding_status"]) for g in a["groups"]]
    kb = [(g["group_id"], g["engineering_binding"]["binding_status"]) for g in b["groups"]]
    return {"ok": ka == kb}


def det_ref_order_invariance() -> Dict[str, Any]:
    model_a = sample_model()
    model_b = sample_model()
    random.Random(0).shuffle(model_b["support_zones"])
    g = _group(gid="G1", origin="MATCHED", scope="LEFT_SUPPORT", cut=1000)
    a = _bind("T01", sample_hybrid("T01", [g]), model_a)
    b = _bind("T01", sample_hybrid("T01", [g]), model_b)
    ra = (a["groups"][0]["engineering_binding"]["support_reference"] or {}).get("support_id")
    rb = (b["groups"][0]["engineering_binding"]["support_reference"] or {}).get("support_id")
    return {"ok": ra == rb == "SL" and a["groups"][0]["engineering_binding"]["binding_status"] == b["groups"][0]["engineering_binding"]["binding_status"]}


def repeatability() -> Dict[str, Any]:
    hybrid = sample_hybrid("T01", [_group(gid="G1", origin="MATCHED", cut=7200), _group(gid="G2", origin="DETERMINISTIC_ONLY_GROUP", layer="BOTTOM")])
    a = _bind("T01", hybrid)
    b = _bind("T01", hybrid)
    sa = json.dumps(a["groups"], sort_keys=True, default=str)
    sb = json.dumps(b["groups"], sort_keys=True, default=str)
    return {"ok": sa == sb}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    order = input_order_invariance()
    groups = group_order_invariance()
    refs = det_ref_order_invariance()
    rep = repeatability()
    ok = all(x.get("ok") for x in (guard, rename, order, groups, refs, rep))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "input_order_invariance": order,
        "group_order_invariance": groups,
        "det_ref_order_invariance": refs,
        "repeatability": rep,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = [
    "det_ref_order_invariance",
    "group_order_invariance",
    "input_order_invariance",
    "rename_invariance",
    "repeatability",
    "run_anti_hardcoding",
    "sample_hybrid",
    "sample_model",
    "source_guard",
]
