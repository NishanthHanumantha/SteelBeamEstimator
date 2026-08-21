"""Explainable Vision↔deterministic matching for provenance. Not deterministic supremacy."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .normalize import map_layer, normalize_spec, parse_bar_count, parse_diameter


def _score(vis: Dict[str, Any], det: Dict[str, Any]) -> int:
    score = 0
    if map_layer(vis.get("layer")) == map_layer(det.get("layer")):
        score += 4
    vs = normalize_spec(vis.get("specification") or vis.get("spec"))
    ds = normalize_spec(det.get("specification") or det.get("spec"))
    if vs and ds and vs == ds:
        score += 4
    vc = vis.get("bar_count") if vis.get("bar_count") is not None else parse_bar_count(vis.get("specification"))
    dc = det.get("bar_count") if det.get("bar_count") is not None else parse_bar_count(det.get("specification"))
    if vc is not None and dc is not None and int(vc) == int(dc):
        score += 2
    vd = vis.get("diameter") if vis.get("diameter") is not None else parse_diameter(vis.get("specification"))
    dd = det.get("diameter") if det.get("diameter") is not None else parse_diameter(det.get("specification"))
    if vd is not None and dd is not None and int(vd) == int(dd):
        score += 2
    vr = str(vis.get("role") or "").upper()
    dr = str(det.get("role") or "").upper()
    if vr and dr and vr == dr:
        score += 1
    vsc = str(vis.get("support_scope") or "").upper()
    dsc = str(det.get("support_scope") or "").upper()
    if vsc and dsc and vsc == dsc and vsc != "UNKNOWN":
        score += 1
    return score


def match_groups(vision: List[Dict[str, Any]], det: List[Dict[str, Any]]) -> Dict[str, Any]:
    pairs = []
    used_d = set()
    used_v = set()
    ranked: List[Tuple[int, int, int]] = []
    for i, vg in enumerate(vision or []):
        for j, dg in enumerate(det or []):
            ranked.append((_score(vg, dg), i, j))
    ranked.sort(key=lambda t: (-t[0], t[1], t[2]))
    for score, i, j in ranked:
        if score < 4:
            break
        if i in used_v or j in used_d:
            continue
        used_v.add(i)
        used_d.add(j)
        pairs.append(
            {
                "vision_index": i,
                "deterministic_index": j,
                "score": score,
                "vision_id": vision[i].get("physical_group_id"),
                "deterministic_id": det[j].get("physical_group_id"),
            }
        )
    vision_only = [i for i in range(len(vision or [])) if i not in used_v]
    det_only = [j for j in range(len(det or [])) if j not in used_d]
    return {
        "pairs": pairs,
        "vision_only_indices": vision_only,
        "deterministic_only_indices": det_only,
    }


def match_stirrups(vision: List[Dict[str, Any]], det: List[Dict[str, Any]]) -> Dict[str, Any]:
    return match_groups(vision, det)


__all__ = ["match_groups", "match_stirrups"]
