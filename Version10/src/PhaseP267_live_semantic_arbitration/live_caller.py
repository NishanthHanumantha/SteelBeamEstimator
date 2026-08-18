"""Live Claude Vision caller. Cache is never read. Secrets are never persisted."""
from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import call_claude_vision

from .config import (
    CACHE_BYPASS,
    CLAUDE_MODEL,
    PASS_PRIMARY,
    PASS_REPEAT,
    SCHEMA_VERSION,
    TEMPERATURE,
)
from .live_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt, prompt_fingerprint
from .live_schema import parse_live_response

_SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+)|(ANTHROPIC_API_KEY\s*=\s*\S+)|(api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def sanitize_text(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: sanitize_text(v) for k, v in value.items() if "api_key" not in str(k).lower()}
    if isinstance(value, list):
        return [sanitize_text(v) for v in value]
    text = str(value)
    return _SECRET_RE.sub("[REDACTED]", text)


def classify_call_error(*, api_error_type: Optional[str], parse_class: Optional[str], error: Optional[str]) -> str:
    if parse_class:
        return parse_class
    et = str(api_error_type or "")
    err = str(error or "").lower()
    if "Authentication" in et or "auth" in err:
        return "authentication_failure"
    if "RateLimit" in et or "rate" in err:
        return "rate_limit"
    if "Timeout" in et or "timeout" in err:
        return "timeout"
    if error:
        return "api_failure"
    return "unknown_failure"


def encode_crop(path: Path) -> Dict[str, Any]:
    raw = Path(path).read_bytes()
    return {
        "media_type": "image/png",
        "data_base64": base64.standard_b64encode(raw).decode("ascii"),
        "role": "beam_crop",
    }


def require_api_key(version10_root: Path) -> None:
    from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import get_claude_client

    get_claude_client(Path(version10_root))


def live_observe(
    *,
    version10_root: Path,
    context: Dict[str, Any],
    crop: Path,
    pass_id: str,
    bypass_cache: bool = CACHE_BYPASS,
) -> Dict[str, Any]:
    if pass_id not in (PASS_PRIMARY, PASS_REPEAT):
        raise ValueError(f"unsupported pass_id {pass_id}")
    if bypass_cache is not True:
        raise RuntimeError("P2.6.7 must bypass cache for both primary and repeat live calls")
    user_prompt = build_user_prompt(context=context)
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    leaks = assert_no_truth_leak(context)
    leaks += assert_no_truth_leak({"user_prompt": user_prompt, "system": SYSTEM_PROMPT})
    base = {
        "pass_id": pass_id,
        "prompt_fingerprint": p_fp,
        "vision_model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "schema_version": SCHEMA_VERSION,
        "truth_leak_keys": leaks,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "production_write": False,
        "cache_bypassed": True,
        "cache_hit": False,
        "source": f"P267_{pass_id}",
    }
    if leaks:
        return {
            **base,
            "ok": False,
            "live_call": False,
            "error": "TRUTH_LEAK_BLOCKED",
            "error_class": "truth_leak",
            "payload": None,
            "raw_response": None,
            "retry_count": 0,
        }
    if not crop.exists():
        return {
            **base,
            "ok": False,
            "live_call": False,
            "error": f"missing_crop:{crop}",
            "error_class": "missing_crop",
            "payload": None,
            "raw_response": None,
            "retry_count": 0,
        }
    image = encode_crop(crop)
    result = call_claude_vision(
        version10_root=version10_root,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images=[image],
    )
    if not result.get("success"):
        return {
            **base,
            "ok": False,
            "live_call": True,
            "error": sanitize_text(result.get("error")),
            "error_class": classify_call_error(
                api_error_type=result.get("error_type"),
                parse_class=None,
                error=result.get("error"),
            ),
            "error_type": result.get("error_type"),
            "payload": None,
            "raw_response": sanitize_text(result.get("raw_text")),
            "retry_count": int(result.get("retry_count") or 0),
            "latency_s": result.get("latency_s"),
            "usage": result.get("usage") or {},
            "model": result.get("model") or CLAUDE_MODEL,
        }
    payload, report = parse_live_response(result.get("raw_text"))
    ok = bool(report.get("ok"))
    if payload:
        payload["source"] = f"P267_{pass_id}"
    return {
        **base,
        "ok": ok,
        "live_call": True,
        "error": sanitize_text(report.get("error")),
        "error_class": None if ok else (report.get("error_class") or "schema_failure"),
        "error_type": result.get("error_type"),
        "payload": payload,
        "raw_response": sanitize_text(result.get("raw_text")),
        "retry_count": int(result.get("retry_count") or 0),
        "latency_s": result.get("latency_s"),
        "usage": result.get("usage") or {},
        "model": result.get("model") or CLAUDE_MODEL,
    }


__all__ = [
    "classify_call_error",
    "encode_crop",
    "live_observe",
    "require_api_key",
    "sanitize_text",
]
