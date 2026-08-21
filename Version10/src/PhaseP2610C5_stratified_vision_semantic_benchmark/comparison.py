"""Multi-dimensional Vision vs deterministic comparison. No automatic truth winner."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .normalize import map_layer, normalize_spec, parse_bar_count, physical_key


def _role(g: Dict[str, Any]) -> str:
    return str(g.get("role_hypothesis") or g.get("reinforcement_role") or g.get("role") or "UNKNOWN").upper()


def _count(g: Dict[str, Any]) -> Optional[int]:
    explicit = g.get("bar_count") if g.get("bar_count") not in (None, "", "UNKNOWN") else g.get("count")
    return parse_bar_count(g.get("spec") or g.get("specification"), explicit)


def _count_label(vis: Optional[int], det: Optional[int]) -> str:
    if vis is None or det is None:
        return "UNKNOWN"
    if vis == det:
        return "EXACT"
    if vis > det:
        return "OVER_ESTIMATE"
    return "UNDER_ESTIMATE"


def _det_long(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for g in groups or []:
        fam = str(g.get("family") or "").upper()
        layer = map_layer(g.get("physical_layer") or g.get("layer"))
        if fam == "STIRRUP" or layer == "STIRRUP":
            continue
        out.append(
            {
                "layer": layer,
                "spec": g.get("specification") or g.get("spec"),
                "role": _role(g),
                "bar_count": g.get("count") if g.get("count") not in ("UNKNOWN", None) else parse_bar_count(g.get("specification")),
                "support_scope": g.get("zone") or g.get("spatial_extent") or "UNKNOWN",
                "raw": g,
            }
        )
    return out


def _det_stirrups(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for g in groups or []:
        fam = str(g.get("family") or "").upper()
        layer = map_layer(g.get("physical_layer") or g.get("layer"))
        if fam == "STIRRUP" or layer == "STIRRUP":
            out.append({"spec": g.get("specification") or g.get("spec"), "raw": g})
    return out


def _vis_long(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for g in parsed.get("groups") or []:
        layer = map_layer(g.get("layer"))
        if layer == "STIRRUP":
            continue
        out.append(
            {
                "layer": layer,
                "spec": g.get("spec"),
                "role": _role(g),
                "bar_count": g.get("bar_count"),
                "support_scope": g.get("support_scope"),
                "relative_length_evidence": g.get("relative_length_evidence"),
                "span_relationship": g.get("span_relationship"),
                "physical_group_id": g.get("physical_group_id"),
                "raw": g,
            }
        )
    return out


def match_physical(vision: List[Dict[str, Any]], det: List[Dict[str, Any]]) -> Dict[str, Any]:
    vis_b: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    det_b: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for g in vision:
        vis_b[physical_key(g)].append(g)
    for g in det:
        det_b[physical_key(g)].append(g)
    keys = sorted(set(vis_b) | set(det_b))
    pairs = []
    vis_only = []
    det_only = []
    merged = 0
    for key in keys:
        vlist = list(vis_b.get(key) or [])
        dlist = list(det_b.get(key) or [])
        if len(dlist) > 1 and len(vlist) == 1:
            merged += 1
        if len(vlist) == 1 and len(dlist) == 1:
            vg, dg = vlist[0], dlist[0]
            vc, dc = _count(vg), _count(dg)
            pairs.append(
                {
                    "layer": key[0],
                    "spec": key[1],
                    "physical_group_match": True,
                    "layer_match": True,
                    "spec_match": True,
                    "role_match": _role(vg) == _role(dg),
                    "vision_role": _role(vg),
                    "deterministic_role": _role(dg),
                    "vision_count": vc,
                    "deterministic_count": dc,
                    "count_comparison": _count_label(vc, dc),
                    "count_delta": (vc - dc) if vc is not None and dc is not None else None,
                    "vision": vg,
                    "deterministic": dg,
                }
            )
            continue
        used_d = set()
        used_v = set()
        for i, vg in enumerate(vlist):
            best = None
            for j, dg in enumerate(dlist):
                if j in used_d:
                    continue
                if _role(vg) == _role(dg):
                    best = j
                    break
            if best is None:
                for j, dg in enumerate(dlist):
                    if j not in used_d:
                        best = j
                        break
            if best is None:
                vis_only.append(vg)
                used_v.add(i)
                continue
            dg = dlist[best]
            used_d.add(best)
            used_v.add(i)
            vc, dc = _count(vg), _count(dg)
            pairs.append(
                {
                    "layer": key[0],
                    "spec": key[1],
                    "physical_group_match": True,
                    "layer_match": True,
                    "spec_match": True,
                    "role_match": _role(vg) == _role(dg),
                    "vision_role": _role(vg),
                    "deterministic_role": _role(dg),
                    "vision_count": vc,
                    "deterministic_count": dc,
                    "count_comparison": _count_label(vc, dc),
                    "count_delta": (vc - dc) if vc is not None and dc is not None else None,
                    "vision": vg,
                    "deterministic": dg,
                }
            )
        for i, vg in enumerate(vlist):
            if i not in used_v:
                vis_only.append(vg)
        for j, dg in enumerate(dlist):
            if j not in used_d:
                det_only.append(dg)
    return {
        "pairs": pairs,
        "vision_only": vis_only,
        "deterministic_only": det_only,
        "merged_distinct_groups": merged,
    }


def _stirrup_cmp(vision: List[Dict[str, Any]], det: List[Dict[str, Any]]) -> Dict[str, Any]:
    vspecs = [normalize_spec(s.get("spec")) for s in vision if s.get("spec")]
    dspecs = [normalize_spec(s.get("spec")) for s in det if s.get("spec")]
    vs, ds = set(vspecs), set(dspecs)
    return {
        "vision_count": len(vspecs),
        "deterministic_count": len(dspecs),
        "matched": sorted(vs & ds),
        "vision_only": sorted(vs - ds),
        "deterministic_only": sorted(ds - vs),
        "agreement": bool(vs) and vs == ds,
    }


def compare_beam(*, parsed: Dict[str, Any], detected: List[Dict[str, Any]], expected: List[Dict[str, Any]], requested_id: str) -> Dict[str, Any]:
    if not parsed or not parsed.get("usable"):
        return {
            "taxonomy": ["INSUFFICIENT_COMPARISON_EVIDENCE"],
            "target_association": "UNKNOWN",
            "note": parsed.get("unusable_reason") if parsed else "no_parsed_vision",
        }
    identified = bool(parsed.get("target_identified"))
    tid = str(parsed.get("target_beam_id") or "")
    if identified and tid == str(requested_id):
        target = "MATCH"
    elif parsed.get("target_identified") is False or (tid and tid != str(requested_id)):
        target = "DISAGREE"
    else:
        target = "UNKNOWN"
    vis = _vis_long(parsed)
    det = _det_long(detected or expected or [])
    phys = match_physical(vis, det)
    stir = _stirrup_cmp(list(parsed.get("stirrups") or []), _det_stirrups(detected or expected or []))
    layers_v = {g["layer"] for g in vis}
    layers_d = {g["layer"] for g in det}
    specs_v = {normalize_spec(g.get("spec")) for g in vis}
    specs_d = {normalize_spec(g.get("spec")) for g in det}
    role_mismatch = sum(1 for p in phys["pairs"] if p["physical_group_match"] and not p["role_match"])
    count_mismatch = sum(1 for p in phys["pairs"] if p["count_comparison"] in ("OVER_ESTIMATE", "UNDER_ESTIMATE"))
    tags: List[str] = []
    if target == "DISAGREE":
        tags.append("TARGET_ASSOCIATION_DISAGREEMENT")
    if not vis and not det:
        tags.append("INSUFFICIENT_COMPARISON_EVIDENCE")
    if phys["vision_only"] and not phys["deterministic_only"] and not phys["pairs"]:
        tags.append("VISION_ONLY_INTERPRETATION")
    if phys["deterministic_only"] and not phys["vision_only"] and not phys["pairs"]:
        tags.append("DETERMINISTIC_ONLY_INTERPRETATION")
    if phys["vision_only"] or phys["deterministic_only"] or phys["merged_distinct_groups"]:
        tags.append("GROUP_STRUCTURE_DISAGREEMENT")
    if role_mismatch and not (phys["vision_only"] or phys["deterministic_only"] or phys["merged_distinct_groups"]):
        tags.append("ROLE_ONLY_DISAGREEMENT")
    elif role_mismatch:
        tags.append("ROLE_ONLY_DISAGREEMENT")
    if count_mismatch:
        tags.append("COUNT_DISAGREEMENT")
    if not stir["agreement"] and (stir["vision_count"] or stir["deterministic_count"]):
        tags.append("STIRRUP_DISAGREEMENT")
    if not tags and phys["pairs"]:
        tags.append("AGREEMENT")
    if not tags:
        tags.append("INSUFFICIENT_COMPARISON_EVIDENCE")
    return {
        "taxonomy": tags,
        "target_association": target,
        "physical_group_count": {"vision": len(vis), "deterministic": len(det)},
        "layer_match": {
            "vision_layers": sorted(layers_v),
            "deterministic_layers": sorted(layers_d),
            "shared": sorted(layers_v & layers_d),
            "vision_only": sorted(layers_v - layers_d),
            "deterministic_only": sorted(layers_d - layers_v),
        },
        "spec_match": {
            "shared": sorted(specs_v & specs_d),
            "vision_only": sorted(specs_v - specs_d),
            "deterministic_only": sorted(specs_d - specs_v),
        },
        "pairs": phys["pairs"],
        "vision_only_groups": phys["vision_only"],
        "deterministic_only_groups": phys["deterministic_only"],
        "merged_distinct_groups": phys["merged_distinct_groups"],
        "role_mismatch_count": role_mismatch,
        "count_disagreement_count": count_mismatch,
        "stirrup": stir,
        "same_spec_collapse": phys["merged_distinct_groups"] > 0,
        "truth_declaration": "NONE",
        "note": "Automated comparison only. No VISION_CORRECT or DETERMINISTIC_CORRECT declaration.",
    }


__all__ = ["compare_beam", "match_physical"]
