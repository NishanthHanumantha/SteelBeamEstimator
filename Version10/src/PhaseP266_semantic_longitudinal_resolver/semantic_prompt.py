"""Targeted semantic arbitration prompt. No expected-outcome metadata."""
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
}

SYSTEM_PROMPT = """You are resolving a specific longitudinal reinforcement ambiguity on a structural beam drawing.

Task: inspect the supplied beam crop and decide whether the highlighted / described longitudinal annotation represents a DISTINCT reinforcement requirement that is not already represented by the deterministic extraction, or a DUPLICATE / REPEAT of reinforcement that is already represented.

This is NOT a request to find all reinforcement on the drawing.

Rules:
- Use the image as primary evidence. Deterministic and spatial fields are supporting context only.
- Do not assume the spatial/context status is correct.
- Do not invent quantities, diameters, or roles that the image does not support.
- If the annotation, leader, or beam context is not reliably visible, return UNSUPPORTED.
- If evidence is conflicting or insufficient to decide distinct vs duplicate, return AMBIGUOUS.
- Prefer AMBIGUOUS over an unsafe DUPLICATE_OR_REPEAT decision.
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
                _walk(val, loc)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            low = node.lower()
            if "ground truth" in low or "expected answer" in low:
                hits.append(path)

    _walk(payload, "")
    return sorted(set(hits))


def build_user_prompt(*, context: Dict[str, Any]) -> str:
    leaks = assert_no_truth_leak(context)
    if leaks:
        raise ValueError(f"truth-leak keys blocked from prompt: {leaks}")
    body = json.dumps(context, indent=2, default=str, sort_keys=True)
    return (
        "Resolve this specific longitudinal reinforcement ambiguity.\n\n"
        "1. Deterministic extraction currently believes the fields in deterministic_reinforcement.\n"
        "2. The ambiguous annotation(s) are listed in annotation_context.\n"
        "3. Reinforcement already represented is listed under existing objects / populated layer.\n"
        "4. spatial_context is SUPPORTING evidence only; do not follow it blindly.\n"
        "5. Question: does the annotation represent a distinct missing longitudinal requirement, "
        "or a duplicate/repeat of reinforcement already represented?\n\n"
        f"schema_version: {SCHEMA_VERSION}\n"
        "Return JSON with keys: decision, confidence, annotation_interpretation, target_layer, "
        "existing_representation_assessment, semantic_reason_codes, visual_evidence, "
        "deterministic_context_consistent, spatial_context_consistent, conflict_present.\n"
        "decision must be one of DISTINCT_REINFORCEMENT | DUPLICATE_OR_REPEAT | AMBIGUOUS | UNSUPPORTED.\n"
        "target_layer must be one of TOP | BOTTOM | SIDE | UNKNOWN.\n"
        "existing_representation_assessment must be one of REPRESENTED | NOT_REPRESENTED | UNCERTAIN.\n"
        "confidence must be a number in [0, 1].\n\n"
        "SEMANTIC CONTEXT (no expected-outcome labels):\n"
        f"{body}\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps(
        {"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "BANNED_KEYS",
    "SYSTEM_PROMPT",
    "assert_no_truth_leak",
    "build_user_prompt",
    "prompt_fingerprint",
]
