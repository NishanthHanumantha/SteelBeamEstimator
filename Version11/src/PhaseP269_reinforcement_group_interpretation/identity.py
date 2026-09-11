"""Group identity and L/R extra collapse. No specification-only dedup. No beam IDs."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .config import UNKNOWN, ZONE_BOTH_SUPPORTS, ZONE_LEFT_SUPPORT, ZONE_RIGHT_SUPPORT
from .group_model import identity_key
from .layer_role import merge_zones


def collapse_piece_groups(pieces: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Collapse LEFT/RIGHT extra pieces of the same layer+role+spec into one group.

    Same spec + different layer remain DISTINCT.
    Same spec + same layer + different role remain DISTINCT.
    Same spec + same layer + same role + complementary support pieces become ONE GROUP.
    """
    buckets: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    order: List[Tuple[Any, ...]] = []
    for piece in pieces:
        key = identity_key(piece)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(piece)
    out: List[Dict[str, Any]] = []
    for key in order:
        members = buckets[key]
        if len(members) == 1:
            out.append(dict(members[0]))
            continue
        base = dict(members[0])
        zones = tuple(str(m.get("zone") or UNKNOWN) for m in members)
        merged_zone = merge_zones(zones)
        if merged_zone == UNKNOWN and {ZONE_LEFT_SUPPORT, ZONE_RIGHT_SUPPORT} <= set(zones):
            merged_zone = ZONE_BOTH_SUPPORTS
        ids: List[str] = []
        sources: List[str] = []
        anns: List[str] = []
        leaders: List[str] = []
        for m in members:
            sid = str(m.get("source_bar_id") or m.get("deterministic_identity") or "")
            if sid:
                sources.append(sid)
            ids.extend(str(x) for x in (m.get("annotation_ids") or []) if x)
            anns.extend(str(x) for x in (m.get("annotation_ids") or []) if x)
            leaders.extend(str(x) for x in (m.get("leader_ids") or []) if x)
        base["zone"] = merged_zone
        base["annotation_ids"] = list(dict.fromkeys(anns or ids))
        base["leader_ids"] = list(dict.fromkeys(leaders))
        base["piece_count"] = len(members)
        base["source_bar_ids"] = sources
        if any(z in (ZONE_LEFT_SUPPORT, ZONE_RIGHT_SUPPORT) for z in zones):
            base["spatial_extent"] = merged_zone
        out.append(base)
    return out


def assign_group_ids(groups: List[Dict[str, Any]], *, beam_id: str) -> List[Dict[str, Any]]:
    ranked = sorted(
        groups,
        key=lambda g: (
            str(g.get("family") or ""),
            str(g.get("physical_layer") or ""),
            str(g.get("reinforcement_role") or ""),
            str(g.get("specification") or ""),
        ),
    )
    out: List[Dict[str, Any]] = []
    for i, rec in enumerate(ranked, start=1):
        item = dict(rec)
        item["beam_id"] = beam_id
        item["group_id"] = f"G{i:02d}"
        out.append(item)
    return out


__all__ = ["assign_group_ids", "collapse_piece_groups"]
