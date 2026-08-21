"""Safe physical-group identity. Same spec on different layer/role stays distinct."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_SPACE_HYPHEN = re.compile(r"[\s\-]")
_DXF_AT_X = re.compile(r"@\\*X", re.I)


def normalize_spec(spec: Any) -> str:
    s = str(spec or "").upper().strip()
    s = s.replace("–", "-").replace("—", "-")
    s = _DXF_AT_X.sub("@", s)
    s = s.replace("\\", "")
    s = _SPACE_HYPHEN.sub("", s)
    return s


def physical_identity(g: Dict[str, Any]) -> Tuple[str, str, str]:
    layer = str(g.get("layer") or g.get("physical_layer") or "UNKNOWN").upper().strip()
    role = str(g.get("role") or g.get("reinforcement_role") or "UNKNOWN").upper().strip()
    if str(g.get("family") or "").upper() == "STIRRUP" or layer == "STIRRUP":
        layer, role = "STIRRUP", "STIRRUP"
    spec = normalize_spec(g.get("spec") or g.get("specification"))
    return (layer, role, spec)


def identity_dict(key: Tuple[str, str, str]) -> Dict[str, str]:
    return {"layer": key[0], "role": key[1], "spec": key[2]}


def keys_of(groups: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    return [physical_identity(g) for g in groups]


def as_group(key: Tuple[str, str, str], *, provenance: str) -> Dict[str, Any]:
    return {
        "layer": key[0],
        "role": key[1],
        "specification": key[2],
        "provenance": provenance,
    }


def match_against(predicted: List[Dict[str, Any]], truth: List[Dict[str, Any]]) -> Dict[str, Any]:
    exp = set(keys_of(truth))
    pred = set(keys_of(predicted))
    matched = sorted(exp & pred)
    missing = sorted(exp - pred)
    spurious = sorted(pred - exp)
    return {
        "expected_count": len(exp),
        "predicted_count": len(pred),
        "correct": len(matched),
        "missing": len(missing),
        "spurious": len(spurious),
        "matched": [identity_dict(k) for k in matched],
        "missing_groups": [identity_dict(k) for k in missing],
        "spurious_groups": [identity_dict(k) for k in spurious],
        "identity_rule": "layer+role+specification",
    }


__all__ = [
    "as_group",
    "identity_dict",
    "keys_of",
    "match_against",
    "normalize_spec",
    "physical_identity",
]
