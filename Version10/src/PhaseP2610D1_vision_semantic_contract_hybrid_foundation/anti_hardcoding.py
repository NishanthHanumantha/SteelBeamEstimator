"""Anti-hardcoding for D.1 resolver. No beam-ID outcome branches."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .resolver import resolve_beam
from .vision_normalizer import extract_deterministic_groups, extract_vision_payload

_RUNTIME = (
    "hybrid_authority_contract.py",
    "normalize.py",
    "vision_normalizer.py",
    "vision_validator.py",
    "matching.py",
    "resolver.py",
    "discovery.py",
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


def _vision(groups, stirrups=None, identified=True, conf=0.95, usable=True, tid="T01"):
    return {
        "usable": usable,
        "target_beam_id": tid,
        "target_identified": identified,
        "association_confidence": conf,
        "groups": groups,
        "stirrups": stirrups or [],
    }


def _det_groups(groups):
    return extract_deterministic_groups(groups)


def rename_invariance() -> Dict[str, Any]:
    vis = extract_vision_payload(
        _vision([{"layer": "TOP", "role_hypothesis": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.9}])
    )
    det = _det_groups([{"physical_layer": "TOP", "reinforcement_role": "EXTRA", "specification": "5Y16", "count": 4, "diameter": 16, "family": "LONGITUDINAL"}])
    a = resolve_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={"p": "a"})
    b = resolve_beam(beam_id="ZX99", vision=vis, deterministic=det, source_provenance={"p": "a"})
    ga, gb = a["groups"][0], b["groups"][0]
    ok = (
        ga["diameter"]["resolved_value"] == gb["diameter"]["resolved_value"] == 20
        and ga["role"]["resolved_value"] == gb["role"]["resolved_value"] == "MAIN"
        and a["target_identity"]["authority_used"] == b["target_identity"]["authority_used"]
    )
    return {"ok": ok}


def ordering_invariance() -> Dict[str, Any]:
    vis_a = extract_vision_payload(
        _vision(
            [
                {"layer": "TOP", "role_hypothesis": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.9},
                {"layer": "BOTTOM", "role_hypothesis": "MAIN", "spec": "3-Y16", "bar_count": 3, "confidence": 0.9},
            ]
        )
    )
    vis_b = extract_vision_payload(
        _vision(
            [
                {"layer": "BOTTOM", "role_hypothesis": "MAIN", "spec": "3-Y16", "bar_count": 3, "confidence": 0.9},
                {"layer": "TOP", "role_hypothesis": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.9},
            ]
        )
    )
    det_a = _det_groups(
        [
            {"physical_layer": "BOTTOM", "reinforcement_role": "MAIN", "specification": "3Y16", "count": 3, "diameter": 16, "family": "LONGITUDINAL"},
            {"physical_layer": "TOP", "reinforcement_role": "MAIN", "specification": "5Y20", "count": 5, "diameter": 20, "family": "LONGITUDINAL"},
        ]
    )
    det_b = _det_groups(list(reversed(det_a["groups"])))
    # extract_deterministic already consumed raw; rebuild
    det_b = _det_groups(
        [
            {"physical_layer": "TOP", "reinforcement_role": "MAIN", "specification": "5Y20", "count": 5, "diameter": 20, "family": "LONGITUDINAL"},
            {"physical_layer": "BOTTOM", "reinforcement_role": "MAIN", "specification": "3Y16", "count": 3, "diameter": 16, "family": "LONGITUDINAL"},
        ]
    )
    ra = resolve_beam(beam_id="T01", vision=vis_a, deterministic=det_a, source_provenance={})
    rb = resolve_beam(beam_id="T01", vision=vis_b, deterministic=det_b, source_provenance={})

    def keyset(res):
        return sorted(
            (
                g["layer"]["resolved_value"],
                g["specification"]["resolved_value"] if isinstance(g["specification"]["resolved_value"], str) else str(g["specification"]["resolved_value"]),
                g["bar_count"]["resolved_value"],
            )
            for g in res["groups"]
        )

    ok = keyset(ra) == keyset(rb) and len(ra["groups"]) == 2
    return {"ok": ok, "a": keyset(ra), "b": keyset(rb)}


def run_anti_hardcoding(*, package_dir: Path) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    rename = rename_invariance()
    order = ordering_invariance()
    ok = bool(guard.get("ok") and rename.get("ok") and order.get("ok"))
    return {
        "ok": ok,
        "source_guard": guard,
        "rename_invariance": rename,
        "ordering_invariance": order,
        "beam_id_special_cases": bool(guard.get("hits")),
    }


__all__ = ["ordering_invariance", "rename_invariance", "run_anti_hardcoding", "source_guard"]
