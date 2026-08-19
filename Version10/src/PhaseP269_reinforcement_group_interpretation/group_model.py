"""Normalized ReinforcementGroupRecord. Fields come from existing evidence or UNKNOWN."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import PHASE_ID, UNKNOWN


def spec_from_count_dia(*, count: Any, diameter: Any, legs: Any = None, family: str = "") -> Optional[str]:
    try:
        q = int(count)
        d = int(round(float(diameter)))
    except (TypeError, ValueError):
        return None
    if q <= 0 or d <= 0:
        return None
    if family == "STIRRUP" or (legs is not None and str(legs).strip()):
        try:
            n_legs = int(legs) if legs is not None else q
        except (TypeError, ValueError):
            n_legs = q
        return f"{n_legs}L-Y{d}"
    return f"{q}Y{d}"


def parse_count_dia(spec: Any) -> Dict[str, Any]:
    text = str(spec or "").upper().replace(" ", "").replace("-", "")
    count = None
    diameter = None
    legs = None
    if "L" in text and "Y" in text:
        left, _, rest = text.partition("L")
        try:
            legs = int(left) if left.isdigit() else None
        except ValueError:
            legs = None
        rest = rest.lstrip("-")
        if rest.startswith("Y"):
            try:
                diameter = int("".join(ch for ch in rest[1:] if ch.isdigit())[:2] or "0") or None
            except ValueError:
                diameter = None
    elif "Y" in text:
        left, _, right = text.partition("Y")
        try:
            count = int("".join(ch for ch in left if ch.isdigit()) or "0") or None
        except ValueError:
            count = None
        try:
            diameter = int("".join(ch for ch in right if ch.isdigit())[:2] or "0") or None
        except ValueError:
            diameter = None
    return {"count": count, "diameter": diameter, "legs": legs}


def make_group(
    *,
    beam_id: str,
    group_id: str,
    family: str,
    physical_layer: str,
    reinforcement_role: str,
    count: Any = None,
    diameter: Any = None,
    specification: Any = None,
    spacing: Any = None,
    zone: str = UNKNOWN,
    spatial_extent: Any = None,
    start_position: Any = None,
    end_position: Any = None,
    annotation_ids: Optional[List[str]] = None,
    leader_ids: Optional[List[str]] = None,
    source_layer: str = UNKNOWN,
    deterministic_identity: str = UNKNOWN,
    provenance: str,
    evidence_quality: str = UNKNOWN,
    confidence: float = 0.0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    parsed = parse_count_dia(specification)
    if count is None:
        count = parsed.get("count")
    if diameter is None:
        diameter = parsed.get("diameter")
    if not specification:
        specification = spec_from_count_dia(
            count=count, diameter=diameter, legs=parsed.get("legs"), family=family
        ) or UNKNOWN
    rec = {
        "phase": PHASE_ID,
        "beam_id": beam_id,
        "group_id": group_id,
        "family": family,
        "physical_layer": physical_layer,
        "reinforcement_role": reinforcement_role,
        "count": count if count is not None else UNKNOWN,
        "diameter": diameter if diameter is not None else UNKNOWN,
        "specification": specification,
        "spacing": spacing if spacing not in (None, "") else UNKNOWN,
        "zone": zone or UNKNOWN,
        "spatial_extent": spatial_extent if spatial_extent not in (None, "") else UNKNOWN,
        "start_position": start_position if start_position is not None else UNKNOWN,
        "end_position": end_position if end_position is not None else UNKNOWN,
        "annotation_ids": list(annotation_ids or []),
        "leader_ids": list(leader_ids or []),
        "source_layer": source_layer or UNKNOWN,
        "deterministic_identity": deterministic_identity,
        "provenance": provenance,
        "evidence_quality": evidence_quality,
        "confidence": confidence,
    }
    if extra:
        rec.update(extra)
    return rec


def identity_key(group: Dict[str, Any]) -> tuple:
    """Physical identity: layer + role + spec. Specification alone is never enough."""
    return (
        str(group.get("family") or UNKNOWN),
        str(group.get("physical_layer") or UNKNOWN),
        str(group.get("reinforcement_role") or UNKNOWN),
        str(group.get("specification") or UNKNOWN),
    )


def spec_layer_key(group: Dict[str, Any]) -> tuple:
    return (
        str(group.get("family") or UNKNOWN),
        str(group.get("physical_layer") or UNKNOWN),
        str(group.get("specification") or UNKNOWN),
    )


__all__ = ["identity_key", "make_group", "parse_count_dia", "spec_from_count_dia", "spec_layer_key"]
