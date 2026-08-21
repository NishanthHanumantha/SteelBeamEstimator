"""Field-level hybrid resolver. Vision preferred only after validation. No beam-ID branches."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    AUTH_DET,
    AUTH_DET_ENG,
    AUTH_VISION,
    REASON_ACCEPTED,
    REASON_DET_AUTHORITY,
    REASON_DET_ONLY,
    REASON_FALLBACK,
    REASON_NO_VALUE,
    REASON_VISION_ONLY,
)
from .hybrid_authority_contract import is_vision_preferred
from .matching import match_groups, match_stirrups
from .vision_validator import flag_possible_duplicates, validate_field


def _resolved_field(
    *,
    field: str,
    vision_value: Any,
    deterministic_value: Any,
    confidence: Optional[float],
    spec: Any = None,
    bar_count: Any = None,
    diameter: Any = None,
    beam_usable: bool = True,
) -> Dict[str, Any]:
    if not is_vision_preferred(field):
        return {
            "vision_value": vision_value,
            "deterministic_value": deterministic_value,
            "resolved_value": deterministic_value,
            "authority_used": AUTH_DET_ENG,
            "reason": REASON_DET_AUTHORITY,
            "validation": {"accepted": False, "reason": REASON_DET_AUTHORITY, "field": field},
            "conflict_recorded": vision_value not in (None, "", "UNKNOWN")
            and deterministic_value not in (None, "", "UNKNOWN")
            and vision_value != deterministic_value,
        }
    val = validate_field(
        field=field,
        vision_value=vision_value,
        confidence=confidence,
        spec=spec,
        bar_count=bar_count,
        diameter=diameter,
        beam_usable=beam_usable,
    )
    if val.get("accepted"):
        resolved = val.get("normalized", vision_value)
        conflict = deterministic_value not in (None, "", "UNKNOWN") and resolved != deterministic_value
        return {
            "vision_value": vision_value,
            "deterministic_value": deterministic_value,
            "resolved_value": resolved,
            "authority_used": AUTH_VISION,
            "reason": REASON_ACCEPTED,
            "validation": val,
            "conflict_recorded": bool(conflict),
        }
    fallback = deterministic_value
    return {
        "vision_value": vision_value,
        "deterministic_value": deterministic_value,
        "resolved_value": fallback,
        "authority_used": AUTH_DET if fallback not in (None, "") else AUTH_DET,
        "reason": val.get("reason") or REASON_FALLBACK,
        "validation": val,
        "conflict_recorded": vision_value not in (None, "") and fallback not in (None, "") and vision_value != fallback,
    }


def resolve_group(
    *,
    vision: Optional[Dict[str, Any]],
    deterministic: Optional[Dict[str, Any]],
    beam_usable: bool,
    origin: str,
) -> Dict[str, Any]:
    vis = vision or {}
    det = deterministic or {}
    spec = vis.get("specification")
    count = vis.get("bar_count")
    dia = vis.get("diameter")
    conf = vis.get("confidence")
    role_conf = vis.get("role_confidence") if vis.get("role_confidence") is not None else conf
    layer = _resolved_field(field="LAYER", vision_value=vis.get("layer"), deterministic_value=det.get("layer"), confidence=conf, beam_usable=beam_usable)
    role = _resolved_field(field="ROLE", vision_value=vis.get("role"), deterministic_value=det.get("role"), confidence=role_conf, beam_usable=beam_usable)
    bar_count = _resolved_field(field="BAR_COUNT", vision_value=count, deterministic_value=det.get("bar_count"), confidence=conf, spec=spec, beam_usable=beam_usable)
    diameter = _resolved_field(field="DIAMETER", vision_value=dia, deterministic_value=det.get("diameter"), confidence=conf, spec=spec, beam_usable=beam_usable)
    specification = _resolved_field(
        field="SPECIFICATION",
        vision_value=spec,
        deterministic_value=det.get("specification"),
        confidence=conf,
        spec=spec,
        bar_count=count,
        diameter=dia,
        beam_usable=beam_usable,
    )
    support = _resolved_field(
        field="SUPPORT_SCOPE",
        vision_value=vis.get("support_scope"),
        deterministic_value=det.get("support_scope"),
        confidence=conf,
        beam_usable=beam_usable,
    )
    gid = vis.get("physical_group_id") or det.get("physical_group_id")
    reasons = [layer["reason"], role["reason"], bar_count["reason"], diameter["reason"], specification["reason"], support["reason"]]
    validation_status = "ACCEPTED" if origin != REASON_DET_ONLY and all(
        r == REASON_ACCEPTED for r in (layer["reason"], role["reason"], bar_count["reason"], diameter["reason"], specification["reason"])
    ) else "MIXED"
    if origin == REASON_DET_ONLY:
        validation_status = "DETERMINISTIC_ONLY"
    if origin == REASON_VISION_ONLY:
        validation_status = "VISION_ONLY" if any(r == REASON_ACCEPTED for r in reasons) else "VISION_REJECTED"
    return {
        "group_id": gid,
        "origin": origin,
        "layer": layer,
        "role": role,
        "bar_count": bar_count,
        "diameter": diameter,
        "specification": specification,
        "support_scope": support,
        "vision_confidence": conf,
        "validation_status": validation_status,
        "resolution_reason": origin,
        "relative_span_length": vis.get("relative_span_length") or "UNKNOWN",
        "relative_group_extent": vis.get("relative_group_extent") or "UNKNOWN",
        "directional_orientation": vis.get("directional_orientation") or "UNKNOWN",
        "longer_bar_likely_main_hook": "ARCHITECTURE_HOOK_ONLY",
        "provenance": {
            "vision_id": vis.get("physical_group_id"),
            "deterministic_id": det.get("physical_group_id"),
            "deterministic_cut_length_mm": det.get("cut_length_mm"),
        },
    }


def resolve_beam(
    *,
    beam_id: str,
    vision: Dict[str, Any],
    deterministic: Dict[str, Any],
    source_provenance: Dict[str, Any],
) -> Dict[str, Any]:
    usable = bool(vision.get("usable"))
    target = _resolved_field(
        field="TARGET_IDENTITY",
        vision_value=vision.get("target_beam_id") if vision.get("target_identified") else None,
        deterministic_value=beam_id,
        confidence=vision.get("association_confidence"),
        beam_usable=usable,
    )
    vgroups = list(vision.get("groups") or [])
    dgroups = list(deterministic.get("groups") or [])
    matched = match_groups(vgroups, dgroups)
    groups: List[Dict[str, Any]] = []
    for p in matched["pairs"]:
        groups.append(
            resolve_group(
                vision=vgroups[p["vision_index"]],
                deterministic=dgroups[p["deterministic_index"]],
                beam_usable=usable,
                origin="MATCHED",
            )
        )
    for i in matched["vision_only_indices"]:
        groups.append(resolve_group(vision=vgroups[i], deterministic=None, beam_usable=usable, origin=REASON_VISION_ONLY))
    for j in matched["deterministic_only_indices"]:
        groups.append(resolve_group(vision=None, deterministic=dgroups[j], beam_usable=usable, origin=REASON_DET_ONLY))

    vst = list(vision.get("stirrups") or [])
    dst = list(deterministic.get("stirrups") or [])
    st_match = match_stirrups(vst, dst)
    stirrups = []
    for p in st_match["pairs"]:
        vis = vst[p["vision_index"]]
        det = dst[p["deterministic_index"]]
        ident = _resolved_field(
            field="STIRRUP_IDENTIFICATION",
            vision_value=vis.get("specification"),
            deterministic_value=det.get("specification"),
            confidence=vis.get("confidence"),
            spec=vis.get("specification"),
            beam_usable=usable,
        )
        stirrups.append(
            {
                "origin": "MATCHED",
                "identification": ident,
                "engineering_calculation_authority": AUTH_DET_ENG,
                "vision": vis,
                "deterministic": {k: det.get(k) for k in ("physical_group_id", "specification", "diameter", "cut_length_mm")},
            }
        )
    for i in st_match["vision_only_indices"]:
        vis = vst[i]
        ident = _resolved_field(
            field="STIRRUP_IDENTIFICATION",
            vision_value=vis.get("specification"),
            deterministic_value=None,
            confidence=vis.get("confidence"),
            spec=vis.get("specification"),
            beam_usable=usable,
        )
        stirrups.append({"origin": REASON_VISION_ONLY, "identification": ident, "engineering_calculation_authority": AUTH_DET_ENG, "vision": vis, "deterministic": None})
    for j in st_match["deterministic_only_indices"]:
        det = dst[j]
        ident = _resolved_field(
            field="STIRRUP_IDENTIFICATION",
            vision_value=None,
            deterministic_value=det.get("specification"),
            confidence=None,
            beam_usable=usable,
        )
        stirrups.append({"origin": REASON_DET_ONLY, "identification": ident, "engineering_calculation_authority": AUTH_DET_ENG, "vision": None, "deterministic": det})

    dup_flags = flag_possible_duplicates(vgroups)
    return {
        "beam_id": beam_id,
        "source_provenance": source_provenance,
        "target_identity": {**target, "confidence": vision.get("association_confidence")},
        "groups": groups,
        "stirrups": stirrups,
        "spacers": {
            "authority": AUTH_DET_ENG,
            "reason": REASON_DET_AUTHORITY,
            "groups": deterministic.get("spacers") or [],
        },
        "deterministic_engineering_data": {
            "cut_lengths": deterministic.get("engineering") or [],
            "authority": AUTH_DET_ENG,
            "note": "Preserved reference only. D.1 does not calculate or overwrite engineering outputs.",
        },
        "possible_duplicate_groups": dup_flags,
        "resolution_summary": {
            "vision_only_groups": len(matched["vision_only_indices"]),
            "deterministic_only_groups": len(matched["deterministic_only_indices"]),
            "matched_groups": len(matched["pairs"]),
            "possible_duplicates": len(dup_flags),
        },
    }


__all__ = ["resolve_beam", "resolve_group", "_resolved_field"]
