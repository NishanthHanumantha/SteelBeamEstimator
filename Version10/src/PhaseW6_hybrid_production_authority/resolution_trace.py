"""Per-beam Hybrid resolution trace. Reconstructs lifecycle without secrets."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

TRACE_FILENAME = "hybrid_resolution_trace.json"

STATUS_HYBRID_RESOLVED = "HYBRID_RESOLVED"
STATUS_DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK_WITH_REASON"
STATUS_VISION_FAILED = "VISION_FAILED_WITH_REASON"
STATUS_EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE_WITH_REASON"

REASON_VISION_NOT_ATTEMPTED = "VISION_NOT_ATTEMPTED"
REASON_VISION_TIMEOUT = "VISION_TIMEOUT"
REASON_VISION_API_ERROR = "VISION_API_ERROR"
REASON_VISION_RESPONSE_INVALID = "VISION_RESPONSE_INVALID"
REASON_VISION_PARSE_FAILED = "VISION_PARSE_FAILED"
REASON_VISION_SCHEMA_REJECTED = "VISION_SCHEMA_REJECTED"
REASON_E2_REJECTED = "E2_REJECTED"
REASON_D2_UNRESOLVED = "D2_UNRESOLVED"
REASON_R13_PATCH_REJECTED = "R13_PATCH_REJECTED"
REASON_PATCH_NOT_APPLIED = "PATCH_NOT_APPLIED"
REASON_DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"
REASON_EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
REASON_OTHER = "OTHER_EXPLICIT_REASON"
REASON_OK = "OK"

PROVIDER_OK = "OK"
PROVIDER_WORKSPACE_SPEND_LIMIT = "WORKSPACE_SPEND_LIMIT"
PROVIDER_RATE_LIMIT = "RATE_LIMIT"
PROVIDER_REQUEST_LIMIT = "REQUEST_LIMIT"
PROVIDER_TOKEN_LIMIT = "TOKEN_LIMIT"
PROVIDER_VISION_TIMEOUT = "VISION_TIMEOUT"
PROVIDER_NETWORK_ERROR = "NETWORK_ERROR"
PROVIDER_INVALID_REQUEST = "INVALID_REQUEST"
PROVIDER_PROVIDER_ERROR = "PROVIDER_ERROR"
PROVIDER_PARSE_FAILURE = "PARSE_FAILURE"
PROVIDER_SCHEMA_FAILURE = "SCHEMA_FAILURE"
PROVIDER_E2_REJECTED = "E2_REJECTED"
PROVIDER_D2_UNRESOLVED = "D2_UNRESOLVED"
PROVIDER_OTHER = "OTHER"

_HTTP_STATUS_RE = re.compile(
    r"(?:error code|status(?: code)?|http)[:\s]*(\d{3})",
    re.IGNORECASE,
)
_HTTP_BARE_RE = re.compile(r"\b(400|401|403|408|429|500|502|503|529)\b")
_SECRET_EXCERPT_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+)|(ANTHROPIC_API_KEY\s*=\s*\S+)",
    re.IGNORECASE,
)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _patched_beam_ids(handoff: Dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in handoff.get("ledger") or []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        if action.startswith("PATCHED"):
            bid = str(item.get("beam_id") or "")
            if bid:
                ids.add(bid)
    return ids


def extract_http_status(row: Dict[str, Any]) -> Optional[int]:
    raw = row.get("http_status")
    if raw is not None and str(raw) not in ("", "None"):
        try:
            code = int(raw)
            if 100 <= code <= 599:
                return code
        except (TypeError, ValueError):
            pass
    err = str(row.get("api_error") or "")
    match = _HTTP_STATUS_RE.search(err)
    if match:
        return int(match.group(1))
    match = _HTTP_BARE_RE.search(err)
    if match:
        return int(match.group(1))
    return None


def safe_error_excerpt(value: Any, *, limit: int = 240) -> Optional[str]:
    if value is None:
        return None
    text = _SECRET_EXCERPT_RE.sub("[REDACTED]", str(value)).strip()
    if not text:
        return None
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def classify_provider_error(row: Dict[str, Any]) -> str:
    """Normalized W.14 provider/lifecycle category. Does not invent unsupported labels."""
    skip = str(row.get("skip_reason") or "")
    fail = str(row.get("failure_category") or "")
    et = str(row.get("error_type") or "")
    err = str(row.get("api_error") or "").lower()
    timeout = str(row.get("timeout_status") or "")
    parse_status = str(row.get("parse_status") or "")
    status = str(row.get("hybrid_status") or "")
    http = extract_http_status(row)
    visual = bool(row.get("visual_available"))
    called = bool(row.get("called"))

    if skip in ("NO_USABLE_EVIDENCE", "RENDER_MISSING", "EVIDENCE_UNAVAILABLE") or (
        not visual and not called
    ):
        return PROVIDER_OTHER

    if (
        timeout == "VISION_TIMEOUT"
        or skip == "VISION_TIMEOUT"
        or skip == "WALL_CLOCK_BUDGET"
        or et in ("TimeoutError", "TimeoutExpired", "ClaudeTimeoutError")
        or "timeout" in et.lower()
    ):
        return PROVIDER_VISION_TIMEOUT

    if fail == "SCHEMA_FAILED" or parse_status == "SCHEMA_INVALID":
        return PROVIDER_SCHEMA_FAILURE
    if parse_status in ("PARSE_FAILED", "JSON_INVALID", "PARSE_INVALID"):
        return PROVIDER_PARSE_FAILURE
    if fail in ("SEMANTIC_UNUSABLE", "TARGET_NOT_IDENTIFIED"):
        return PROVIDER_E2_REJECTED

    if fail == "API_FAILED" or skip == "API_FAILED" or skip == "LIVE_CALL_EXCEPTION":
        if (
            "usage limit" in err
            or "workspace api usage" in err
            or "spend limit" in err
            or "workspace usage" in err
        ):
            return PROVIDER_WORKSPACE_SPEND_LIMIT
        if "RateLimit" in et or http == 429 or "rate limit" in err or "rate_limit" in err:
            return PROVIDER_RATE_LIMIT
        if "timeout" in err or "timeout" in et.lower() or http == 408:
            return PROVIDER_VISION_TIMEOUT
        if (
            "connection" in et.lower()
            or "network" in err
            or "dns" in err
            or et in ("APIConnectionError", "ConnectTimeout", "ReadTimeout")
        ):
            return PROVIDER_NETWORK_ERROR
        if ("token" in err and "limit" in err) or "max_tokens" in err or "context length" in err:
            return PROVIDER_TOKEN_LIMIT
        if "request limit" in err or "too many requests" in err:
            return PROVIDER_REQUEST_LIMIT
        if "invalid_request" in err or http == 400:
            return PROVIDER_INVALID_REQUEST
        return PROVIDER_PROVIDER_ERROR

    if skip in (
        "LIVE_DISABLED",
        "ANTHROPIC_API_KEY_ABSENT",
        "ANTHROPIC_API_KEY_EMPTY",
        "PER_RUN_REQUEST_LIMIT",
    ) or not called:
        return PROVIDER_OTHER

    if status == "HYBRID_ERROR":
        return PROVIDER_D2_UNRESOLVED if skip != "LIVE_CALL_EXCEPTION" else PROVIDER_PROVIDER_ERROR

    if status == "OBSERVED":
        if row.get("semantic_usable") is False:
            return PROVIDER_E2_REJECTED
        if row.get("hybrid_semantic") is None and row.get("hybrid_interpretation") is None:
            return PROVIDER_D2_UNRESOLVED
        return PROVIDER_OK

    if fail:
        return PROVIDER_OTHER
    return PROVIDER_OTHER


def classify_stop_stage(row: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Return (final_status, reason_code, existing_code).

    existing_code preserves the codebase's native skip_reason / failure_category
    unless a more specific W.14 provider category is known.
    """
    skip = str(row.get("skip_reason") or "")
    fail = str(row.get("failure_category") or "")
    existing = skip or fail or ""
    visual = bool(row.get("visual_available"))
    called = bool(row.get("called"))
    status = str(row.get("hybrid_status") or "")
    parse_status = str(row.get("parse_status") or "")
    error_type = str(row.get("error_type") or "")
    timeout = str(row.get("timeout_status") or "")

    if skip in ("NO_USABLE_EVIDENCE", "RENDER_MISSING", "EVIDENCE_UNAVAILABLE") or (
        not visual and not called
    ):
        return (
            STATUS_EVIDENCE_UNAVAILABLE,
            REASON_EVIDENCE_UNAVAILABLE,
            existing or skip or REASON_EVIDENCE_UNAVAILABLE,
        )

    if (
        timeout == "VISION_TIMEOUT"
        or skip == "VISION_TIMEOUT"
        or skip == "WALL_CLOCK_BUDGET"
        or error_type in ("TimeoutError", "TimeoutExpired", "ClaudeTimeoutError")
    ):
        return STATUS_VISION_FAILED, REASON_VISION_TIMEOUT, existing or REASON_VISION_TIMEOUT

    if fail == "API_FAILED" or skip == "API_FAILED":
        provider = classify_provider_error(row)
        existing_api = provider if provider != PROVIDER_OTHER else (existing or "API_FAILED")
        return STATUS_VISION_FAILED, REASON_VISION_API_ERROR, existing_api

    if fail == "SCHEMA_FAILED" or parse_status == "SCHEMA_INVALID":
        return STATUS_VISION_FAILED, REASON_VISION_SCHEMA_REJECTED, existing or "SCHEMA_FAILED"

    if fail in ("SEMANTIC_UNUSABLE", "TARGET_NOT_IDENTIFIED"):
        return STATUS_VISION_FAILED, REASON_E2_REJECTED, existing or fail

    if skip in (
        "LIVE_DISABLED",
        "ANTHROPIC_API_KEY_ABSENT",
        "ANTHROPIC_API_KEY_EMPTY",
        "PER_RUN_REQUEST_LIMIT",
    ):
        return STATUS_DETERMINISTIC_FALLBACK, REASON_VISION_NOT_ATTEMPTED, existing

    if not called:
        return STATUS_DETERMINISTIC_FALLBACK, skip or REASON_VISION_NOT_ATTEMPTED, existing

    if status == "HYBRID_ERROR":
        if skip == "LIVE_CALL_EXCEPTION":
            return STATUS_VISION_FAILED, REASON_VISION_API_ERROR, existing
        return STATUS_VISION_FAILED, REASON_D2_UNRESOLVED, existing or "HYBRID_ERROR"

    if status == "OBSERVED":
        if row.get("semantic_usable") is False:
            return STATUS_VISION_FAILED, REASON_E2_REJECTED, existing or "E2_REJECTED"
        if row.get("hybrid_semantic") is None and row.get("hybrid_interpretation") is None:
            return STATUS_VISION_FAILED, REASON_D2_UNRESOLVED, existing or "D2_UNRESOLVED"
        return STATUS_HYBRID_RESOLVED, REASON_OK, existing or "OK"

    if fail:
        return STATUS_DETERMINISTIC_FALLBACK, fail, existing
    if skip:
        return STATUS_DETERMINISTIC_FALLBACK, skip, existing
    return STATUS_DETERMINISTIC_FALLBACK, REASON_OTHER, existing or REASON_OTHER


def _stage_flags(row: Dict[str, Any], *, patched: bool) -> Dict[str, Any]:
    called = bool(row.get("called"))
    api_success = row.get("api_success")
    if api_success is None:
        usage = row.get("usage") if isinstance(row.get("usage"), dict) else {}
        tokens = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
        if called and tokens > 0:
            api_success = True
        elif called and str(row.get("failure_category") or "") == "API_FAILED":
            api_success = False
        elif called and str(row.get("hybrid_status") or "") == "OBSERVED":
            api_success = True
        else:
            api_success = False
    parse_ok = bool(api_success) and str(row.get("failure_category") or "") not in (
        "API_FAILED",
        "SCHEMA_FAILED",
    )
    if row.get("parse_status"):
        parse_ok = str(row.get("parse_status")) not in ("API_FAILED", "SCHEMA_INVALID", "")
        if str(row.get("parse_status")) == "OK":
            parse_ok = True
    schema_valid = row.get("schema_valid")
    if schema_valid is None:
        schema_valid = bool(api_success) and str(row.get("failure_category") or "") != "SCHEMA_FAILED"
    e2_accepted = bool(row.get("semantic_usable")) if row.get("semantic_usable") is not None else (
        str(row.get("hybrid_status") or "") == "OBSERVED"
    )
    d2_resolved = str(row.get("hybrid_status") or "") == "OBSERVED" and (
        isinstance(row.get("hybrid_semantic"), dict) or isinstance(row.get("hybrid_interpretation"), dict)
    )
    provider_category = classify_provider_error(row)
    return {
        "deterministic_registry_present": True,
        "evidence_generated": bool(row.get("visual_available")),
        "evidence_provenance": row.get("visual_source") or row.get("context_source"),
        "context_path": row.get("context_path"),
        "detail_path": row.get("detail_path"),
        "claude_attempted": called,
        "claude_api_success": bool(api_success),
        "response_parse_success": bool(parse_ok and api_success),
        "schema_valid": bool(schema_valid and api_success),
        "e2_accepted": bool(e2_accepted),
        "d2_resolved": bool(d2_resolved),
        "r13_patch_eligible": bool(d2_resolved),
        "r13_patch_applied": bool(patched),
        "retry_count": row.get("retry_count"),
        "attempts": row.get("attempts"),
        "timeout_status": row.get("timeout_status"),
        "error_type": row.get("error_type"),
        "api_error": row.get("api_error"),
        "failure_category": row.get("failure_category"),
        "skip_reason": row.get("skip_reason"),
        "hybrid_status": row.get("hybrid_status"),
        "parse_status": row.get("parse_status"),
        "claude_duration_s": row.get("claude_duration_s"),
        "http_status": extract_http_status(row),
        "provider_category": provider_category,
        "api_error_excerpt": safe_error_excerpt(row.get("api_error")),
        "timeout_flag": bool(
            str(row.get("timeout_status") or "") == "VISION_TIMEOUT"
            or provider_category == PROVIDER_VISION_TIMEOUT
        ),
    }


def _api_recovery_checkpoint(beams: List[Dict[str, Any]]) -> Dict[str, Any]:
    successes: List[Dict[str, Any]] = []
    first_failure: Optional[Dict[str, Any]] = None
    attempt_n = 0
    for row in beams:
        if not row.get("claude_attempted"):
            continue
        attempt_n += 1
        if row.get("claude_api_success"):
            successes.append(
                {
                    "success_number": len(successes) + 1,
                    "attempt_number": attempt_n,
                    "beam_id": row.get("beam_id"),
                }
            )
        elif first_failure is None:
            first_failure = {
                "attempt_number": attempt_n,
                "beam_id": row.get("beam_id"),
                "provider_category": row.get("provider_category"),
                "http_status": row.get("http_status"),
                "api_error_excerpt": row.get("api_error_excerpt"),
            }
    n_success = len(successes)
    beyond_26 = n_success > 26
    all_attempted_succeeded = attempt_n > 0 and n_success == attempt_n
    if all_attempted_succeeded or beyond_26:
        cliff = "PREVIOUS_26_CALL_CLIFF_NOT_REPRODUCED"
    elif n_success == 26 and first_failure is not None:
        cliff = "CLIFF_REPRODUCED_AT_26"
    elif 0 < n_success < 26 and first_failure is not None:
        cliff = "FAILURE_BEFORE_26"
    elif n_success == 0 and first_failure is not None:
        cliff = "NO_API_SUCCESS"
    else:
        cliff = "INCONCLUSIVE"
    def _nth(n: int) -> Optional[Dict[str, Any]]:
        return successes[n - 1] if len(successes) >= n else None

    return {
        "attempted": attempt_n,
        "api_success": n_success,
        "api_failure": max(0, attempt_n - n_success),
        "success_continued_beyond_26": beyond_26,
        "cliff_classification": cliff,
        "first_api_success": _nth(1),
        "success_26": _nth(26),
        "success_27": _nth(27),
        "final_successful_api_call_number": n_success if n_success else None,
        "first_api_failure": first_failure,
    }


def _cost_summary(shadow: Dict[str, Any], totals: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from PhaseW5_production_hybrid_shadow.cost import estimate_cost_usd
        from PhaseW5_production_hybrid_shadow.config import COST_BASIS
    except Exception:
        estimate_cost_usd = None  # type: ignore[assignment]
        COST_BASIS = "ESTIMATED"
    try:
        inp = int(shadow.get("input_tokens") or 0)
        out = int(shadow.get("output_tokens") or 0)
    except (TypeError, ValueError):
        inp, out = 0, 0
    if estimate_cost_usd is not None:
        est = estimate_cost_usd(input_tokens=inp, output_tokens=out)
        usd = float(est.get("estimated_cost_usd") or 0.0)
        basis = str(est.get("cost_basis") or COST_BASIS)
        rates = {
            "input_usd_per_mtok": est.get("input_usd_per_mtok"),
            "output_usd_per_mtok": est.get("output_usd_per_mtok"),
        }
    else:
        usd = 0.0
        basis = "ESTIMATED"
        rates = {}
    attempted = int(totals.get("claude_attempted") or 0)
    success = int(totals.get("claude_api_success") or 0)
    drawing_beams = int(totals.get("total_beams") or 0)
    per_beam_tokens: List[int] = []
    for row in shadow.get("beams") or []:
        if not isinstance(row, dict):
            continue
        usage = row.get("usage") if isinstance(row.get("usage"), dict) else {}
        try:
            tok = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
        except (TypeError, ValueError):
            tok = 0
        if tok > 0:
            per_beam_tokens.append(tok)
    token_mean = round(sum(per_beam_tokens) / len(per_beam_tokens), 1) if per_beam_tokens else 0
    token_max = max(per_beam_tokens) if per_beam_tokens else 0
    token_min = min(per_beam_tokens) if per_beam_tokens else 0
    unreliable = bool(per_beam_tokens) and token_mean > 0 and (token_max / token_mean) >= 2.0
    projection_143 = None
    if attempted > 0:
        projection_143 = round(usd * (143.0 / float(attempted)), 6)
    return {
        "cost_label": "ESTIMATED",
        "cost_basis": basis,
        "not_billed_exact": True,
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out,
        "estimated_cost_usd": round(usd, 6),
        "cost_per_attempted_beam_usd": round(usd / attempted, 6) if attempted else None,
        "cost_per_successful_vision_beam_usd": round(usd / success, 6) if success else None,
        "cost_per_total_drawing_usd": round(usd, 6),
        "drawing_beam_count": drawing_beams,
        "attempted_beam_count": attempted,
        "successful_vision_beam_count": success,
        "per_success_token_min": token_min,
        "per_success_token_mean": token_mean,
        "per_success_token_max": token_max,
        "projection_143_beam_usd": projection_143,
        "projection_label": "PROJECTION ONLY",
        "projection_unreliable": unreliable,
        **rates,
    }


def build_resolution_trace(
    *,
    run_id: str,
    beam_ids: Iterable[str],
    shadow_result: Dict[str, Any],
    handoff: Optional[Dict[str, Any]] = None,
    coverage: Optional[Dict[str, Any]] = None,
    visual_prep: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    handoff = handoff if isinstance(handoff, dict) else {}
    coverage = coverage if isinstance(coverage, dict) else {}
    visual_prep = visual_prep if isinstance(visual_prep, dict) else {}
    patched = _patched_beam_ids(handoff)
    rows = [b for b in (shadow_result.get("beams") or []) if isinstance(b, dict)]
    by_id = {str(r.get("beam_id")): r for r in rows if r.get("beam_id")}
    eligible = [str(b) for b in beam_ids if str(b)]
    beams: List[Dict[str, Any]] = []
    reason_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}

    totals = {
        "total_beams": len(eligible),
        "hybrid_eligible": len(eligible),
        "evidence_generated": 0,
        "evidence_unavailable": 0,
        "claude_attempted": 0,
        "claude_api_success": 0,
        "claude_api_failure": 0,
        "claude_timeout": 0,
        "response_parse_success": 0,
        "response_parse_failure": 0,
        "schema_valid": 0,
        "schema_rejected": 0,
        "e2_accepted": 0,
        "e2_rejected": 0,
        "d2_resolved": 0,
        "d2_unresolved": 0,
        "r13_patch_eligible": 0,
        "r13_patch_applied": 0,
        "r13_patch_rejected": 0,
        "deterministic_fallback": 0,
        "unexplained": 0,
    }

    for bid in eligible:
        row = by_id.get(bid) or {
            "beam_id": bid,
            "visual_available": False,
            "called": False,
            "skip_reason": "MISSING_SHADOW_ROW",
        }
        final_status, reason_code, existing = classify_stop_stage(row)
        if final_status == STATUS_HYBRID_RESOLVED and bid not in patched and handoff.get("applied"):
            patch_note = REASON_PATCH_NOT_APPLIED
        elif final_status == STATUS_HYBRID_RESOLVED:
            patch_note = None
        else:
            patch_note = None
        flags = _stage_flags(row, patched=bid in patched)
        if flags["evidence_generated"]:
            totals["evidence_generated"] += 1
        else:
            totals["evidence_unavailable"] += 1
        if flags["claude_attempted"]:
            totals["claude_attempted"] += 1
        if flags["claude_api_success"]:
            totals["claude_api_success"] += 1
        elif flags["claude_attempted"]:
            totals["claude_api_failure"] += 1
        if reason_code == REASON_VISION_TIMEOUT:
            totals["claude_timeout"] += 1
        if flags["response_parse_success"]:
            totals["response_parse_success"] += 1
        elif flags["claude_api_success"]:
            totals["response_parse_failure"] += 1
        if flags["schema_valid"]:
            totals["schema_valid"] += 1
        elif flags["claude_api_success"]:
            totals["schema_rejected"] += 1
        if flags["e2_accepted"]:
            totals["e2_accepted"] += 1
        elif flags["claude_api_success"]:
            totals["e2_rejected"] += 1
        if flags["d2_resolved"]:
            totals["d2_resolved"] += 1
        else:
            totals["d2_unresolved"] += 1
        if flags["r13_patch_eligible"]:
            totals["r13_patch_eligible"] += 1
        if flags["r13_patch_applied"]:
            totals["r13_patch_applied"] += 1
        elif flags["r13_patch_eligible"]:
            totals["r13_patch_rejected"] += 1
        if final_status != STATUS_HYBRID_RESOLVED:
            totals["deterministic_fallback"] += 1

        reason_counts[reason_code] = reason_counts.get(reason_code, 0) + 1
        status_counts[final_status] = status_counts.get(final_status, 0) + 1
        beams.append(
            {
                "beam_id": bid,
                "final_status": final_status,
                "reason_code": reason_code,
                "existing_code": existing or None,
                "patch_note": patch_note,
                **flags,
            }
        )

    unexplained = [
        b["beam_id"]
        for b in beams
        if b["final_status"] != STATUS_HYBRID_RESOLVED and not b.get("reason_code")
    ]
    totals["unexplained"] = len(unexplained)
    totals["parse_valid"] = totals["response_parse_success"]
    totals["parse_invalid"] = totals["response_parse_failure"]
    provider_counts: Dict[str, int] = {}
    for b in beams:
        cat = str(b.get("provider_category") or PROVIDER_OTHER)
        provider_counts[cat] = provider_counts.get(cat, 0) + 1
    identity_ok = totals["total_beams"] == len(beams) and len(unexplained) == 0
    fallback_identity = (
        totals["hybrid_eligible"]
        == totals["d2_resolved"] + totals["deterministic_fallback"]
    )
    return {
        "run_id": run_id,
        "artifact": TRACE_FILENAME,
        "lifecycle_counts": totals,
        "reason_counts": reason_counts,
        "status_counts": status_counts,
        "provider_category_counts": provider_counts,
        "api_recovery": _api_recovery_checkpoint(beams),
        "cost_summary": _cost_summary(shadow_result, totals),
        "unexplained": unexplained,
        "coverage_reconcile": {
            "claude_attempted_coverage": coverage.get("claude_attempted"),
            "claude_success_coverage": coverage.get("claude_success"),
            "unresolved_coverage": coverage.get("unresolved"),
        },
        "visual_prep": {
            "evidence_packages_generated": visual_prep.get("evidence_packages_generated"),
            "context_selected": visual_prep.get("context_selected"),
            "detail_selected": visual_prep.get("detail_selected"),
        },
        "handoff": {
            "applied": handoff.get("applied"),
            "reason": handoff.get("reason"),
            "beams_patched": handoff.get("beams_patched"),
            "fields_patched": handoff.get("fields_patched"),
        },
        "identity_ok": identity_ok,
        "fallback_identity_ok": fallback_identity,
        "beams": beams,
    }


def reconstruct_from_staging(staging: Path, *, run_id: Optional[str] = None) -> Dict[str, Any]:
    staging = Path(staging)
    shadow = _load_json(staging / "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json") or {}
    coverage = _load_json(staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_coverage.json") or {}
    handoff = _load_json(staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_handoff_ledger.json") or {}
    obs = _load_json(staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json") or {}
    rid = run_id or str(shadow.get("run_id") or staging.name)
    beam_ids = [str(b.get("beam_id")) for b in (shadow.get("beams") or []) if isinstance(b, dict) and b.get("beam_id")]
    visual_prep = obs.get("visual_prep") if isinstance(obs.get("visual_prep"), dict) else {}
    return build_resolution_trace(
        run_id=rid,
        beam_ids=beam_ids,
        shadow_result=shadow,
        handoff=handoff,
        coverage=coverage,
        visual_prep=visual_prep,
    )


__all__ = [
    "TRACE_FILENAME",
    "build_resolution_trace",
    "classify_provider_error",
    "classify_stop_stage",
    "extract_http_status",
    "reconstruct_from_staging",
    "safe_error_excerpt",
]
