"""Extract detected reinforcement groups from a production R1.3 model. Read-only."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .config import (
    FAMILY_STIRRUP,
    R13_BUCKETS,
    UNKNOWN,
)
from .group_model import make_group, spec_from_count_dia
from .identity import assign_group_ids, collapse_piece_groups
from .layer_role import physical_layer_from_role, reinforcement_role_from_token, zone_from_piece

_LEGS_RE = re.compile(r"(\d+)\s*L\s*-?\s*Y", re.I)


def _as_conf(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        token = str(value or "").upper()
        if token == "HIGH":
            return 0.85
        if token == "MEDIUM":
            return 0.6
        if token == "LOW":
            return 0.4
        return 0.7


def _int(value: Any) -> Optional[int]:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _legs_from_bar(bar: Dict[str, Any]) -> Optional[int]:
    label = str(bar.get("bar_label") or "")
    hit = _LEGS_RE.search(label)
    if hit:
        return int(hit.group(1))
    return _int(bar.get("leg_count") or bar.get("legs"))


def extract_detected_groups(model: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a group inventory from existing R1.3 role buckets. Does not mutate the model."""
    if not isinstance(model, dict):
        return []
    beam_id = str(model.get("beam_id") or UNKNOWN)
    pieces: List[Dict[str, Any]] = []
    for bucket, family, layer, role in R13_BUCKETS:
        for bar in model.get(bucket) or []:
            if not isinstance(bar, dict):
                continue
            semantic = bar.get("semantic_role") or bar.get("piece_type") or role
            phys = physical_layer_from_role(semantic)
            if phys == UNKNOWN:
                phys = layer
            rrole = reinforcement_role_from_token(semantic)
            if rrole == UNKNOWN:
                rrole = role
            qty = _int(bar.get("quantity"))
            dia = _int(bar.get("diameter_mm"))
            legs = _legs_from_bar(bar) if family == FAMILY_STIRRUP else None
            spec = spec_from_count_dia(count=qty if family != FAMILY_STIRRUP else (legs or qty), diameter=dia, legs=legs, family=family)
            if family == FAMILY_STIRRUP and spec == UNKNOWN and dia:
                spec = spec_from_count_dia(count=legs or qty, diameter=dia, legs=legs or qty, family=family)
            zone = zone_from_piece(
                piece_type=bar.get("piece_type"),
                support_zone=bar.get("support_zone"),
                extent=bar.get("extent"),
                position_zone=bar.get("position_zone"),
            )
            pieces.append(
                make_group(
                    beam_id=beam_id,
                    group_id="",
                    family=family,
                    physical_layer=phys,
                    reinforcement_role=rrole,
                    count=qty if family != FAMILY_STIRRUP else (legs or qty),
                    diameter=dia,
                    specification=spec,
                    spacing=bar.get("spacing_pattern") or bar.get("spacing_mm"),
                    zone=zone,
                    spatial_extent=bar.get("extent") or zone,
                    annotation_ids=[],
                    source_layer=UNKNOWN,
                    deterministic_identity=str(bar.get("bar_id") or UNKNOWN),
                    provenance="R13_PRODUCTION_MODEL",
                    evidence_quality="DETERMINISTIC",
                    confidence=_as_conf(bar.get("classification_confidence")),
                    extra={
                        "source_bar_id": bar.get("bar_id"),
                        "piece_type": bar.get("piece_type"),
                        "cut_length_mm": bar.get("cut_length_mm") if bar.get("cut_length_mm") is not None else UNKNOWN,
                    },
                )
            )
    collapsed = collapse_piece_groups(pieces)
    return assign_group_ids(collapsed, beam_id=beam_id)


__all__ = ["extract_detected_groups"]
