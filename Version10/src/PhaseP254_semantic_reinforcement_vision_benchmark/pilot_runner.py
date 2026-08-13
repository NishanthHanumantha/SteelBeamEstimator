"""Per-candidate P2.5.4 Claude Vision shadow execution."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from PhaseP253_claude_vision_interpretation_pilot.claude_vision_client import (
    call_claude_vision,
)

from .baseline_comparator import collect_conflicts, compare_baseline
from .benchmark_evaluator import evaluate_against_ground_truth
from .candidate_loader import build_evidence_package
from .config import PRIMARY_EVIDENCE_MODE
from .semantic_schema import extract_json_object, normalize_parsed
from .shadow_resolver import build_shadow_result
from .validator import validate_interpretation
from .vision_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt, prompt_fingerprint

MODEL_VERSION = "10.8.0"


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _fp(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_one_candidate(
    *,
    candidate: Dict[str, Any],
    ground_truth: Dict[str, Any],
    version10_root: Path,
    out_candidates_root: Path,
    evidence_mode: str = PRIMARY_EVIDENCE_MODE,
) -> Dict[str, Any]:
    cid = candidate["candidate_id"]
    out_dir = Path(out_candidates_root) / cid.replace("::", "__")
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence = build_evidence_package(
        candidate=candidate,
        version10_root=version10_root,
        evidence_mode=evidence_mode,
    )
    user_prompt = build_user_prompt(evidence["metadata"])
    p_fp = prompt_fingerprint(SYSTEM_PROMPT, user_prompt)
    leaks = assert_no_truth_leak(evidence["metadata"])
    leaks += assert_no_truth_leak({"user_prompt": user_prompt, "system": SYSTEM_PROMPT})

    input_manifest = {
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "raw_text": candidate.get("raw_text"),
        "evidence_mode": evidence_mode,
        "evidence_fingerprint": evidence.get("evidence_fingerprint"),
        "prompt_fingerprint": p_fp,
        "image_roles": [im.get("role") for im in evidence.get("images") or []],
        "image_sha256": [im.get("sha256") for im in evidence.get("images") or []],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ground_truth_sent_to_claude": False,
        "truth_leak_keys": leaks,
        "production_write": False,
        "semantic_class_omitted_from_claude": True,
    }
    _dump(out_dir / "input_manifest.json", input_manifest)

    if leaks:
        result = {
            "candidate_id": cid,
            "success": False,
            "error": "TRUTH_LEAK_BLOCKED",
            "truth_leak_keys": leaks,
            "evaluation": {"evaluation": "INVALID_RESPONSE", "exact_match": False},
        }
        _dump(out_dir / "evaluation.json", result)
        return result

    if not evidence.get("images"):
        result = {
            "candidate_id": cid,
            "beam_id": candidate.get("beam_id"),
            "success": False,
            "error": "missing_evidence_images",
            "evaluation": {"evaluation": "API_ERROR", "exact_match": False},
        }
        _dump(out_dir / "evaluation.json", result)
        return result

    call = call_claude_vision(
        version10_root=version10_root,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images=evidence["images"],
    )
    claude_record = {
        **call,
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "evidence_mode": evidence_mode,
        "prompt_fingerprint": p_fp,
        "evidence_fingerprint": evidence.get("evidence_fingerprint"),
        "prompt_version": "P254_SEMANTIC_VISION_PROMPT_V1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    _dump(out_dir / "claude_response.json", claude_record)

    parsed = None
    parse_error = None
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

    _dump(
        out_dir / "validation.json",
        {"parsed": parsed, "validation": validation, "parse_error": parse_error},
    )

    evidence_weak = (candidate.get("p2523_completeness") not in (None, "PASS")) or (
        candidate.get("semantic_class") == "SIDE_FACE"
    )
    evaluation = evaluate_against_ground_truth(
        validated=validated,
        validation_ok=bool(validation.get("valid")),
        ground_truth=ground_truth,
        api_ok=bool(call.get("success")),
        evidence_weak=evidence_weak,
    )
    conflicts = collect_conflicts(
        validated=validated, candidate=candidate, ground_truth=ground_truth
    )
    comparison = compare_baseline(
        candidate=candidate,
        validated=validated,
        validation_ok=bool(validation.get("valid")),
        ground_truth=ground_truth,
        evaluation=evaluation,
    )
    shadow = build_shadow_result(
        candidate=candidate,
        claude_interpretation=validated,
        validation=validation,
        conflicts=conflicts,
        evaluation=evaluation,
        comparison=comparison,
        evidence_fingerprint=evidence.get("evidence_fingerprint") or "",
        prompt_fingerprint=p_fp,
        usage=call.get("usage"),
    )
    _dump(out_dir / "shadow_result.json", shadow)
    eval_out = {
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "raw_text": candidate.get("raw_text"),
        "semantic_class": candidate.get("semantic_class"),
        "evaluation": evaluation,
        "comparison": comparison,
        "conflicts": conflicts,
        "ground_truth": ground_truth,
        "validation": validation,
    }
    _dump(out_dir / "evaluation.json", eval_out)

    return {
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "raw_text": candidate.get("raw_text"),
        "semantic_class": candidate.get("semantic_class"),
        "semantic_class_tags": candidate.get("semantic_class_tags"),
        "evidence_mode": evidence_mode,
        "evidence_fingerprint": evidence.get("evidence_fingerprint"),
        "prompt_fingerprint": p_fp,
        "claude_call": {
            "success": call.get("success"),
            "model": call.get("model"),
            "latency_s": call.get("latency_s"),
            "usage": call.get("usage"),
            "error": call.get("error"),
            "error_type": call.get("error_type"),
            "response_fingerprint": _fp(call.get("raw_text") or ""),
        },
        "parsed": parsed,
        "validation": validation,
        "validated_interpretation": validated,
        "ground_truth": ground_truth,
        "evaluation": evaluation,
        "comparison": comparison,
        "conflicts": conflicts,
        "shadow_result": shadow,
        "production_impact": "NONE",
        "engineering_write": False,
    }


__all__ = ["run_one_candidate"]
