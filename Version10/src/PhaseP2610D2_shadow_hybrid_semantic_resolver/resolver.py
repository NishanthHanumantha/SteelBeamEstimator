"""Apply the D.1 authority contract to produce a D.2 canonical hybrid object."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.config import (
    AUTH_DET_ENG,
    REASON_DET_ONLY,
    REASON_VISION_ONLY,
)
from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.resolver import resolve_group, _resolved_field
from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_validator import flag_possible_duplicates

from .canonical import canonical_field, engineering_refs
from .config import REASON_AMBIGUOUS, REASON_DET_AUTH, SRC_DET
from .matching import match_groups_conservative, match_stirrups_conservative


def _group_payload(
    *,
    vision: Optional[Dict[str, Any]],
    deterministic: Optional[Dict[str, Any]],
    beam_usable: bool,
    origin: str,
    match_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw = resolve_group(vision=vision, deterministic=deterministic, beam_usable=beam_usable, origin=origin)
    conf = raw.get("vision_confidence")
    fields = {}
    for name in ("layer", "role", "bar_count", "diameter", "specification", "support_scope"):
        fields[name] = canonical_field(raw[name], origin=origin, confidence=conf if name != "role" else (vision or {}).get("role_confidence") or conf)
    return {
        "group_id": raw.get("group_id"),
        "origin": origin,
        **fields,
        "deterministic_engineering": engineering_refs(deterministic),
        "relative_span_length": raw.get("relative_span_length"),
        "relative_group_extent": raw.get("relative_group_extent"),
        "longer_bar_likely_main_hook": "ARCHITECTURE_HOOK_ONLY",
        "provenance": {
            "vision_available": vision is not None,
            "deterministic_available": deterministic is not None,
            "conflict_detected": any(fields[n].get("conflict_detected") for n in fields),
            "resolution_reason": origin if origin != "MATCHED" else (
                REASON_AMBIGUOUS if (match_meta or {}).get("ambiguous") else "MATCHED"
            ),
            "vision_id": (vision or {}).get("physical_group_id"),
            "deterministic_id": (deterministic or {}).get("physical_group_id"),
            "match_score": (match_meta or {}).get("score"),
        },
    }


def resolve_hybrid_beam(
    *,
    beam_id: str,
    vision: Dict[str, Any],
    deterministic: Dict[str, Any],
    source_provenance: Dict[str, Any],
) -> Dict[str, Any]:
    usable = bool(vision.get("usable"))
    target_raw = _resolved_field(
        field="TARGET_IDENTITY",
        vision_value=vision.get("target_beam_id") if vision.get("target_identified") else None,
        deterministic_value=beam_id,
        confidence=vision.get("association_confidence"),
        beam_usable=usable,
    )
    target = canonical_field(target_raw, origin="MATCHED", confidence=vision.get("association_confidence"))

    vgroups = list(vision.get("groups") or [])
    dgroups = list(deterministic.get("groups") or [])
    matched = match_groups_conservative(vgroups, dgroups)
    groups: List[Dict[str, Any]] = []
    for p in matched["pairs"]:
        groups.append(
            _group_payload(
                vision=vgroups[p["vision_index"]],
                deterministic=dgroups[p["deterministic_index"]],
                beam_usable=usable,
                origin="MATCHED",
                match_meta=p,
            )
        )
    amb_v = {a["vision_index"] for a in matched["ambiguous"]}
    for a in matched["ambiguous"]:
        groups.append(
            _group_payload(
                vision=vgroups[a["vision_index"]],
                deterministic=None,
                beam_usable=usable,
                origin=REASON_VISION_ONLY,
                match_meta={"ambiguous": True, "score": a.get("score")},
            )
        )
    for i in matched["vision_only_indices"]:
        if i in amb_v:
            continue
        groups.append(_group_payload(vision=vgroups[i], deterministic=None, beam_usable=usable, origin=REASON_VISION_ONLY))
    for j in matched["deterministic_only_indices"]:
        groups.append(_group_payload(vision=None, deterministic=dgroups[j], beam_usable=usable, origin=REASON_DET_ONLY))

    vst = list(vision.get("stirrups") or [])
    dst = list(deterministic.get("stirrups") or [])
    st_match = match_stirrups_conservative(vst, dst)
    stirrups = []
    for p in st_match["pairs"]:
        vis = vst[p["vision_index"]]
        det = dst[p["deterministic_index"]]
        ident = canonical_field(
            _resolved_field(
                field="STIRRUP_IDENTIFICATION",
                vision_value=vis.get("specification"),
                deterministic_value=det.get("specification"),
                confidence=vis.get("confidence"),
                spec=vis.get("specification"),
                beam_usable=usable,
            ),
            origin="MATCHED",
            confidence=vis.get("confidence"),
        )
        stirrups.append(
            {
                "origin": "MATCHED",
                "semantic_identification": ident,
                "engineering_calculation_reference": {
                    "source": SRC_DET,
                    "authority": AUTH_DET_ENG,
                    "cut_length_mm": det.get("cut_length_mm"),
                    "specification": det.get("specification"),
                    "reason": REASON_DET_AUTH,
                },
            }
        )
    for i in st_match["vision_only_indices"]:
        vis = vst[i]
        ident = canonical_field(
            _resolved_field(
                field="STIRRUP_IDENTIFICATION",
                vision_value=vis.get("specification"),
                deterministic_value=None,
                confidence=vis.get("confidence"),
                spec=vis.get("specification"),
                beam_usable=usable,
            ),
            origin=REASON_VISION_ONLY,
            confidence=vis.get("confidence"),
        )
        stirrups.append(
            {
                "origin": REASON_VISION_ONLY,
                "semantic_identification": ident,
                "engineering_calculation_reference": {"source": SRC_DET, "authority": AUTH_DET_ENG, "reason": REASON_DET_AUTH, "cut_length_mm": "UNAVAILABLE"},
            }
        )
    for j in st_match["deterministic_only_indices"]:
        det = dst[j]
        ident = canonical_field(
            _resolved_field(
                field="STIRRUP_IDENTIFICATION",
                vision_value=None,
                deterministic_value=det.get("specification"),
                confidence=None,
                beam_usable=usable,
            ),
            origin=REASON_DET_ONLY,
        )
        stirrups.append(
            {
                "origin": REASON_DET_ONLY,
                "semantic_identification": ident,
                "engineering_calculation_reference": {
                    "source": SRC_DET,
                    "authority": AUTH_DET_ENG,
                    "cut_length_mm": det.get("cut_length_mm"),
                    "specification": det.get("specification"),
                    "reason": REASON_DET_AUTH,
                },
            }
        )

    return {
        "beam_id": beam_id,
        "source_provenance": source_provenance,
        "target_identity": target,
        "reinforcement_groups": groups,
        "stirrups": {
            "items": stirrups,
            "semantic_identification_authority": "VISION_PREFERRED",
            "engineering_calculation_authority": AUTH_DET_ENG,
        },
        "spacers": {
            "source": SRC_DET,
            "authority": AUTH_DET_ENG,
            "reason": REASON_DET_AUTH,
            "groups": deterministic.get("spacers") or [],
        },
        "group_matching": {
            "matched": len(matched["pairs"]),
            "vision_only": len([i for i in matched["vision_only_indices"] if i not in amb_v]),
            "deterministic_only": len(matched["deterministic_only_indices"]),
            "ambiguous": len(matched["ambiguous"]),
            "possible_duplicates": matched["possible_duplicates"],
            "pairs": matched["pairs"],
            "ambiguous_records": matched["ambiguous"],
        },
        "possible_duplicate_groups": flag_possible_duplicates(vgroups),
        "successfully_resolved": target.get("source") != "UNRESOLVED",
    }


__all__ = ["resolve_hybrid_beam"]
