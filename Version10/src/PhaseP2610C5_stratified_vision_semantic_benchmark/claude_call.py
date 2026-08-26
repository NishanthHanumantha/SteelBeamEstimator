"""C.5 Claude Vision calls. Reuses P253 client and C.3 PNG encoding. Max 10 beams."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import (
    call_claude_vision,
    get_claude_client,
)
from PhaseP2610C3_visual_completeness_claude_shadow.claude_client import encode_png

from .vision_contract import parse_and_validate, unusable
from .vision_prompt import SYSTEM_PROMPT, build_user_prompt, prompt_fingerprint


def smoke_api(version10_root: Path) -> Dict[str, Any]:
    try:
        client, cfg = get_claude_client(version10_root)
        text = client.generate_response(
            prompt="Reply with the single token OK and nothing else.",
            system_prompt="You are a connectivity check. Return only OK.",
        )
        ok = "OK" in str(text or "").upper()
        return {
            "ok": ok,
            "model": getattr(cfg, "MODEL_NAME", None),
            "text_present": bool(text),
            "error": None if ok else "unexpected_smoke_text",
        }
    except Exception as exc:
        return {"ok": False, "model": None, "text_present": False, "error": type(exc).__name__}


def call_selected_beam(
    *,
    version10_root: Path,
    beam_id: str,
    context_path: Path,
    detail_path: Path,
    context_source: str,
    detail_source: str,
    client_override=None,
    timeout_s=None,
    max_attempts=None,
) -> Dict[str, Any]:
    user_prompt = build_user_prompt(
        beam_id=beam_id,
        context_source=context_source,
        detail_source=detail_source,
    )
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    images = [encode_png(context_path), encode_png(detail_path)]
    if client_override is not None:
        call = client_override(
            version10_root=version10_root,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            images=images,
        )
    else:
        call = call_claude_vision(
            version10_root=version10_root,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            images=images,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
        )
    audit = {
        "success": bool(call.get("success")),
        "model": call.get("model"),
        "latency_s": call.get("latency_s"),
        "retry_count": call.get("retry_count"),
        "usage": call.get("usage"),
        "error": call.get("error"),
        "error_type": call.get("error_type"),
        "temperature": call.get("temperature"),
        "prompt_fingerprint": p_fp,
        "n_images": 2,
    }
    if not call.get("success"):
        parsed = unusable(f"api_error:{call.get('error_type') or call.get('error') or 'unknown'}", call_status="API_FAILED")
        return {"audit": audit, "parsed": parsed, "raw_text": None, "called": True}
    parsed = parse_and_validate(call.get("raw_text"), requested_beam_id=beam_id)
    return {"audit": audit, "parsed": parsed, "raw_text": call.get("raw_text"), "called": True}


__all__ = ["call_selected_beam", "smoke_api"]
