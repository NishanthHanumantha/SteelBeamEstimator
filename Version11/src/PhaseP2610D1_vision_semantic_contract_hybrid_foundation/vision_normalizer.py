"""Normalize existing C.3/C.5 Vision payloads into a canonical shadow model. No repair."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .normalize import map_layer, parse_bar_count, parse_diameter


def _conf(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def normalize_vision_group(g: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    spec = g.get("spec") or g.get("specification")
    count = parse_bar_count(spec, g.get("bar_count") if g.get("bar_count") is not None else g.get("count"))
    dia = parse_diameter(spec, g.get("diameter"))
    role = str(g.get("role_hypothesis") or g.get("role") or "UNKNOWN").upper()
    return {
        "physical_group_id": str(g.get("physical_group_id") or g.get("group_id") or f"VG{index+1}"),
        "layer": map_layer(g.get("layer") or g.get("physical_layer")),
        "role": role if role in ("MAIN", "EXTRA", "UNKNOWN") else "UNKNOWN",
        "specification_raw": spec,
        "specification": spec,
        "bar_count": count,
        "diameter": dia,
        "support_scope": str(g.get("support_scope") or g.get("zone") or "UNKNOWN").upper(),
        "confidence": _conf(g.get("confidence")),
        "role_confidence": _conf(g.get("role_confidence") if g.get("role_confidence") is not None else g.get("confidence")),
        "relative_span_length": g.get("relative_length_evidence") or "UNKNOWN",
        "relative_group_extent": g.get("span_relationship") or g.get("support_scope") or "UNKNOWN",
        "directional_orientation": g.get("directional_orientation") or "UNKNOWN",
        "evidence": g.get("evidence"),
        "raw": g,
    }


def normalize_vision_stirrup(s: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    spec = s.get("spec") or s.get("specification")
    return {
        "stirrup_id": str(s.get("stirrup_id") or f"VS{index+1}"),
        "specification_raw": spec,
        "specification": spec,
        "diameter": parse_diameter(spec, s.get("diameter")),
        "legs": None,
        "confidence": _conf(s.get("confidence")),
        "evidence": s.get("evidence"),
        "raw": s,
    }


def extract_vision_payload(parsed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    parsed = parsed or {}
    identified = parsed.get("target_identified")
    if identified is None:
        identified = parsed.get("target_beam_identified")
    conf = parsed.get("association_confidence")
    if conf is None:
        conf = parsed.get("target_association_confidence")
    groups_raw = parsed.get("groups")
    if groups_raw is None:
        groups_raw = parsed.get("reinforcement_groups") or []
    stirrups_raw = list(parsed.get("stirrups") or [])
    groups = []
    extra_stirrups = []
    for i, g in enumerate(groups_raw):
        if not isinstance(g, dict):
            continue
        layer = map_layer(g.get("layer"))
        if layer == "STIRRUP":
            extra_stirrups.append(normalize_vision_stirrup(g, index=len(stirrups_raw) + len(extra_stirrups)))
            continue
        groups.append(normalize_vision_group(g, index=i))
    stirrups = [normalize_vision_stirrup(s, index=i) for i, s in enumerate(stirrups_raw) if isinstance(s, dict)]
    stirrups.extend(extra_stirrups)
    return {
        "usable": bool(parsed.get("usable", True)),
        "unusable_reason": parsed.get("unusable_reason"),
        "schema_version": parsed.get("schema_version"),
        "target_beam_id": parsed.get("target_beam_id"),
        "target_identified": bool(identified),
        "association_confidence": _conf(conf),
        "groups": groups,
        "stirrups": stirrups,
        "neighbour_evidence_detected": bool(
            parsed.get("neighbour_evidence_detected") if parsed.get("neighbour_evidence_detected") is not None else parsed.get("neighbor_evidence_detected")
        ),
    }


def extract_deterministic_groups(detected: List[Dict[str, Any]]) -> Dict[str, Any]:
    long_g = []
    stirrups = []
    spacers = []
    engineering = []
    for i, g in enumerate(detected or []):
        if not isinstance(g, dict):
            continue
        fam = str(g.get("family") or "").upper()
        layer = map_layer(g.get("physical_layer") or g.get("layer"))
        role = str(g.get("reinforcement_role") or g.get("role") or "UNKNOWN").upper()
        row = {
            "physical_group_id": str(g.get("group_id") or f"DG{i+1}"),
            "layer": layer,
            "role": role if role in ("MAIN", "EXTRA", "STIRRUP", "SPACER", "UNKNOWN") else "UNKNOWN",
            "specification": g.get("specification") or g.get("spec"),
            "bar_count": g.get("count") if g.get("count") not in ("UNKNOWN", None, "") else parse_bar_count(g.get("specification")),
            "diameter": g.get("diameter") if g.get("diameter") not in ("UNKNOWN", None, "") else parse_diameter(g.get("specification")),
            "support_scope": str(g.get("zone") or g.get("spatial_extent") or "UNKNOWN").upper(),
            "cut_length_mm": g.get("cut_length_mm"),
            "provenance": g.get("provenance"),
            "family": fam,
            "raw": g,
        }
        if fam == "SPACER" or layer == "SPACER" or role == "SPACER":
            spacers.append(row)
            continue
        if fam == "STIRRUP" or layer == "STIRRUP" or role == "STIRRUP":
            stirrups.append(row)
            continue
        long_g.append(row)
        if g.get("cut_length_mm") is not None:
            engineering.append({"kind": "CUT_LENGTH", "group_id": row["physical_group_id"], "cut_length_mm": g.get("cut_length_mm")})
    return {
        "groups": long_g,
        "stirrups": stirrups,
        "spacers": spacers,
        "engineering": engineering,
    }


__all__ = ["extract_deterministic_groups", "extract_vision_payload", "normalize_vision_group"]
