"""Assign generic evidence strata. No beam-ID rules."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from .config import (
    STATUS_LIMITED,
    STATUS_READY,
    STRATA,
)


def classify_strata(rec: Dict[str, Any]) -> List[str]:
    stats = rec.get("group_stats") or {}
    assigned: List[str] = []
    top_n = int(stats.get("top_count") or 0)
    bot_n = int(stats.get("bottom_count") or 0)
    long_n = int(stats.get("longitudinal_count") or 0)
    if top_n == 1 and bot_n == 1 and not stats.get("has_extra") and long_n <= 2:
        assigned.append("SIMPLE_LONGITUDINAL")
    if top_n > 1 or bot_n > 1 or long_n > 2:
        assigned.append("MULTI_GROUP_LONGITUDINAL")
    if stats.get("has_main") and stats.get("has_extra"):
        assigned.append("MAIN_EXTRA_COMPLEXITY")
    if stats.get("same_spec_distinct"):
        assigned.append("SAME_SPEC_DISTINCT_GROUPS")
    if stats.get("stirrup_complex") or stats.get("stirrup_present"):
        assigned.append("STIRRUP_SEMANTIC_COMPLEXITY")
    if rec.get("neighbour_association_risk") or rec.get("association_ambiguous"):
        assigned.append("NEIGHBOUR_ASSOCIATION_RISK")
    if rec.get("c3_visual_gate_status") == STATUS_LIMITED:
        assigned.append("LIMITED_RENDER")
    if long_n >= 5 or (stats.get("has_extra") and stats.get("stirrup_present") and long_n >= 4):
        assigned.append("OTHER_HIGH_INFORMATION_COMPLEXITY")
    # Preserve order defined by STRATA.
    order = {name: i for i, name in enumerate(STRATA)}
    return sorted(set(assigned), key=lambda n: order.get(n, 99))


def eligibility_rank(rec: Dict[str, Any]) -> int:
    st = rec.get("c3_visual_gate_status")
    if st == STATUS_READY:
        return 0
    if st == STATUS_LIMITED:
        return 1
    return 9


def strata_set(rec: Dict[str, Any]) -> Set[str]:
    return set(rec.get("strata") or classify_strata(rec))


__all__ = ["classify_strata", "eligibility_rank", "strata_set"]
