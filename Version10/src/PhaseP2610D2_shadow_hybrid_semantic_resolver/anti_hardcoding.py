"""Anti-hardcoding for D.2. No beam-ID outcome branches."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_normalizer import (
    extract_deterministic_groups,
    extract_vision_payload,
)

from .resolver import resolve_hybrid_beam

_RUNTIME = (
    "discovery.py",
    "matching.py",
    "canonical.py",
    "resolver.py",
    "audit.py",
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
    return {"ok": len(hits) == 0, "hits": hits, "beam_id_special_cases": bool(hits)}


def _vis(groups, stirrups=None, tid="T01", conf=0.95, usable=True, identified=True):
    return extract_vision_payload(
        {
            "usable": usable,
            "target_beam_id": tid,
            "target_identified": identified,
            "association_confidence": conf,
            "groups": groups,
            "stirrups": stirrups or [],
        }
    )


def rename_invariance() -> Dict[str, Any]:
    vis = _vis([{"layer": "TOP", "role_hypothesis": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.9}])
    det = extract_deterministic_groups(
        [{"physical_layer": "TOP", "reinforcement_role": "EXTRA", "specification": "5Y16", "count": 4, "diameter": 16, "family": "LONGITUDINAL"}]
    )
    a = resolve_hybrid_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={})
    b = resolve_hybrid_beam(beam_id="ZX99", vision=vis, deterministic=det, source_provenance={})
    ga, gb = a["reinforcement_groups"][0], b["reinforcement_groups"][0]
    ok = (
        ga["diameter"]["value"] == gb["diameter"]["value"] == 20
        and ga["role"]["value"] == gb["role"]["value"] == "MAIN"
        and a["target_identity"]["source"] == b["target_identity"]["source"]
    )
    return {"ok": ok}


def ordering_invariance() -> Dict[str, Any]:
    g1 = {"layer": "TOP", "role_hypothesis": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.9}
    g2 = {"layer": "BOTTOM", "role_hypothesis": "MAIN", "spec": "3-Y16", "bar_count": 3, "confidence": 0.9}
    d1 = {"physical_layer": "BOTTOM", "reinforcement_role": "MAIN", "specification": "3Y16", "count": 3, "diameter": 16, "family": "LONGITUDINAL"}
    d2 = {"physical_layer": "TOP", "reinforcement_role": "MAIN", "specification": "5Y20", "count": 5, "diameter": 20, "family": "LONGITUDINAL"}
    ra = resolve_hybrid_beam(beam_id="T01", vision=_vis([g1, g2]), deterministic=extract_deterministic_groups([d1, d2]), source_provenance={})
    rb = resolve_hybrid_beam(beam_id="T01", vision=_vis([g2, g1]), deterministic=extract_deterministic_groups([d2, d1]), source_provenance={})

    def keys(res):
        return sorted((g["layer"]["value"], g["bar_count"]["value"], g["diameter"]["value"]) for g in res["reinforcement_groups"])

    return {"ok": keys(ra) == keys(rb) and len(ra["reinforcement_groups"]) == 2}


def repeatability() -> Dict[str, Any]:
    vis = _vis(
        [
            {"layer": "TOP", "role_hypothesis": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.9},
            {"layer": "BOTTOM", "role_hypothesis": "EXTRA", "spec": "3-Y16", "bar_count": 3, "confidence": 0.9},
        ]
    )
    det = extract_deterministic_groups(
        [
            {"physical_layer": "TOP", "reinforcement_role": "MAIN", "specification": "5Y16", "count": 5, "diameter": 16, "family": "LONGITUDINAL"},
            {"physical_layer": "BOTTOM", "reinforcement_role": "MAIN", "specification": "3Y16", "count": 3, "diameter": 16, "family": "LONGITUDINAL"},
        ]
    )
    a = resolve_hybrid_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={})
    b = resolve_hybrid_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={})
    sa = json.dumps(a["reinforcement_groups"], sort_keys=True, default=str)
    sb = json.dumps(b["reinforcement_groups"], sort_keys=True, default=str)
    return {"ok": sa == sb}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    order = ordering_invariance()
    rep = repeatability()
    ok = bool(guard.get("ok") and rename.get("ok") and order.get("ok") and rep.get("ok"))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "ordering_invariance": order,
        "repeatability": rep,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = ["ordering_invariance", "rename_invariance", "repeatability", "run_anti_hardcoding", "source_guard"]
