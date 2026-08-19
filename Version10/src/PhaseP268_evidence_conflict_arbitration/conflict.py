"""Conflict taxonomy. Multiple conflicts may apply; primary is the highest-severity identity conflict."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    CONFLICT_EQUAL_SPEC_LAYER,
    CONFLICT_EQUAL_SPEC_TARGET,
    CONFLICT_INSUFFICIENT,
    CONFLICT_LAYER,
    CONFLICT_LEADER,
    CONFLICT_NONE,
    CONFLICT_ROLE,
    CONFLICT_SEM_DIST_PHYS_DUP,
    CONFLICT_SEM_DUP_PHYS_DIST,
    CONFLICT_SPATIAL,
    CONFLICT_SPEC,
    LAYER_BOTTOM,
    LAYER_TOP,
    LAYER_UNKNOWN,
    PHYS_DISTINCT,
    PHYS_DUPLICATE,
    PHYS_INSUFFICIENT,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNUSABLE,
)
from .layer_resolver import layer_from_role

_PRIORITY = (
    CONFLICT_SEM_DUP_PHYS_DIST,
    CONFLICT_SEM_DIST_PHYS_DUP,
    CONFLICT_EQUAL_SPEC_LAYER,
    CONFLICT_EQUAL_SPEC_TARGET,
    CONFLICT_SPEC,
    CONFLICT_ROLE,
    CONFLICT_LAYER,
    CONFLICT_LEADER,
    CONFLICT_SPATIAL,
    CONFLICT_INSUFFICIENT,
    CONFLICT_NONE,
)


def detect_conflicts(evidence: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    found: List[str] = []
    det = evidence.get("deterministic_identity") or {}
    layer = evidence.get("layer") or {}
    prov = evidence.get("provenance") or {}
    quality = evidence.get("evidence_quality") or {}
    physical = str(det.get("physical") or PHYS_INSUFFICIENT)
    populated = str(det.get("populated_layer") or LAYER_UNKNOWN)
    cand_layer = str(layer.get("resolved_layer") or evidence.get("layer_hint") or LAYER_UNKNOWN)
    sem = evidence.get("semantic_identity") or {}
    sem_decision = str(sem.get("decision") or SEM_UNUSABLE)
    sem_layer = str(sem.get("target_layer") or LAYER_UNKNOWN).upper()
    spec_any = bool(evidence.get("spec_match_any_layer"))
    usable = bool(sem.get("usable"))

    if physical == PHYS_DISTINCT:
        reasons.extend(["DETERMINISTIC_DISTINCT", "PHYSICAL_TARGET_MISMATCH"])
    elif physical == PHYS_DUPLICATE:
        reasons.extend(["DETERMINISTIC_DUPLICATE", "PHYSICAL_TARGET_MATCH"])
    else:
        reasons.append("INSUFFICIENT_PHYSICAL_EVIDENCE")

    if spec_any:
        reasons.append("SPEC_MATCH")
    elif evidence.get("normalized_specification"):
        reasons.append("SPEC_MISMATCH")

    if cand_layer in (LAYER_TOP, LAYER_BOTTOM) and populated in (LAYER_TOP, LAYER_BOTTOM):
        reasons.append("LAYER_MATCH" if cand_layer == populated else "LAYER_MISMATCH")

    if sem_decision == SEM_DUPLICATE:
        reasons.append("SEMANTIC_DUPLICATE")
    elif sem_decision == SEM_DISTINCT:
        reasons.append("SEMANTIC_DISTINCT")
    elif not usable or sem_decision == SEM_UNUSABLE:
        reasons.append("SEMANTIC_UNUSABLE")

    if usable and sem_decision == SEM_DUPLICATE and physical == PHYS_DISTINCT:
        found.append(CONFLICT_SEM_DUP_PHYS_DIST)
        reasons.extend(["DETERMINISTIC_EVIDENCE_STRONGER", "SEMANTIC_EVIDENCE_WEAKER"])
    if usable and sem_decision == SEM_DISTINCT and physical == PHYS_DUPLICATE:
        found.append(CONFLICT_SEM_DIST_PHYS_DUP)
        reasons.extend(["DETERMINISTIC_EVIDENCE_STRONGER", "SEMANTIC_EVIDENCE_WEAKER"])

    if (
        spec_any
        and cand_layer in (LAYER_TOP, LAYER_BOTTOM)
        and populated in (LAYER_TOP, LAYER_BOTTOM)
        and cand_layer != populated
    ):
        found.append(CONFLICT_EQUAL_SPEC_LAYER)
        reasons.append("EQUAL_SPEC_CROSS_LAYER")
    elif spec_any and physical == PHYS_DISTINCT and cand_layer == populated and cand_layer != LAYER_UNKNOWN:
        found.append(CONFLICT_EQUAL_SPEC_TARGET)

    if evidence.get("normalized_specification") and not spec_any and physical == PHYS_DISTINCT:
        found.append(CONFLICT_SPEC)

    role = str(evidence.get("semantic_role") or "").upper()
    if role and role not in ("UNKNOWN", "", "OTHER") and cand_layer in (LAYER_TOP, LAYER_BOTTOM):
        role_layer = layer_from_role(role)
        if role_layer in (LAYER_TOP, LAYER_BOTTOM) and role_layer != cand_layer:
            found.append(CONFLICT_ROLE)

    if usable and sem_layer in (LAYER_TOP, LAYER_BOTTOM) and cand_layer in (LAYER_TOP, LAYER_BOTTOM) and sem_layer != cand_layer:
        found.append(CONFLICT_LAYER)

    leader_layer = str(layer.get("leader_layer") or LAYER_UNKNOWN)
    if usable and sem_layer in (LAYER_TOP, LAYER_BOTTOM) and leader_layer in (LAYER_TOP, LAYER_BOTTOM) and sem_layer != leader_layer:
        found.append(CONFLICT_LEADER)
        reasons.append("LEADER_MISMATCH")
    elif leader_layer in (LAYER_TOP, LAYER_BOTTOM) and cand_layer == leader_layer:
        reasons.append("LEADER_MATCH")

    spatial_status = str(prov.get("p265_context_status") or "")
    spatial_contradicts_duplicate = spatial_status == "CONTEXT_SUPPORTS_CALL" and physical == PHYS_DUPLICATE
    spatial_contradicts_distinct = spatial_status == "CONTEXT_SUPPORTS_SKIP" and physical == PHYS_DISTINCT
    if spatial_contradicts_duplicate:
        reasons.extend(["SPATIAL_MISMATCH", "ANNOTATION_REPRESENTATION_ONLY"])
    elif spatial_contradicts_distinct:
        found.append(CONFLICT_SPATIAL)
        reasons.append("SPATIAL_MISMATCH")
    elif spatial_status in ("CONTEXT_SUPPORTS_CALL", "CONTEXT_SUPPORTS_SKIP", ""):
        reasons.append("SPATIAL_MATCH")

    if quality.get("layer_evidence_incomplete") and physical == PHYS_INSUFFICIENT and not found:
        found.append(CONFLICT_INSUFFICIENT)

    ordered = [c for c in _PRIORITY if c in found]
    primary = ordered[0] if ordered else CONFLICT_NONE
    return {
        "conflict_type": primary,
        "conflict_types": ordered if ordered else [CONFLICT_NONE],
        "reason_codes": list(dict.fromkeys(reasons)),
        "semantic_usable": usable,
    }


__all__ = ["detect_conflicts"]
