"""Deterministic arbitration. LLM never outranks strong physical/layer evidence."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    ARB_AGREE,
    ARB_DET_OVERRIDES,
    ARB_INSUFFICIENT,
    ARB_REVIEW,
    ARB_SEM_SUPPORTS,
    ARB_UNUSABLE,
    CONFLICT_EQUAL_SPEC_LAYER,
    CONFLICT_INSUFFICIENT,
    CONFLICT_NONE,
    CONFLICT_SEM_DIST_PHYS_DUP,
    CONFLICT_SEM_DUP_PHYS_DIST,
    PHASE_ID,
    PHYS_DISTINCT,
    PHYS_DUPLICATE,
    PHYS_INSUFFICIENT,
    PRODUCTION_ACTION,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNUSABLE,
    SHADOW_ONLY,
    SRC_DET_LAYER,
    SRC_DET_PHYSICAL,
    SRC_DRAWING,
    SRC_LEADER,
    SRC_LLM,
    SRC_SPATIAL,
    STRENGTH_MEDIUM,
    STRENGTH_NONE,
    STRENGTH_STRONG,
    STRENGTH_WEAK,
)
from .conflict import detect_conflicts


def _winning_source(evidence: Dict[str, Any], conflict_type: str) -> str:
    det = evidence.get("deterministic_identity") or {}
    physical = str(det.get("physical") or PHYS_INSUFFICIENT)
    quality = evidence.get("evidence_quality") or {}
    if physical in (PHYS_DISTINCT, PHYS_DUPLICATE):
        return SRC_DET_PHYSICAL
    if conflict_type == CONFLICT_EQUAL_SPEC_LAYER:
        return SRC_DET_LAYER
    if quality.get("leader_geometry_available"):
        return SRC_LEADER
    if (evidence.get("provenance") or {}).get("p265_context_status"):
        return SRC_SPATIAL
    if evidence.get("normalized_specification"):
        return SRC_DRAWING
    return SRC_LLM


def _strength(evidence: Dict[str, Any], winning: str) -> str:
    det = evidence.get("deterministic_identity") or {}
    physical = str(det.get("physical") or PHYS_INSUFFICIENT)
    if winning == SRC_DET_PHYSICAL and physical in (PHYS_DISTINCT, PHYS_DUPLICATE):
        return STRENGTH_STRONG
    if winning in (SRC_DET_LAYER, SRC_LEADER):
        return STRENGTH_MEDIUM
    if winning == SRC_LLM:
        return STRENGTH_WEAK
    if physical == PHYS_INSUFFICIENT:
        return STRENGTH_NONE
    return STRENGTH_MEDIUM


def arbitrate(evidence: Dict[str, Any]) -> Dict[str, Any]:
    conflicts = detect_conflicts(evidence)
    conflict_type = conflicts.get("conflict_type") or CONFLICT_NONE
    reasons: List[str] = list(conflicts.get("reason_codes") or [])
    sem = evidence.get("semantic_identity") or {}
    usable = bool(sem.get("usable"))
    sem_decision = str(sem.get("decision") or SEM_UNUSABLE)
    physical = str((evidence.get("deterministic_identity") or {}).get("physical") or PHYS_INSUFFICIENT)
    winning = _winning_source(evidence, conflict_type)
    strength = _strength(evidence, winning)

    if not usable and physical == PHYS_INSUFFICIENT:
        result = ARB_UNUSABLE
    elif conflict_type in (CONFLICT_SEM_DUP_PHYS_DIST, CONFLICT_SEM_DIST_PHYS_DUP):
        result = ARB_DET_OVERRIDES
        winning = SRC_DET_PHYSICAL
        strength = STRENGTH_STRONG
        if "DETERMINISTIC_EVIDENCE_STRONGER" not in reasons:
            reasons.append("DETERMINISTIC_EVIDENCE_STRONGER")
    elif conflict_type == CONFLICT_EQUAL_SPEC_LAYER:
        if usable and sem_decision == SEM_DUPLICATE:
            result = ARB_DET_OVERRIDES
            winning = SRC_DET_LAYER
        elif usable and sem_decision == SEM_DISTINCT:
            result = ARB_SEM_SUPPORTS
            winning = SRC_DET_LAYER
        else:
            result = ARB_REVIEW
            winning = SRC_DET_LAYER
        strength = STRENGTH_STRONG
    elif conflict_type == CONFLICT_INSUFFICIENT or physical == PHYS_INSUFFICIENT:
        result = ARB_INSUFFICIENT if usable else ARB_UNUSABLE
        strength = STRENGTH_NONE
    elif conflict_type == CONFLICT_NONE:
        if usable and (
            (sem_decision == SEM_DUPLICATE and physical == PHYS_DUPLICATE)
            or (sem_decision == SEM_DISTINCT and physical == PHYS_DISTINCT)
        ):
            result = ARB_AGREE
        elif usable:
            result = ARB_SEM_SUPPORTS
        else:
            result = ARB_INSUFFICIENT
    else:
        result = ARB_REVIEW

    det_summary = {
        "physical": physical,
        "populated_layer": (evidence.get("deterministic_identity") or {}).get("populated_layer"),
        "match_status": (evidence.get("deterministic_identity") or {}).get("match_status"),
        "specification": evidence.get("normalized_specification"),
        "spec_match_any_layer": evidence.get("spec_match_any_layer"),
        "spec_match_same_layer": evidence.get("spec_match_same_layer"),
    }
    return {
        "phase": PHASE_ID,
        "candidate_id": evidence.get("candidate_id"),
        "set_key": evidence.get("set_key"),
        "beam_id": evidence.get("beam_id"),
        "semantic_result": {
            "decision": sem_decision,
            "source": sem.get("source"),
            "usable": usable,
            "target_layer": sem.get("target_layer"),
            "confidence": sem.get("confidence"),
        },
        "deterministic_result": det_summary,
        "resolved_layer": (evidence.get("layer") or {}).get("resolved_layer") or evidence.get("layer_hint"),
        "conflict_type": conflict_type,
        "conflict_types": conflicts.get("conflict_types"),
        "arbitration_result": result,
        "evidence_strength": strength,
        "confidence": 0.9 if strength == STRENGTH_STRONG else (0.6 if strength == STRENGTH_MEDIUM else 0.3),
        "winning_evidence_source": winning,
        "reason_codes": list(dict.fromkeys(reasons)),
        "rationale": (
            f"{conflict_type}: deterministic={physical} semantic={sem_decision} "
            f"winner={winning} action={PRODUCTION_ACTION}"
        ),
        "production_action": PRODUCTION_ACTION,
        "shadow_only": SHADOW_ONLY,
        "p266_semantic": evidence.get("p266_semantic"),
        "p267_semantic": evidence.get("p267_semantic"),
        "layer_evidence": evidence.get("layer"),
        "target_evidence": {
            "physical": physical,
            "leader": (evidence.get("spatial_position") or {}),
            "spatial_status": (evidence.get("provenance") or {}).get("p265_context_status"),
        },
        "observed_decision": (evidence.get("provenance") or {}).get("observed_decision"),
        "longitudinal_coverage": (evidence.get("provenance") or {}).get("longitudinal_coverage"),
        "production_routing_changed": False,
    }


__all__ = ["arbitrate"]
