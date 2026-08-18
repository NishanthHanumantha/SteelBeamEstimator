"""P2.6.7 live semantic arbitration prompt. No expected-outcome metadata."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from .config import PROMPT_VERSION, SCHEMA_VERSION

BANNED_KEYS = {
    "ground_truth",
    "expected_role",
    "expected_decision",
    "expected_answer",
    "benchmark_answer",
    "benchmark_label",
    "control_family",
    "estimator_kg",
    "estimator_steel",
    "EstimatorOutput",
    "gt_match_status",
    "stratum",
    "eval_stratum",
    "vision_outcome",
    "p266_reference",
    "reference_class",
    "evaluation_reference",
}

_BANNED_SUBSTRINGS = (
    "ground truth",
    "expected answer",
    "expected class",
    "expected routing",
    "true recovery",
    "duplicate_control",
    "false_skip_control",
    "true_recovery_control",
)

SYSTEM_PROMPT = """You are resolving a specific longitudinal reinforcement ambiguity on a structural beam drawing.

Inspect the supplied beam crop independently.

Decide whether the highlighted / described longitudinal annotation represents:

- DISTINCT_REINFORCEMENT: an additional or missing reinforcement specification that is NOT adequately represented by the deterministic model
- DUPLICATE_OR_REPEAT: a repeat / continuation / duplicate callout of reinforcement already represented by the deterministic model
- AMBIGUOUS: evidence conflicts or is insufficient to distinguish distinct from duplicate
- UNSUPPORTED: the image or context does not contain enough evidence

This is NOT a request to find all reinforcement.
This is NOT a request to change engineering quantities.

Rules:
- Use the image as primary evidence. Deterministic and spatial fields are supporting context only.
- Do not assume the spatial/context status is correct.
- Do not invent quantities, diameters, or roles that the image does not support.
- Prefer AMBIGUOUS over an unsafe DUPLICATE_OR_REPEAT decision.
- Prefer AMBIGUOUS over guessing DISTINCT when the target layer is unclear.
- Return ONLY valid JSON matching the required schema. No markdown fences. No prose outside JSON.
"""


def assert_no_truth_leak(payload: Any) -> List[str]:
    hits: List[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                k = str(key)
                loc = f"{path}.{k}" if path else k
                if k in BANNED_KEYS:
                    hits.append(loc)
                low = k.lower()
                if "ground_truth" in low or "expected_decision" in low or "estimator" in low:
                    hits.append(loc)
                if "reference_class" in low or "control_family" in low:
                    hits.append(loc)
                _walk(val, loc)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            low = node.lower()
            for tok in _BANNED_SUBSTRINGS:
                if tok in low:
                    hits.append(path)

    _walk(payload, "")
    return sorted(set(hits))


def build_user_prompt(*, context: Dict[str, Any]) -> str:
    leaks = assert_no_truth_leak(context)
    if leaks:
        raise ValueError(f"truth-leak keys blocked from prompt: {leaks}")
    body = json.dumps(context, indent=2, default=str, sort_keys=True)
    return (
        "Determine whether the highlighted reinforcement annotation represents an additional/"
        "missing reinforcement specification or repeats reinforcement already represented.\n\n"
        "1. Deterministic extraction currently believes the fields in deterministic_reinforcement.\n"
        "2. The ambiguous annotation(s) are listed in annotation_context and candidate_notation.\n"
        "3. Reinforcement already represented is listed under existing objects / populated layer.\n"
        "4. spatial_context is SUPPORTING evidence only; do not follow it blindly.\n"
        "5. Independently inspect the image. Do not infer a hidden expected label. None is provided.\n\n"
        f"schema_version: {SCHEMA_VERSION}\n"
        "Return JSON with keys: schema_version, decision, confidence, target_layer, "
        "existing_representation_assessment, deterministic_context_consistent, "
        "spatial_context_consistent, conflict_present, reason_codes, evidence, "
        "annotation_interpretation, uncertainty_notes.\n"
        "decision must be one of DISTINCT_REINFORCEMENT | DUPLICATE_OR_REPEAT | AMBIGUOUS | UNSUPPORTED.\n"
        "target_layer must be one of TOP | BOTTOM | SIDE | UNKNOWN.\n"
        "existing_representation_assessment must be one of REPRESENTED | NOT_REPRESENTED | UNCERTAIN.\n"
        "confidence must be a number in [0, 1].\n"
        "reason_codes must be a JSON array of strings.\n"
        "evidence must be a JSON array of strings, not a nested object.\n"
        "annotation_interpretation must be a single string, not an object.\n"
        "uncertainty_notes must be a single string, not an array.\n\n"
        "SEMANTIC CONTEXT (no expected-outcome labels):\n"
        f"{body}\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps(
        {"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def prompt_document() -> str:
    return (
        "# P2.6.7 live semantic arbitration prompt\n\n"
        f"prompt_version: `{PROMPT_VERSION}`\n"
        f"schema_version: `{SCHEMA_VERSION}`\n\n"
        "## System\n\n"
        f"{SYSTEM_PROMPT}\n\n"
        "## User template notes\n\n"
        "- Image: QA.3.0 shared rendered beam crop\n"
        "- Context: deterministic reinforcement + annotation geometry + P2.6.5 spatial supporting evidence\n"
        "- Frozen P2.6.1 Vision observations and P2.6.6 semantic classes are excluded from the prompt\n"
        "- Evaluation reference labels are applied only after inference\n"
    )


__all__ = [
    "BANNED_KEYS",
    "SYSTEM_PROMPT",
    "assert_no_truth_leak",
    "build_user_prompt",
    "prompt_document",
    "prompt_fingerprint",
]
