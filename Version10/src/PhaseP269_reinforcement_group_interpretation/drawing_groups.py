"""Drawing-level groups from R.1 annotations. One group per layer+role+spec. No beam IDs."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .config import (
    FAMILY_LONGITUDINAL,
    FAMILY_STIRRUP,
    LAYER_STIRRUP,
    LAYER_UNKNOWN,
    ROLE_STIRRUP,
    ROLE_UNKNOWN,
    UNKNOWN,
    ZONE_FULL_SPAN,
    ZONE_SUPPORT,
    ZONE_UNKNOWN,
)
from .group_model import make_group, spec_from_count_dia
from .identity import assign_group_ids, collapse_piece_groups
from .layer_role import family_from_layer, physical_layer_from_role, reinforcement_role_from_token

_STIRRUP_RE = re.compile(r"\d+\s*L\s*-?\s*Y\d+|C/C|@", re.I)
_SPACING_RE = re.compile(r"(\d+(?:\s*/\s*\d+)+|\d+)\s*(?:C/C)?", re.I)


def _int(value: Any) -> Optional[int]:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def looks_like_stirrup(text: Any, role: Any) -> bool:
    if str(role or "").upper().find("STIRRUP") >= 0:
        return True
    raw = str(text or "").upper()
    return bool(re.search(r"\d+\s*L\s*-?\s*Y", raw)) and ("@" in raw or "C/C" in raw)


def spacing_from_text(text: Any) -> Any:
    raw = str(text or "")
    if "@" not in raw.upper() and "C/C" not in raw.upper():
        return UNKNOWN
    after = raw.split("@", 1)[-1]
    hit = _SPACING_RE.search(after.replace("\\X", ""))
    if not hit:
        return UNKNOWN
    return hit.group(1).replace(" ", "") + " C/C"


def annotation_to_piece(ann: Dict[str, Any], *, beam_id: str) -> Optional[Dict[str, Any]]:
    raw = ann.get("clean_text") or ann.get("raw_text") or ann.get("bar_label") or ""
    role = ann.get("role")
    if looks_like_stirrup(raw, role):
        layer = LAYER_STIRRUP
        family = FAMILY_STIRRUP
        rrole = ROLE_STIRRUP
    else:
        layer = physical_layer_from_role(role)
        family = family_from_layer(layer) if layer != LAYER_UNKNOWN else FAMILY_LONGITUDINAL
        rrole = reinforcement_role_from_token(role)
        if rrole == ROLE_UNKNOWN and family == FAMILY_LONGITUDINAL:
            rrole = ROLE_UNKNOWN
    qty = _int(ann.get("quantity"))
    dia = _int(ann.get("diameter_mm"))
    if family == FAMILY_STIRRUP:
        spec = spec_from_count_dia(count=qty, diameter=dia, legs=qty, family=FAMILY_STIRRUP)
        spacing = spacing_from_text(raw)
        zone = ZONE_UNKNOWN
    else:
        spec = spec_from_count_dia(count=qty, diameter=dia, family=family)
        spacing = UNKNOWN
        zone = ZONE_FULL_SPAN if rrole == "MAIN" else (ZONE_SUPPORT if rrole == "EXTRA" else ZONE_UNKNOWN)
    if spec in (None, UNKNOWN) and not str(raw).strip():
        return None
    if spec in (None, UNKNOWN) and looks_like_stirrup(raw, role):
        spec = str(raw).replace(" ", "")
        family = FAMILY_STIRRUP
        layer = LAYER_STIRRUP
        rrole = ROLE_STIRRUP
    if spec in (None, UNKNOWN):
        return None
    quality = str(ann.get("confidence") or UNKNOWN)
    return make_group(
        beam_id=beam_id,
        group_id="",
        family=family,
        physical_layer=layer,
        reinforcement_role=rrole,
        count=qty,
        diameter=dia,
        specification=spec,
        spacing=spacing,
        zone=zone,
        spatial_extent=zone,
        annotation_ids=[str(ann.get("annotation_id") or "")],
        source_layer=UNKNOWN,
        deterministic_identity="DRAWING_ANNOTATION",
        provenance="R1_DXF_ANNOTATION",
        evidence_quality=quality,
        confidence=0.8 if str(quality).upper() == "HIGH" else 0.5,
        extra={"raw_text": str(raw), "position_zone": ann.get("position_zone") or UNKNOWN},
    )


def extract_drawing_groups(annotations: Iterable[Dict[str, Any]], *, beam_id: str) -> List[Dict[str, Any]]:
    pieces: List[Dict[str, Any]] = []
    for ann in annotations:
        if not isinstance(ann, dict):
            continue
        piece = annotation_to_piece(ann, beam_id=beam_id)
        if piece:
            pieces.append(piece)
    collapsed = collapse_piece_groups(pieces)
    return assign_group_ids(collapsed, beam_id=beam_id)


__all__ = ["extract_drawing_groups", "looks_like_stirrup", "spacing_from_text"]
