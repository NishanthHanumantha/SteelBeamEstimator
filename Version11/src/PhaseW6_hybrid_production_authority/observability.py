"""Safe Hybrid production observability. Never logs secrets."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseW5_production_hybrid_shadow.config import (
    STATUS_ERROR,
    STATUS_KEY_ABSENT,
    STATUS_PARTIAL_BUDGET,
)

from .config import (
    CLASS_API_ERROR,
    CLASS_FALLBACK,
    CLASS_RESOLUTION_ERROR,
    CLASS_SKIPPED,
    CLASS_SUCCESS,
    CLASS_TIMEOUT,
    CLASS_UNAVAILABLE,
)


def classify_run(
    *,
    mode: str,
    shadow_result: Dict[str, Any],
    handoff: Dict[str, Any],
) -> str:
    if mode == "off":
        return CLASS_SKIPPED
    status = str(shadow_result.get("hybrid_status") or "")
    reason = str(shadow_result.get("reason") or "")
    if status == STATUS_KEY_ABSENT:
        return CLASS_UNAVAILABLE
    if "TIMEOUT" in reason.upper() or "WALL_CLOCK" in reason.upper():
        return CLASS_TIMEOUT
    beams = shadow_result.get("beams") or []
    if any(str(b.get("error_type") or "") == "TimeoutError" for b in beams if isinstance(b, dict)):
        return CLASS_TIMEOUT
    if any(str(b.get("skip_reason") or "") == "LIVE_CALL_EXCEPTION" for b in beams if isinstance(b, dict)):
        return CLASS_API_ERROR
    if status == STATUS_ERROR:
        return CLASS_RESOLUTION_ERROR
    if mode == "production" and handoff.get("applied"):
        return CLASS_SUCCESS
    if mode == "production":
        return CLASS_FALLBACK
    if status == STATUS_PARTIAL_BUDGET:
        return CLASS_TIMEOUT if "WALL" in reason.upper() else CLASS_FALLBACK
    return CLASS_SUCCESS if status in ("COMPLETE",) else CLASS_FALLBACK


def beam_counts(shadow_result: Dict[str, Any]) -> Dict[str, int]:
    resolved = 0
    unresolved = 0
    fallback = 0
    timeout = 0
    failed = 0
    called = 0
    for row in shadow_result.get("beams") or []:
        if not isinstance(row, dict):
            continue
        if row.get("called"):
            called += 1
        status = str(row.get("hybrid_status") or "")
        if status == "OBSERVED":
            resolved += 1
        elif row.get("error_type") == "TimeoutError" or row.get("skip_reason") == "WALL_CLOCK_BUDGET":
            timeout += 1
            unresolved += 1
        elif status in ("HYBRID_ERROR",):
            failed += 1
            unresolved += 1
        else:
            unresolved += 1
            fallback += 1
    return {
        "semantic_items_resolved": resolved,
        "semantic_items_unresolved": unresolved,
        "deterministic_fallback_usage": fallback,
        "timeout_count": timeout,
        "failed_invocation_count": failed,
        "claude_invocation_count": int(shadow_result.get("request_count") or called),
        "successful_invocation_count": resolved,
    }


def public_observability(
    *,
    run_id: str,
    mode: str,
    shadow_result: Dict[str, Any],
    handoff: Dict[str, Any],
    classification: str,
    primed_key: bool,
) -> Dict[str, Any]:
    counts = beam_counts(shadow_result)
    settings = shadow_result.get("settings") if isinstance(shadow_result.get("settings"), dict) else {}
    return {
        "phase_id": "W.6",
        "run_id": run_id,
        "hybrid_mode": mode,
        "hybrid_enabled": mode != "off",
        "hybrid_invocation_attempted": bool(shadow_result.get("hybrid_started")) and mode != "off",
        "api_key_configured": primed_key or settings.get("api_key_status") == "PRESENT",
        "classification": classification,
        "hybrid_status": shadow_result.get("hybrid_status"),
        "reason": shadow_result.get("reason"),
        "production_authority": "semantic_only" if mode == "production" else "none",
        "production_authority_applied": bool(handoff.get("applied")),
        "handoff_reason": handoff.get("reason"),
        "beams_patched": handoff.get("beams_patched") or 0,
        "fields_patched": handoff.get("fields_patched") or 0,
        "unresolved_vision_only": handoff.get("unresolved_vision_only") or 0,
        "fallback_used": classification in (CLASS_FALLBACK, CLASS_UNAVAILABLE, CLASS_TIMEOUT, CLASS_API_ERROR, CLASS_RESOLUTION_ERROR),
        "provider": shadow_result.get("provider"),
        "model": shadow_result.get("model"),
        "claude_invocation_count": counts["claude_invocation_count"],
        "successful_invocation_count": counts["successful_invocation_count"],
        "failed_invocation_count": counts["failed_invocation_count"],
        "timeout_count": counts["timeout_count"],
        "fallback_count": counts["deterministic_fallback_usage"],
        "hybrid_latency_s": shadow_result.get("hybrid_latency_s"),
        "semantic_items_resolved": counts["semantic_items_resolved"],
        "semantic_items_unresolved": counts["semantic_items_unresolved"],
        "deterministic_fallback_usage": counts["deterministic_fallback_usage"],
        "beam_count": shadow_result.get("beam_count"),
        "visual_available_count": shadow_result.get("visual_available_count"),
        "cache_hits": shadow_result.get("cache_hits"),
        "cost_basis": shadow_result.get("cost_basis"),
        "final_hybrid_status": classification,
    }


def public_summary(observability: Dict[str, Any]) -> Dict[str, Any]:
    keys: List[str] = [
        "hybrid_mode",
        "hybrid_status",
        "classification",
        "reason",
        "production_authority",
        "production_authority_applied",
        "handoff_reason",
        "claude_invocation_count",
        "successful_invocation_count",
        "failed_invocation_count",
        "timeout_count",
        "fallback_count",
        "hybrid_latency_s",
        "semantic_items_resolved",
        "semantic_items_unresolved",
        "beams_patched",
        "fields_patched",
        "fallback_used",
        "model",
        "beam_count",
        "request_count",
        "coverage",
    ]
    out = {k: observability.get(k) for k in keys if k in observability}
    out["request_count"] = observability.get("claude_invocation_count")
    out["hybrid_status"] = observability.get("classification") or observability.get("hybrid_status")
    return out
