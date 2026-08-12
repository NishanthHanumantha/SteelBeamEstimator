"""Per-candidate Claude Vision pilot execution."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .benchmark_evaluator import derive_ground_truth, evaluate_against_ground_truth
from .claude_vision_client import call_claude_vision
from .config import PRIMARY_EVIDENCE_MODE
from .interpretation_validator import validate_interpretation
from .pilot_candidate_loader import build_evidence_package
from .response_schema import extract_json_object, normalize_parsed
from .vision_prompt import SYSTEM_PROMPT, build_user_prompt, prompt_fingerprint

MODEL_VERSION = "10.7.0"


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

    # Ground truth derived locally — never sent to Claude
    gt = derive_ground_truth(
        candidate.get("raw_text") or "",
        candidate.get("candidate_reason_codes"),
    )

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
        # Explicit firewall note
        "ground_truth_sent_to_claude": False,
        "production_write": False,
    }
    _dump(out_dir / "input_manifest.json", input_manifest)

    if not evidence.get("images"):
        result = {
            "candidate_id": cid,
            "beam_id": candidate.get("beam_id"),
            "success": False,
            "error": "missing_evidence_images",
            "claude_call": {"success": False, "error": "missing_images"},
            "ground_truth": gt,
            "evaluation": {
                "evaluation": "API_ERROR",
                "exact_match": False,
                "details": "missing_images",
            },
        }
        _dump(out_dir / "evaluation.json", result)
        return result

    call = call_claude_vision(
        version10_root=version10_root,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        images=evidence["images"],
    )
    # Persist raw response without images/base64
    claude_record = {
        **call,
        "candidate_id": cid,
        "evidence_mode": evidence_mode,
        "prompt_fingerprint": p_fp,
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
            validation = validate_interpretation(
                parsed=parsed, expected_candidate_id=cid
            )
            validated = validation.get("validated_interpretation")
        else:
            validation = {
                "valid": False,
                "errors": [parse_error or "PARSE_FAILED"],
                "warnings": [],
            }

    _dump(
        out_dir / "validated_interpretation.json",
        {
            "parsed": parsed,
            "validation": validation,
            "parse_error": parse_error,
        },
    )

    evaluation = evaluate_against_ground_truth(
        validated=validated,
        validation_ok=bool(validation.get("valid")),
        ground_truth=gt,
        api_ok=bool(call.get("success")),
    )
    # Store GT only in evaluation artifacts (not sent to Claude)
    eval_out = {
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "raw_text": candidate.get("raw_text"),
        "evaluation": evaluation,
        "ground_truth": gt,
        "validation": validation,
    }
    _dump(out_dir / "evaluation.json", eval_out)

    return {
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "raw_text": candidate.get("raw_text"),
        "candidate_priority": candidate.get("candidate_priority"),
        "candidate_reason_codes": candidate.get("candidate_reason_codes"),
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
        "ground_truth": gt,
        "evaluation": evaluation,
        "fingerprints": {
            "evidence": evidence.get("evidence_fingerprint"),
            "prompt": p_fp,
            "validation": _fp(validation),
            "claude_response": _fp(call.get("raw_text") or ""),
        },
        "production_impact": "NONE",
        "engineering_write": False,
    }


__all__ = ["run_one_candidate"]
