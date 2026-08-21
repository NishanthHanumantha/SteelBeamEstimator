"""Generic group reconciliation. Operates on evidence groups only. No beam-ID branches."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import (
    STATUS_AMBIGUOUS,
    STATUS_DET_CONFIRMED,
    STATUS_EQUIVALENT,
    STATUS_INSUFFICIENT,
    STATUS_VIS_CONFIRMED,
    STRENGTH_INSUFFICIENT,
    STRENGTH_LIMITED,
    STRENGTH_MODERATE,
    STRENGTH_STRONG,
)
from .normalize import as_group, keys_of, match_against


def _perfect(match: Dict[str, Any]) -> bool:
    return (
        int(match.get("missing") or 0) == 0
        and int(match.get("spurious") or 0) == 0
        and int(match.get("expected_count") or 0) > 0
    )


def _result_label(match: Dict[str, Any], *, truth_established: bool) -> str:
    if not truth_established:
        return "UNRESOLVED"
    if _perfect(match):
        return "MATCHES_RECONCILED_TRUTH"
    if int(match.get("correct") or 0) > 0:
        return "PARTIAL_VS_RECONCILED_TRUTH"
    return "DISAGREES_WITH_RECONCILED_TRUTH"


def reconcile_groups(
    *,
    vision_groups: Sequence[Dict[str, Any]],
    deterministic_groups: Sequence[Dict[str, Any]],
    p269_groups: Optional[Sequence[Dict[str, Any]]] = None,
    independent_groups: Optional[Sequence[Dict[str, Any]]] = None,
    independent_conflict: bool = False,
    independent_basis: Optional[str] = None,
) -> Dict[str, Any]:
    vis = list(vision_groups or [])
    det = list(deterministic_groups or [])
    p269 = list(p269_groups or [])
    independent = list(independent_groups or [])
    vis_keys = set(keys_of(vis))
    det_keys = set(keys_of(det))
    ind_keys = set(keys_of(independent))

    unresolved: List[Dict[str, Any]] = []
    truth: List[Tuple[str, str, str]] = []
    status = STATUS_INSUFFICIENT
    strength = STRENGTH_INSUFFICIENT
    confidence = "LOW"
    reason = ""
    truth_source = "NONE"

    if independent_conflict:
        status = STATUS_AMBIGUOUS
        strength = STRENGTH_LIMITED
        confidence = "LOW"
        reason = "Independent evidence sources disagree"
        truth_source = "CONFLICTING_INDEPENDENT"
        unresolved = [as_group(k, provenance="unresolved") for k in sorted(vis_keys | det_keys | ind_keys)]
    elif ind_keys:
        truth = sorted(ind_keys)
        vis_m = match_against(vis, independent)
        det_m = match_against(det, independent)
        vis_ok = _perfect(vis_m)
        det_ok = _perfect(det_m)
        if vis_ok and det_ok:
            status = STATUS_EQUIVALENT
            reason = "Independent evidence matches both interpretations after normalization"
        elif vis_ok and not det_ok:
            status = STATUS_VIS_CONFIRMED
            reason = "Independent evidence supports Vision over deterministic"
        elif det_ok and not vis_ok:
            status = STATUS_DET_CONFIRMED
            reason = "Independent evidence supports deterministic over Vision"
        else:
            status = STATUS_AMBIGUOUS
            reason = "Independent evidence exists but neither interpretation fully matches"
            unresolved = [as_group(k, provenance="unresolved") for k in truth]
            truth = []
        strength = STRENGTH_STRONG if str(independent_basis or "").upper().startswith("MANUAL") else STRENGTH_MODERATE
        confidence = "HIGH" if status in (STATUS_VIS_CONFIRMED, STATUS_DET_CONFIRMED, STATUS_EQUIVALENT) else "LOW"
        truth_source = independent_basis or "INDEPENDENT_EVIDENCE"
        if status == STATUS_AMBIGUOUS:
            strength = STRENGTH_LIMITED
    elif vis_keys and vis_keys == det_keys:
        truth = sorted(vis_keys)
        status = STATUS_EQUIVALENT
        strength = STRENGTH_MODERATE
        confidence = "MEDIUM"
        reason = "Deterministic and Vision resolve to the same physical groups after safe normalization"
        truth_source = "AGREEMENT_AFTER_NORMALIZATION"
    elif vis_keys and det_keys and vis_keys != det_keys:
        status = STATUS_AMBIGUOUS
        strength = STRENGTH_LIMITED
        confidence = "LOW"
        reason = "Deterministic and Vision conflict without independent arbiter"
        truth_source = "UNRESOLVED_CONFLICT"
        unresolved = [as_group(k, provenance="unresolved") for k in sorted(vis_keys | det_keys)]
    elif vis_keys or det_keys or set(keys_of(p269)):
        status = STATUS_INSUFFICIENT
        strength = STRENGTH_INSUFFICIENT
        confidence = "LOW"
        reason = "Only one interpretation is present; cannot establish reconciled truth"
        truth_source = "SINGLE_SOURCE"
        unresolved = [as_group(k, provenance="unresolved") for k in sorted(vis_keys | det_keys | set(keys_of(p269)))]
    else:
        status = STATUS_INSUFFICIENT
        strength = STRENGTH_INSUFFICIENT
        confidence = "LOW"
        reason = "MISSING_EVIDENCE"
        truth_source = "NONE"

    truth_groups = [as_group(k, provenance=truth_source) for k in truth]
    truth_established = bool(truth_groups)
    vis_vs = match_against(vis, truth_groups) if truth_established else {
        "expected_count": 0,
        "predicted_count": len(vis_keys),
        "correct": 0,
        "missing": 0,
        "spurious": 0,
        "matched": [],
        "missing_groups": [],
        "spurious_groups": [],
        "identity_rule": "layer+role+specification",
        "excluded_from_forced_correctness": True,
    }
    det_vs = match_against(det, truth_groups) if truth_established else {
        "expected_count": 0,
        "predicted_count": len(det_keys),
        "correct": 0,
        "missing": 0,
        "spurious": 0,
        "matched": [],
        "missing_groups": [],
        "spurious_groups": [],
        "identity_rule": "layer+role+specification",
        "excluded_from_forced_correctness": True,
    }
    if not truth_established:
        vis_vs["excluded_from_forced_correctness"] = True
        det_vs["excluded_from_forced_correctness"] = True

    return {
        "reconciliation_status": status,
        "reconciliation_confidence": confidence,
        "evidence_strength": strength,
        "truth_source_summary": truth_source,
        "unresolved_reason": reason if not truth_established else "",
        "reason": reason,
        "reconciled_groups": truth_groups,
        "unresolved_items": unresolved,
        "vision_vs_truth": vis_vs,
        "deterministic_vs_truth": det_vs,
        "vision_result": _result_label(vis_vs, truth_established=truth_established),
        "deterministic_result": _result_label(det_vs, truth_established=truth_established),
        "truth_established": truth_established,
    }


__all__ = ["reconcile_groups"]
