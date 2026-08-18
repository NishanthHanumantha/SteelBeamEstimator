"""Replay frozen P2.6.1 Vision observations into the P2.6.6 semantic schema.

Uses deterministic_match_status only. Never uses labelled match outcome fields.
This is an observation adapter, not a live targeted-prompt hit.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP26_vision_candidate_recovery.deterministic_comparator import role_family

from .config import (
    ADAPTER_AMBIGUOUS_CONFIDENCE,
    ADAPTER_DISTINCT_CONFIDENCE,
    ADAPTER_DUPLICATE_CONFIDENCE,
    ADAPTER_SOURCE,
    ADAPTER_UNSUPPORTED_CONFIDENCE,
    DET_ALREADY,
    DET_CONFLICT,
    DET_MISSING,
    LAYER_BOTTOM,
    LAYER_SIDE,
    LAYER_TOP,
    LAYER_UNKNOWN,
    REP_NOT_REPRESENTED,
    REP_REPRESENTED,
    REP_UNCERTAIN,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNSUPPORTED,
    STATUS_AMBIGUOUS,
    STATUS_CALL,
    STATUS_INSUFFICIENT,
    STATUS_SKIP,
)
from .semantic_schema import normalize_semantic_payload


def _layer_from_role(role: Any) -> str:
    fam = role_family(role)
    if fam == "TOP":
        return LAYER_TOP
    if fam == "BOTTOM":
        return LAYER_BOTTOM
    if fam == "SIDE":
        return LAYER_SIDE
    return LAYER_UNKNOWN


def _long_rows(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for cand in candidates:
        ctype = str(cand.get("candidate_type") or "").upper()
        if "LONGITUDINAL" not in ctype:
            continue
        rows.append(cand)
    return rows


def _notes(rows: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for cand in rows:
        for note in cand.get("evidence_notes") or []:
            text = str(note).strip()
            if text and text not in out:
                out.append(text)
    return out[:8]


def _populated_layer(context: Dict[str, Any]) -> str:
    det = context.get("deterministic_reinforcement") or {}
    roles = det.get("role_assignments") or {}
    spat = context.get("spatial_context") or {}
    return str(roles.get("populated_layer") or spat.get("populated_layer") or "").upper()


def _spatial_consistent(decision: str, spatial_status: str) -> bool:
    status = str(spatial_status or "")
    if decision == SEM_DISTINCT:
        return status in (STATUS_CALL, "")
    if decision == SEM_DUPLICATE:
        return status == STATUS_SKIP
    if status in (STATUS_AMBIGUOUS, STATUS_INSUFFICIENT, ""):
        return False
    return False


def adapt_frozen_observations(
    *,
    context: Dict[str, Any],
    frozen_candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    rows = _long_rows(frozen_candidates)
    spatial_status = str((context.get("spatial_context") or {}).get("spatial_context_status") or "")
    populated = _populated_layer(context)
    if not rows:
        payload = {
            "decision": SEM_UNSUPPORTED,
            "confidence": ADAPTER_UNSUPPORTED_CONFIDENCE,
            "annotation_interpretation": "No frozen longitudinal Vision observation for this beam.",
            "target_layer": LAYER_UNKNOWN,
            "existing_representation_assessment": REP_UNCERTAIN,
            "semantic_reason_codes": ["BEAM_CONTEXT_INSUFFICIENT"],
            "visual_evidence": [],
            "deterministic_context_consistent": False,
            "spatial_context_consistent": False,
            "conflict_present": False,
        }
        out = normalize_semantic_payload(payload)
        out["source"] = ADAPTER_SOURCE
        return out

    missing = [c for c in rows if c.get("deterministic_match_status") == DET_MISSING]
    conflict = [c for c in rows if c.get("deterministic_match_status") == DET_CONFLICT]
    already = [c for c in rows if c.get("deterministic_match_status") == DET_ALREADY]
    primary = (missing or conflict or already or rows)[0]
    target_layer = _layer_from_role(primary.get("role"))
    texts = sorted(
        {
            str(c.get("annotation_text") or c.get("normalized_text") or "").strip()
            for c in rows
            if str(c.get("annotation_text") or c.get("normalized_text") or "").strip()
        }
    )
    visual = _notes(rows)
    missing_layers = {_layer_from_role(c.get("role")) for c in missing}
    codes: List[str] = []
    conflict_present = bool(conflict) or (bool(missing) and bool(already) and not missing_layers.difference({populated, LAYER_UNKNOWN}))

    if missing:
        decision = SEM_DISTINCT
        confidence = ADAPTER_DISTINCT_CONFIDENCE
        assessment = REP_NOT_REPRESENTED
        codes.append("UNREPRESENTED_REINFORCEMENT")
        if LAYER_BOTTOM in missing_layers and populated == LAYER_TOP:
            codes.extend(["DISTINCT_LAYER", "EXPLICIT_BOTTOM_WHILE_TOP_ONLY"])
        elif LAYER_TOP in missing_layers and populated == LAYER_BOTTOM:
            codes.extend(["DISTINCT_LAYER", "EXPLICIT_TOP_WHILE_BOTTOM_ONLY"])
        elif target_layer in (LAYER_TOP, LAYER_BOTTOM) and populated and target_layer != populated:
            codes.append("DISTINCT_LAYER")
        else:
            codes.append("DISTINCT_CALLOUT_TARGET")
        if len(missing) >= 2:
            codes.append("SEPARATE_REPEATED_SPEC")
        interp = (
            "Frozen Vision longitudinal observation has no equivalent deterministic bar "
            f"({', '.join(texts) or 'annotation'})."
        )
        det_consistent = True
    elif conflict and not already:
        decision = SEM_AMBIGUOUS
        confidence = ADAPTER_AMBIGUOUS_CONFIDENCE
        assessment = REP_UNCERTAIN
        codes.extend(["DETERMINISTIC_VISION_CONFLICT", "MULTIPLE_PLAUSIBLE_TARGETS"])
        interp = (
            "Frozen Vision longitudinal observation conflicts with an existing deterministic bar "
            f"({', '.join(texts) or 'annotation'})."
        )
        det_consistent = False
        conflict_present = True
    elif already and not missing and not conflict:
        decision = SEM_DUPLICATE
        confidence = ADAPTER_DUPLICATE_CONFIDENCE
        assessment = REP_REPRESENTED
        codes.extend(
            ["ALREADY_REPRESENTED_LAYER", "SAME_REINFORCEMENT_TARGET", "DUPLICATE_ANNOTATION"]
        )
        if spatial_status == STATUS_CALL:
            codes.append("CROSS_LAYER_AMBIGUITY")
        interp = (
            "Frozen Vision longitudinal observation matches an existing deterministic bar "
            f"({', '.join(texts) or 'annotation'})."
        )
        det_consistent = True
    else:
        decision = SEM_AMBIGUOUS
        confidence = ADAPTER_AMBIGUOUS_CONFIDENCE
        assessment = REP_UNCERTAIN
        codes.extend(["DETERMINISTIC_VISION_CONFLICT", "MULTIPLE_PLAUSIBLE_TARGETS"])
        interp = "Frozen Vision longitudinal observations disagree on whether the spec is already represented."
        det_consistent = False
        conflict_present = True

    spatial_ok = _spatial_consistent(decision, spatial_status)
    payload = {
        "decision": decision,
        "confidence": confidence,
        "annotation_interpretation": interp,
        "target_layer": target_layer,
        "existing_representation_assessment": assessment,
        "semantic_reason_codes": list(dict.fromkeys(codes)),
        "visual_evidence": visual,
        "deterministic_context_consistent": det_consistent,
        "spatial_context_consistent": spatial_ok,
        "conflict_present": conflict_present,
    }
    out = normalize_semantic_payload(payload)
    out["source"] = ADAPTER_SOURCE
    out["adapter_observation_count"] = len(rows)
    out["adapter_match_statuses"] = sorted(
        {str(c.get("deterministic_match_status") or "") for c in rows}
    )
    return out


__all__ = ["adapt_frozen_observations"]
