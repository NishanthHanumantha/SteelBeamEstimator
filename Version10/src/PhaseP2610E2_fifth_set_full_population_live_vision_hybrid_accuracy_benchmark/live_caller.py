"""Live Claude Vision for E.2. Reuses C.5 schema and P253 client. Secrets never persisted."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PhaseP2610C5_stratified_vision_semantic_benchmark.claude_call import call_selected_beam
from PhaseP2610C5_stratified_vision_semantic_benchmark.vision_contract import unusable
from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_normalizer import extract_vision_payload

from .config import MAX_API_ATTEMPTS, MAX_SCHEMA_PARSE_ATTEMPTS

_SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+)|(ANTHROPIC_API_KEY\s*=\s*\S+)|(api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def sanitize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items() if "api_key" not in str(k).lower()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return _SECRET_RE.sub("[REDACTED]", str(value))


def classify_failure(*, audit: Dict[str, Any], parsed: Dict[str, Any]) -> str:
    if not audit.get("success"):
        return "API_FAILED"
    status = str(parsed.get("call_status") or "")
    if status == "SCHEMA_INVALID" or (parsed.get("usable") is False and "json" in str(parsed.get("unusable_reason") or "").lower()):
        return "SCHEMA_FAILED"
    if parsed.get("usable") is False:
        if "target" in str(parsed.get("unusable_reason") or "").lower():
            return "TARGET_NOT_IDENTIFIED"
        return "SEMANTIC_UNUSABLE"
    if not parsed.get("target_identified") and not (parsed.get("groups") or parsed.get("stirrups")):
        return "SEMANTIC_UNUSABLE"
    return "OK"


def call_live_beam(
    *,
    version10_root: Path,
    beam_id: str,
    render_path: Path,
    context_source: str,
    detail_source: str,
    client_override: Optional[Callable] = None,
    context_path: Optional[Path] = None,
    detail_path: Optional[Path] = None,
    timeout_s: Optional[float] = None,
    max_attempts: Optional[int] = None,
    max_api_attempts: Optional[int] = None,
) -> Dict[str, Any]:
    attempts = 0
    last: Dict[str, Any] = {}
    schema_attempts = 0
    ctx = Path(context_path or render_path)
    det = Path(detail_path or render_path)
    api_limit = int(max_api_attempts) if max_api_attempts is not None else MAX_API_ATTEMPTS
    api_limit = max(1, api_limit)
    while attempts < api_limit:
        attempts += 1
        last = call_selected_beam(
            version10_root=version10_root,
            beam_id=beam_id,
            context_path=ctx,
            detail_path=det,
            context_source=context_source,
            detail_source=detail_source,
            client_override=client_override,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
        )
        audit = last.get("audit") or {}
        parsed = last.get("parsed") or unusable("empty")
        fail = classify_failure(audit=audit, parsed=parsed)
        error_type = str(audit.get("error_type") or "")
        timed_out = fail == "API_FAILED" and (
            "Timeout" in error_type or "timeout" in str(audit.get("error") or "").lower()
        )
        if fail == "API_FAILED" and attempts < api_limit and not timed_out:
            continue
        if fail == "SCHEMA_FAILED":
            schema_attempts += 1
            if schema_attempts < MAX_SCHEMA_PARSE_ATTEMPTS:
                continue
        extracted = extract_vision_payload(parsed if parsed.get("usable") else {"usable": False, "unusable_reason": parsed.get("unusable_reason"), "groups": [], "stirrups": []})
        semantic_usable = bool(
            extracted.get("usable")
            and (extracted.get("groups") or extracted.get("stirrups") or extracted.get("target_identified"))
        )
        if not semantic_usable and fail == "OK":
            fail = "SEMANTIC_UNUSABLE"
        return {
            "beam_id": beam_id,
            "called": True,
            "attempts": attempts,
            "retry_count": max(0, attempts - 1),
            "audit": sanitize(audit),
            "parsed": parsed,
            "extracted": extracted,
            "raw_text": sanitize(last.get("raw_text")),
            "failure_category": fail,
            "semantic_usable": semantic_usable,
            "schema_valid": fail not in ("SCHEMA_FAILED", "API_FAILED") and bool(parsed.get("usable") or parsed.get("call_status") == "OK"),
            "api_success": bool(audit.get("success")),
            "model": (audit or {}).get("model"),
            "usage": sanitize((audit or {}).get("usage")),
        }
    return {
        "beam_id": beam_id,
        "called": True,
        "attempts": attempts,
        "retry_count": max(0, attempts - 1),
        "audit": sanitize((last or {}).get("audit")),
        "parsed": unusable("api_exhausted"),
        "extracted": extract_vision_payload({"usable": False, "unusable_reason": "API_FAILED", "groups": [], "stirrups": []}),
        "raw_text": None,
        "failure_category": "API_FAILED",
        "semantic_usable": False,
        "schema_valid": False,
        "api_success": False,
        "model": None,
        "usage": None,
    }


__all__ = ["call_live_beam", "classify_failure", "sanitize"]
