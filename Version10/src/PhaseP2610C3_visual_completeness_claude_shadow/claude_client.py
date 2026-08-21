"""Controlled Claude Vision adapter. Reuses P2.5.3 client. No API keys in artefacts."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import call_claude_vision

from .vision_contract import parse_and_validate, unusable
from .vision_prompt import SYSTEM_PROMPT, build_user_prompt, prompt_fingerprint


def encode_png(path: Path) -> Dict[str, Any]:
    raw = Path(path).read_bytes()
    return {
        "media_type": "image/png",
        "data_base64": base64.standard_b64encode(raw).decode("ascii"),
        "role": Path(path).name,
        "sha256": None,
        "path": str(path),
    }


def call_beam_vision(
    *,
    version10_root: Path,
    beam_id: str,
    context_path: Path,
    detail_path: Path,
    context_source: str,
    detail_source: str,
    client_override=None,
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
        )
    audit = {
        "success": bool(call.get("success")),
        "model": call.get("model"),
        "latency_s": call.get("latency_s"),
        "retry_count": call.get("retry_count"),
        "usage": call.get("usage"),
        "estimated_input_tokens": call.get("estimated_input_tokens"),
        "estimated_output_tokens": call.get("estimated_output_tokens"),
        "error": call.get("error"),
        "error_type": call.get("error_type"),
        "temperature": call.get("temperature"),
        "prompt_fingerprint": p_fp,
        "n_images": 2,
    }
    if not call.get("success"):
        parsed = unusable(f"api_error:{call.get('error_type') or call.get('error') or 'unknown'}")
        return {"audit": audit, "parsed": parsed, "raw_text": None}
    parsed = parse_and_validate(call.get("raw_text"), requested_beam_id=beam_id)
    return {"audit": audit, "parsed": parsed, "raw_text": call.get("raw_text")}


__all__ = ["call_beam_vision", "encode_png"]
