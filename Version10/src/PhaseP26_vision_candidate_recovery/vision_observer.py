"""P2.6 Claude Vision observer. Reuses P2.5.3 client. Cache-first. No GT."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import (
    call_claude_vision,
)

from .cache import cache_key, load_cache, save_cache
from .config import CLAUDE_MODEL, MODE_CACHE_ONLY, MODE_LIVE_API, SCHEMA_VERSION, TEMPERATURE
from .response_parser import parse_vision_response
from .vision_prompt import (
    SYSTEM_PROMPT,
    assert_no_truth_leak,
    build_user_prompt,
    prompt_fingerprint,
)


def observe_region(
    *,
    version10_root: Path,
    region: Dict[str, Any],
    cache_root: Path,
    mode: str = MODE_LIVE_API,
) -> Dict[str, Any]:
    beam_id = region["beam_id"]
    region_id = region["region_id"]
    metadata = region["metadata"]
    user_prompt = build_user_prompt(region_id=region_id, beam_id=beam_id, metadata=metadata)
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    leaks = list(region.get("truth_leak_keys") or [])
    leaks += assert_no_truth_leak(metadata)
    leaks += assert_no_truth_leak({"user_prompt": user_prompt, "system": SYSTEM_PROMPT})
    key = cache_key(
        drawing_hash=region.get("drawing_hash") or "",
        region_hash=region.get("region_hash") or "",
        prompt_hash=p_fp,
        vision_model=CLAUDE_MODEL,
        schema_version=SCHEMA_VERSION,
    )
    base = {
        "region_id": region_id,
        "beam_id": beam_id,
        "cache_key": key,
        "prompt_fingerprint": p_fp,
        "vision_model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "schema_version": SCHEMA_VERSION,
        "truth_leak_keys": leaks,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "production_write": False,
        "decision": "SHADOW_CANDIDATE",
    }
    if leaks:
        return {
            **base,
            "api_ok": False,
            "cache_hit": False,
            "error": "TRUTH_LEAK_BLOCKED",
            "candidates": [],
            "usage": {},
        }
    if not region.get("images"):
        return {
            **base,
            "api_ok": False,
            "cache_hit": False,
            "error": "missing_evidence_images",
            "candidates": [],
            "usage": {},
        }

    cached = load_cache(cache_root, key)
    if cached is not None:
        cands, parse_report = parse_vision_response(
            cached.get("raw_response"), beam_id=beam_id, region_id=region_id
        )
        for c in cands:
            c["raw_vision_response_reference"] = str(cache_root / f"{key}.json")
        return {
            **base,
            "api_ok": cached.get("error") is None,
            "cache_hit": True,
            "live_call": False,
            "error": cached.get("error"),
            "candidates": cands,
            "parse_report": parse_report,
            "usage": cached.get("usage") or {},
            "raw_response": cached.get("raw_response"),
        }

    if mode == MODE_CACHE_ONLY:
        return {
            **base,
            "api_ok": False,
            "cache_hit": False,
            "live_call": False,
            "error": "CACHE_MISS_CACHE_ONLY",
            "candidates": [],
            "usage": {},
        }

    call = call_claude_vision(
        version10_root=version10_root,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images=region["images"],
    )
    raw = call.get("raw_text")
    cands: List[Dict[str, Any]] = []
    parse_report: Dict[str, Any] = {"ok": False, "error": call.get("error")}
    if call.get("success") and raw:
        cands, parse_report = parse_vision_response(raw, beam_id=beam_id, region_id=region_id)
    usage = call.get("usage") or {}
    save_cache(
        cache_root,
        key,
        {
            "request_metadata": {
                "region_id": region_id,
                "beam_id": beam_id,
                "prompt_fingerprint": p_fp,
                "image_hash": region.get("image_hash"),
                "model": CLAUDE_MODEL,
                "temperature": TEMPERATURE,
                "schema_version": SCHEMA_VERSION,
            },
            "raw_response": raw,
            "normalized_response": {"candidates": cands, "parse_report": parse_report},
            "usage": usage,
            "error": None if call.get("success") else call.get("error"),
        },
    )
    for c in cands:
        c["raw_vision_response_reference"] = str(cache_root / f"{key}.json")
    return {
        **base,
        "api_ok": bool(call.get("success")),
        "cache_hit": False,
        "live_call": True,
        "error": call.get("error"),
        "candidates": cands,
        "parse_report": parse_report,
        "usage": usage,
        "raw_response": raw,
        "claude_call": {
            "success": call.get("success"),
            "error": call.get("error"),
            "latency_s": call.get("latency_s"),
            "model": call.get("model") or CLAUDE_MODEL,
            "temperature": call.get("temperature") if call.get("temperature") is not None else TEMPERATURE,
        },
    }


__all__ = ["observe_region"]
