"""Re-parse already collected live raw_responses. Does not call the API.

This is not P2.6.1 / P2.6.6 replay. It only re-validates stored Claude text
after schema-tolerance changes. Credit-exhausted calls with no raw text stay failed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .config import PASS_PRIMARY, PASS_REPEAT
from .live_schema import parse_live_response


def _usable_raw(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("none", "null"):
        return None
    return text


def raw_path(raw_root: Path, *, set_key: str, beam_id: str, pass_id: str) -> Path:
    return Path(raw_root) / f"{pass_id}__{set_key}__{beam_id}.json"


def load_stored_raw(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "live_call": False,
            "error": f"missing_raw:{path.name}",
            "error_class": "missing_raw",
            "payload": None,
            "raw_response": None,
            "cache_hit": False,
            "schema_reparsed": False,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def reparse_stored_observation(stored: Dict[str, Any], *, pass_id: str) -> Dict[str, Any]:
    """Rebuild a live observation from a stored raw file. Never invents a decision."""
    raw_text = _usable_raw(stored.get("raw_response"))
    original_error_class = str(stored.get("error_class") or "")
    payload, report = parse_live_response(raw_text)
    live_call = bool(raw_text) or original_error_class in {
        "schema_failure",
        "api_failure",
        "rate_limit",
        "timeout",
        "authentication_failure",
        "malformed_json",
        "empty_response",
    }
    out = {
        "pass_id": stored.get("pass_id") or pass_id,
        "ok": False,
        "live_call": live_call,
        "error": stored.get("error"),
        "error_class": stored.get("error_class"),
        "payload": None,
        "raw_response": stored.get("raw_response"),
        "retry_count": stored.get("retry_count"),
        "latency_s": stored.get("latency_s"),
        "usage": stored.get("usage") or {},
        "cache_hit": False,
        "cache_bypassed": True,
        "source": stored.get("source") or f"P267_{pass_id}",
        "schema_reparsed": False,
        "original_error_class": original_error_class or None,
    }
    if payload and report.get("ok"):
        out["ok"] = True
        out["payload"] = payload
        out["error"] = None
        out["error_class"] = None
        out["schema_reparsed"] = original_error_class == "schema_failure"
        return out
    if raw_text:
        out["error"] = report.get("error") or stored.get("error")
        out["error_class"] = report.get("error_class") or stored.get("error_class") or "schema_failure"
        return out
    out["ok"] = False
    out["payload"] = None
    out["error"] = stored.get("error") or report.get("error") or "no_raw_response"
    out["error_class"] = stored.get("error_class") or report.get("error_class") or "api_failure"
    return out


def load_and_reparse(
    raw_root: Path, *, set_key: str, beam_id: str, pass_id: str
) -> Dict[str, Any]:
    if pass_id not in (PASS_PRIMARY, PASS_REPEAT):
        raise ValueError(f"unsupported pass_id {pass_id}")
    stored = load_stored_raw(raw_path(raw_root, set_key=set_key, beam_id=beam_id, pass_id=pass_id))
    return reparse_stored_observation(stored, pass_id=pass_id)


__all__ = [
    "load_and_reparse",
    "load_stored_raw",
    "raw_path",
    "reparse_stored_observation",
]
