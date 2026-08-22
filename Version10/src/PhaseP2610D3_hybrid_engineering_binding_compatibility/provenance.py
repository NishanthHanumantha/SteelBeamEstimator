"""Preserve D.2 semantic provenance. Binding must not overwrite Vision-preferred fields."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


def _field(rec: Any) -> Any:
    if isinstance(rec, dict) and "value" in rec:
        return rec.get("value")
    return rec


def semantic_snapshot(*, hybrid: Dict[str, Any], group: Dict[str, Any]) -> Dict[str, Any]:
    target = hybrid.get("target_identity") if isinstance(hybrid.get("target_identity"), dict) else {}
    return {
        "target_identity": _field(target),
        "layer": _field(group.get("layer")),
        "role": _field(group.get("role")),
        "bar_count": _field(group.get("bar_count")),
        "diameter": _field(group.get("diameter")),
        "specification": _field(group.get("specification")),
        "support_scope": _field(group.get("support_scope")),
        "provenance": deepcopy(group.get("provenance") or {}),
        "field_records": {
            "layer": deepcopy(group.get("layer")),
            "role": deepcopy(group.get("role")),
            "bar_count": deepcopy(group.get("bar_count")),
            "diameter": deepcopy(group.get("diameter")),
            "specification": deepcopy(group.get("specification")),
            "support_scope": deepcopy(group.get("support_scope")),
        },
        "longer_bar_likely_main_hook": group.get("longer_bar_likely_main_hook") or "ARCHITECTURE_HOOK_ONLY",
    }


def ambiguous_ids(hybrid: Dict[str, Any]) -> List[str]:
    gm = hybrid.get("group_matching") if isinstance(hybrid.get("group_matching"), dict) else {}
    ids: List[str] = []
    for rec in gm.get("ambiguous_records") or []:
        if not isinstance(rec, dict):
            continue
        vid = rec.get("vision_id")
        if vid is not None and str(vid) not in ids:
            ids.append(str(vid))
    return ids


def duplicate_id_set(hybrid: Dict[str, Any]) -> set:
    out = set()
    for rec in hybrid.get("possible_duplicate_groups") or []:
        if not isinstance(rec, dict):
            continue
        for gid in rec.get("group_ids") or []:
            if gid not in (None, "", "None"):
                out.add(str(gid))
    return out


def is_ambiguous_group(group: Dict[str, Any], hybrid: Dict[str, Any]) -> bool:
    origin = str(group.get("origin") or "")
    prov = group.get("provenance") if isinstance(group.get("provenance"), dict) else {}
    if origin == "AMBIGUOUS" or "AMBIGUOUS" in origin:
        return True
    reason = str(prov.get("resolution_reason") or "")
    if "AMBIGUOUS" in reason:
        return True
    gid = str(group.get("group_id") or "")
    vid = str(prov.get("vision_id") or gid)
    return vid in set(ambiguous_ids(hybrid)) or gid in set(ambiguous_ids(hybrid))


def is_possible_duplicate(group: Dict[str, Any], hybrid: Dict[str, Any]) -> bool:
    ids = duplicate_id_set(hybrid)
    prov = group.get("provenance") if isinstance(group.get("provenance"), dict) else {}
    gid = str(group.get("group_id") or "")
    vid = str(prov.get("vision_id") or "")
    return gid in ids or vid in ids


def authority_preserved(original: Dict[str, Any], bound: Dict[str, Any]) -> Dict[str, bool]:
    orig_sem = semantic_snapshot(hybrid={"target_identity": original.get("target_identity")}, group=original) if "layer" in original else None
    if orig_sem is None:
        orig_sem = original.get("semantic") or {}
    new_sem = bound.get("semantic") or {}
    return {
        "diameter": orig_sem.get("diameter") == new_sem.get("diameter"),
        "role": orig_sem.get("role") == new_sem.get("role"),
        "layer": orig_sem.get("layer") == new_sem.get("layer"),
        "bar_count": orig_sem.get("bar_count") == new_sem.get("bar_count"),
        "specification": orig_sem.get("specification") == new_sem.get("specification"),
    }


__all__ = [
    "ambiguous_ids",
    "authority_preserved",
    "duplicate_id_set",
    "is_ambiguous_group",
    "is_possible_duplicate",
    "semantic_snapshot",
]
