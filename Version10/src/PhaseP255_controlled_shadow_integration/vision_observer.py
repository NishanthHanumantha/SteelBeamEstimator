"""Vision observer: replay frozen P2.5.4 responses, or live-call the same prompt/schema."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import (
    call_claude_vision,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.candidate_loader import (
    build_evidence_package,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.config import (
    PRIMARY_EVIDENCE_MODE,
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

from .config import VISION_SOURCE_LIVE, VISION_SOURCE_REPLAY
from .frozen_loader import load_p254_vision_replay


def observe_vision(
    *,
    candidate: Dict[str, Any],
    version10_root: Path,
    live: bool,
) -> Dict[str, Any]:
    if not live:
        replay = load_p254_vision_replay(version10_root, candidate["candidate_id"])
        replay["vision_source"] = VISION_SOURCE_REPLAY
        replay["live_call"] = False
        return replay
    return _live_observe(candidate=candidate, version10_root=version10_root)


def _live_observe(*, candidate: Dict[str, Any], version10_root: Path) -> Dict[str, Any]:
    cid = candidate["candidate_id"]
    evidence = build_evidence_package(
        candidate=candidate,
        version10_root=version10_root,
        evidence_mode=PRIMARY_EVIDENCE_MODE,
    )
    user_prompt = build_user_prompt(evidence["metadata"])
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    leaks = assert_no_truth_leak(evidence["metadata"])
    leaks += assert_no_truth_leak({"user_prompt": user_prompt, "system": SYSTEM_PROMPT})
    if leaks:
        return {
            "vision_source": VISION_SOURCE_LIVE,
            "live_call": True,
            "api_ok": False,
            "claude_call": {"success": False, "error": "TRUTH_LEAK_BLOCKED"},
            "parsed": None,
            "validation": {"valid": False, "errors": ["TRUTH_LEAK_BLOCKED"], "warnings": []},
            "validated_interpretation": None,
            "evaluation": None,
            "evidence_fingerprint": evidence.get("evidence_fingerprint"),
            "prompt_fingerprint": p_fp,
            "usage": {},
            "model": None,
            "temperature": 0,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
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
            validation = {
                "valid": False,
                "errors": [parse_error or "PARSE_FAILED"],
                "warnings": [],
            }
    return {
        "vision_source": VISION_SOURCE_LIVE,
        "live_call": True,
        "api_ok": bool(call.get("success")),
        "claude_call": call,
        "parsed": parsed,
        "validation": validation,
        "validated_interpretation": validated,
        "evaluation": None,
        "evidence_fingerprint": evidence.get("evidence_fingerprint"),
        "prompt_fingerprint": p_fp,
        "usage": call.get("usage") or {},
        "model": call.get("model"),
        "temperature": call.get("temperature"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["observe_vision"]
