"""LIVE Claude Vision for unseen crops using the frozen P2.5.4 prompt/schema."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import (
    call_claude_vision,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.semantic_schema import (
    extract_json_object,
    normalize_parsed,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.validator import (
    validate_interpretation,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.vision_prompt import (
    SYSTEM_PROMPT,
    assert_no_truth_leak,
    build_user_prompt,
    prompt_fingerprint,
)

from .config import CLAUDE_MODEL, PROMPT_VERSION, SCHEMA_VERSION, TEMPERATURE
from .evidence_package import build_unseen_evidence_package


def observe_live(*, candidate: Dict[str, Any], version10_root: Path) -> Dict[str, Any]:
    cid = candidate["candidate_id"]
    evidence = build_unseen_evidence_package(candidate)
    user_prompt = build_user_prompt(evidence["metadata"])
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    leaks = assert_no_truth_leak(evidence["metadata"])
    leaks += assert_no_truth_leak({"user_prompt": user_prompt, "system": SYSTEM_PROMPT})
    leaks += assert_no_truth_leak({"candidate_keys": list(candidate.keys())})
    # candidate_keys walk does not include nested GT if stored separately;
    # still reject if the caller accidentally attached GT onto the candidate.
    if "ground_truth" in candidate or candidate.get("expected_role") is not None:
        leaks.append("candidate.ground_truth_or_expected")

    base = {
        "live_call": True,
        "vision_source": "LIVE_P254_PROMPT",
        "replay": False,
        "prompt_fingerprint": p_fp,
        "evidence_fingerprint": evidence.get("evidence_fingerprint"),
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "truth_leak_keys": leaks,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if leaks:
        return {
            **base,
            "api_ok": False,
            "error": "TRUTH_LEAK_BLOCKED",
            "validation": {"valid": False, "errors": ["TRUTH_LEAK_BLOCKED"], "warnings": []},
            "validated_interpretation": None,
            "usage": {},
        }
    if not evidence.get("images"):
        return {
            **base,
            "api_ok": False,
            "error": "missing_evidence_images",
            "validation": {"valid": False, "errors": ["MISSING_IMAGE"], "warnings": []},
            "validated_interpretation": None,
            "usage": {},
        }

    call = call_claude_vision(
        version10_root=version10_root,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images=evidence["images"],
    )
    parsed = None
    validation = {"valid": False, "errors": ["NO_RESPONSE"], "warnings": []}
    validated = None
    if call.get("success") and call.get("raw_text"):
        obj, parse_error = extract_json_object(call["raw_text"])
        if obj is not None:
            parsed = normalize_parsed(obj)
            validation = validate_interpretation(parsed=parsed, expected_candidate_id=cid)
            validated = validation.get("validated_interpretation")
        else:
            validation = {"valid": False, "errors": [parse_error or "PARSE_FAILED"], "warnings": []}
    usage = call.get("usage") or {}
    return {
        **base,
        "api_ok": bool(call.get("success")),
        "error": call.get("error"),
        "claude_call": {
            "success": call.get("success"),
            "error": call.get("error"),
            "error_type": call.get("error_type"),
            "latency_s": call.get("latency_s"),
            "retry_count": call.get("retry_count"),
            "model": call.get("model"),
            "temperature": call.get("temperature"),
        },
        "parsed": parsed,
        "validation": validation,
        "validated_interpretation": validated,
        "usage": usage,
        "model": call.get("model") or CLAUDE_MODEL,
        "temperature": call.get("temperature") if call.get("temperature") is not None else TEMPERATURE,
        "input_tokens": (usage or {}).get("input_tokens") or call.get("estimated_input_tokens"),
        "output_tokens": (usage or {}).get("output_tokens") or call.get("estimated_output_tokens"),
    }


__all__ = ["observe_live"]
