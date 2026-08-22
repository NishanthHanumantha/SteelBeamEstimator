"""Withhold engineering calculation for ambiguous groups. Do not force resolution."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import STATUS_GROUP_AMBIGUOUS, STATUS_WITHHELD


def is_ambiguous(group: Dict[str, Any]) -> bool:
    if group.get("ambiguous"):
        return True
    bind = group.get("engineering_binding") if isinstance(group.get("engineering_binding"), dict) else {}
    if str(bind.get("binding_status") or "") == "AMBIGUOUS":
        return True
    origin = str(group.get("origin") or "")
    return "AMBIGUOUS" in origin


def withheld_rows(calculated_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for g in calculated_groups:
        if g.get("status") in (STATUS_GROUP_AMBIGUOUS, STATUS_WITHHELD) or STATUS_WITHHELD in (g.get("reasons") or []):
            rows.append(
                {
                    "beam_id": g.get("beam_id"),
                    "group_id": g.get("group_id"),
                    "reason": STATUS_WITHHELD,
                    "calculated": False,
                    "status": g.get("status"),
                    "semantic": {
                        "layer": (g.get("semantic") or {}).get("layer"),
                        "role": (g.get("semantic") or {}).get("role"),
                        "diameter": g.get("diameter_mm"),
                        "bar_count": g.get("bar_count"),
                    },
                }
            )
    return rows


__all__ = ["is_ambiguous", "withheld_rows"]
