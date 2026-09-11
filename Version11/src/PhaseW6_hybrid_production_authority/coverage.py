"""Beam-level Hybrid crop-path and outcome coverage. No secrets."""
from __future__ import annotations

from typing import Any, Dict, List

CROP_P2610_PRIMARY = "P2610_PRIMARY_EVIDENCE"
CROP_T1_NATIVE = "T1_NATIVE_CROP"
CROP_W6_FALLBACK = "W6_GENERATED_FALLBACK_CROP"
CROP_UNAVAILABLE = "VISUAL_CONTEXT_UNAVAILABLE"
CROP_NOT_ELIGIBLE = "NOT_HYBRID_ELIGIBLE"

OUT_CLAUDE_SUCCESS = "CLAUDE_SUCCESS"
OUT_CLAUDE_FAILURE = "CLAUDE_FAILURE"
OUT_FALLBACK = "DETERMINISTIC_FALLBACK"
OUT_NOT_ELIGIBLE = "NOT_HYBRID_ELIGIBLE"

_P2610_SOURCES = {
    "P2610B1_ADAPTIVE_CONTEXT_DETAIL",
    "P2610_PRIMARY",
    "W8_EVIDENCE",
    "B.1",
}
_T1_SOURCES = {"T1_OPENCV_CROP", "T1_OPENCV_RENDERS", "T1"}
_W6_SOURCES = {"W6_ENVELOPE_RENDER", "T1_ENVELOPE_PLUS_M1_RENDERER", "W.6"}


def _crop_class(row: Dict[str, Any]) -> str:
    evidence_class = str(row.get("evidence_class") or "").upper()
    source = str(row.get("visual_source") or row.get("source") or "")
    available = bool(row.get("visual_available") or row.get("available"))
    if not available:
        return CROP_UNAVAILABLE
    if evidence_class in ("FALLBACK", "COMPATIBILITY"):
        if source in _W6_SOURCES or "W6" in source.upper() or "ENVELOPE" in source.upper() or source == "W8_SELECTED_MIXED":
            return CROP_W6_FALLBACK
        if source in _T1_SOURCES:
            return CROP_T1_NATIVE
        return CROP_W6_FALLBACK
    if evidence_class == "PRIMARY" or source in _P2610_SOURCES or source.startswith("P2610"):
        return CROP_P2610_PRIMARY
    if source in _W6_SOURCES or "W6" in source.upper() or "ENVELOPE" in source.upper():
        return CROP_W6_FALLBACK
    if source in _T1_SOURCES:
        return CROP_T1_NATIVE
    return CROP_T1_NATIVE


def _outcome_class(row: Dict[str, Any]) -> str:
    status = str(row.get("hybrid_status") or "")
    skip = str(row.get("skip_reason") or "")
    error = str(row.get("error_type") or "")
    if status == "OBSERVED":
        return OUT_CLAUDE_SUCCESS
    if (
        status == "HYBRID_ERROR"
        or skip in ("LIVE_CALL_EXCEPTION", "API_FAILED")
        or str(row.get("failure_category") or "") == "API_FAILED"
        or error in ("TimeoutError", "APIError", "APIStatusError", "APITimeoutError")
    ):
        return OUT_CLAUDE_FAILURE
    return OUT_FALLBACK


def _is_explicit_skip(row: Dict[str, Any]) -> bool:
    skip = str(row.get("skip_reason") or "")
    return skip in (
        "PER_RUN_REQUEST_LIMIT",
        "WALL_CLOCK_BUDGET",
        "LIVE_DISABLED",
        "ANTHROPIC_API_KEY_ABSENT",
        "ANTHROPIC_API_KEY_EMPTY",
    )


def build_coverage(
    *,
    mode: str,
    beam_ids: List[str],
    shadow_result: Dict[str, Any],
    visual_prep: Dict[str, Any],
) -> Dict[str, Any]:
    rows = [b for b in (shadow_result.get("beams") or []) if isinstance(b, dict)]
    by_id = {str(r.get("beam_id")): r for r in rows if r.get("beam_id")}
    eligible = [str(b) for b in beam_ids if str(b)]
    beams: List[Dict[str, Any]] = []
    unexplained: List[str] = []

    if mode == "off":
        return {
            "total_production_beams": len(eligible),
            "hybrid_eligible": 0,
            "p2610_primary_evidence": 0,
            "native_t1_crop": 0,
            "generated_fallback_crop": 0,
            "visual_context_unavailable": 0,
            "not_hybrid_eligible": len(eligible),
            "evidence_packages_generated": 0,
            "context_selected": 0,
            "detail_selected": 0,
            "multiple_detail_beams": 0,
            "w6_compatibility_path": 0,
            "t1_compatibility_path": 0,
            "fallback_path": 0,
            "evidence_unavailable": 0,
            "claude_invocations": 0,
            "claude_attempted": 0,
            "claude_success": 0,
            "claude_failure": 0,
            "explicitly_skipped": 0,
            "deterministic_fallback": 0,
            "hybrid_resolved": 0,
            "unresolved": 0,
            "unexplained": 0,
            "unexplained_ids": [],
            "visual_prep": visual_prep,
            "identity_ok": True,
            "beams": [],
        }

    for bid in eligible:
        row = by_id.get(bid)
        if row is None:
            unexplained.append(bid)
            beams.append(
                {
                    "beam_id": bid,
                    "crop_path": CROP_UNAVAILABLE,
                    "hybrid_outcome": OUT_FALLBACK,
                    "eligible": True,
                    "unexplained": True,
                }
            )
            continue
        crop = _crop_class(row)
        outcome = _outcome_class(row)
        beams.append(
            {
                "beam_id": bid,
                "crop_path": crop,
                "hybrid_outcome": outcome,
                "eligible": True,
                "unexplained": False,
                "visual_source": row.get("visual_source") or row.get("source"),
                "visual_available": bool(row.get("visual_available")),
                "called": bool(row.get("called")),
                "hybrid_status": row.get("hybrid_status"),
                "skip_reason": row.get("skip_reason"),
                "evidence_class": row.get("evidence_class"),
                "fallback_status": row.get("fallback_status"),
                "context_path": row.get("context_path"),
                "detail_path": row.get("detail_path"),
                "explicitly_skipped": _is_explicit_skip(row),
            }
        )

    extra = [bid for bid in by_id if bid not in set(eligible)]
    unexplained.extend(extra)

    primary = sum(1 for b in beams if b.get("crop_path") == CROP_P2610_PRIMARY)
    native = sum(1 for b in beams if b.get("crop_path") == CROP_T1_NATIVE)
    fallback_crop = sum(1 for b in beams if b.get("crop_path") == CROP_W6_FALLBACK)
    unavailable = sum(1 for b in beams if b.get("crop_path") == CROP_UNAVAILABLE)
    success = sum(1 for b in beams if b.get("hybrid_outcome") == OUT_CLAUDE_SUCCESS)
    failure = sum(1 for b in beams if b.get("hybrid_outcome") == OUT_CLAUDE_FAILURE)
    skipped = sum(1 for b in beams if b.get("explicitly_skipped"))
    det_fb = sum(1 for b in beams if b.get("hybrid_outcome") == OUT_FALLBACK)
    unresolved = sum(1 for b in beams if b.get("hybrid_outcome") != OUT_CLAUDE_SUCCESS)

    valid_evidence = primary + native + fallback_crop
    crop_sum = valid_evidence + unavailable
    outcome_sum = success + failure + det_fb
    sent_or_skipped = success + failure + skipped
    identity_ok = crop_sum == len(eligible) and outcome_sum == len(eligible) and len(unexplained) == 0

    prep = visual_prep if isinstance(visual_prep, dict) else {}
    return {
        "total_production_beams": len(eligible),
        "hybrid_eligible": len(eligible),
        "p2610_primary_evidence": primary,
        "native_t1_crop": native,
        "generated_fallback_crop": fallback_crop,
        "visual_context_unavailable": unavailable,
        "not_hybrid_eligible": 0,
        "evidence_packages_generated": int(prep.get("evidence_packages_generated") or valid_evidence),
        "context_selected": int(prep.get("context_selected") or valid_evidence),
        "detail_selected": int(prep.get("detail_selected") or valid_evidence),
        "multiple_detail_beams": int(prep.get("multiple_detail_beams") or 0),
        "w6_compatibility_path": fallback_crop,
        "t1_compatibility_path": native,
        "fallback_path": fallback_crop + native,
        "evidence_unavailable": unavailable,
        "claude_invocations": int(shadow_result.get("request_count") or 0),
        "claude_attempted": int(shadow_result.get("request_count") or 0),
        "claude_success": success,
        "claude_failure": failure,
        "explicitly_skipped": skipped,
        "deterministic_fallback": det_fb,
        "hybrid_resolved": success,
        "unresolved": unresolved,
        "unexplained": len(unexplained),
        "unexplained_ids": unexplained,
        "visual_prep": visual_prep,
        "identity_ok": identity_ok,
        "identity": {
            "eligible_equals_valid_plus_unavailable": crop_sum == len(eligible),
            "eligible_equals_outcomes": outcome_sum == len(eligible),
            "crop_sum": crop_sum,
            "outcome_sum": outcome_sum,
            "beams_with_valid_evidence": valid_evidence,
            "explicitly_unavailable_beams": unavailable,
            "claude_sent_or_explicitly_skipped": sent_or_skipped,
        },
        "beams": beams,
    }
