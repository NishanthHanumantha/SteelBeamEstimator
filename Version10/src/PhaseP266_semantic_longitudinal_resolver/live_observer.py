"""Optional live shadow observer. Isolated cache. Disabled unless LIVE_API opt-in."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import call_claude_vision
from PhaseP26_vision_candidate_recovery.cache import cache_key, load_cache, save_cache

from .config import CLAUDE_MODEL, MODE_LIVE, SCHEMA_VERSION, TEMPERATURE
from .semantic_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt, prompt_fingerprint
from .semantic_schema import parse_semantic_response


def _encode_crop(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    raw = p.read_bytes()
    return {
        "media_type": "image/png",
        "data_base64": base64.standard_b64encode(raw).decode("ascii"),
        "role": "beam_crop",
    }


def observe_semantic(
    *,
    version10_root: Path,
    context: Dict[str, Any],
    cache_root: Path,
    crop_path: Optional[str],
    mode: str,
    drawing_hash: str = "",
    region_hash: str = "",
) -> Dict[str, Any]:
    user_prompt = build_user_prompt(context=context)
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    leaks = assert_no_truth_leak(context)
    leaks += assert_no_truth_leak({"user_prompt": user_prompt, "system": SYSTEM_PROMPT})
    key = cache_key(
        drawing_hash=drawing_hash or str(context.get("region_id") or ""),
        region_hash=region_hash or str(context.get("beam_id") or ""),
        prompt_hash=p_fp,
        vision_model=CLAUDE_MODEL,
        schema_version=SCHEMA_VERSION,
    )
    base = {
        "cache_key": key,
        "prompt_fingerprint": p_fp,
        "vision_model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "schema_version": SCHEMA_VERSION,
        "truth_leak_keys": leaks,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "production_write": False,
        "source": "P266_ISOLATED_CACHE",
    }
    if leaks:
        return {**base, "api_ok": False, "cache_hit": False, "error": "TRUTH_LEAK_BLOCKED", "payload": None}
    cached = load_cache(cache_root, key)
    if cached is not None:
        payload, report = parse_semantic_response(cached.get("raw_response"))
        return {
            **base,
            "api_ok": bool(report.get("ok")),
            "cache_hit": True,
            "error": report.get("error"),
            "payload": payload,
            "live_call": False,
        }
    if mode != MODE_LIVE:
        return {
            **base,
            "api_ok": False,
            "cache_hit": False,
            "error": "REPLAY_NO_ISOLATED_CACHE",
            "payload": None,
            "live_call": False,
        }
    image = _encode_crop(crop_path)
    if image is None:
        return {
            **base,
            "api_ok": False,
            "cache_hit": False,
            "error": "missing_crop",
            "payload": None,
            "live_call": False,
        }
    result = call_claude_vision(
        version10_root=version10_root,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images=[image],
    )
    save_cache(
        cache_root,
        key,
        {
            "request_metadata": {"region_id": context.get("region_id"), "beam_id": context.get("beam_id")},
            "raw_response": result.get("raw_text"),
            "normalized_response": None,
            "usage": result.get("usage") or {},
            "error": result.get("error"),
        },
    )
    payload, report = parse_semantic_response(result.get("raw_text"))
    if payload:
        payload["source"] = "P266_LIVE_SHADOW"
    return {
        **base,
        "api_ok": bool(result.get("success")) and bool(report.get("ok")),
        "cache_hit": False,
        "error": result.get("error") or report.get("error"),
        "payload": payload,
        "live_call": True,
        "source": "P266_LIVE_SHADOW",
        "usage": result.get("usage") or {},
    }


__all__ = ["observe_semantic"]
