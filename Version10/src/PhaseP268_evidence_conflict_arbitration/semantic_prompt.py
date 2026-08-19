"""Constrained observational prompt. Never asks whether to recover."""
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
    "control_family",
    "estimator_kg",
    "EstimatorOutput",
}

SYSTEM_PROMPT = """You classify evidence conflicts on a structural beam drawing.

You receive a normalized evidence record. Classify only:

1. specification_equivalence: MATCH | MISMATCH | UNCERTAIN
2. physical_target_equivalence: SAME | DIFFERENT | UNCERTAIN
3. layer_equivalence: SAME | DIFFERENT | UNCERTAIN
4. conflict_type from the allowed taxonomy
5. confidence in [0, 1]
6. a short rationale string

Rules:
- Same specification does NOT mean same physical reinforcement target.
- Different annotation text does NOT mean different physical reinforcement.
- Do not decide recovery. Do not emit quantities. Do not emit BBS rows.
- Do not override deterministic geometry.
- Return ONLY JSON. No markdown.
"""


def assert_no_truth_leak(payload: Any) -> List[str]:
    hits: List[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                loc = f"{path}.{key}" if path else str(key)
                if str(key) in BANNED_KEYS or "ground_truth" in str(key).lower() or "estimator" in str(key).lower():
                    hits.append(loc)
                _walk(val, loc)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(payload, "")
    return sorted(set(hits))


def build_user_prompt(*, evidence: Dict[str, Any]) -> str:
    leaks = assert_no_truth_leak(evidence)
    if leaks:
        raise ValueError(f"truth-leak keys blocked from prompt: {leaks}")
    body = json.dumps(evidence, indent=2, default=str, sort_keys=True)
    return (
        "Classify specification vs physical-target vs layer identity. Do not decide recovery.\n\n"
        f"schema_version: {SCHEMA_VERSION}\n"
        "Return JSON keys: specification_equivalence, physical_target_equivalence, "
        "layer_equivalence, conflict_type, confidence, rationale.\n\n"
        f"EVIDENCE:\n{body}\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps({"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["SYSTEM_PROMPT", "assert_no_truth_leak", "build_user_prompt", "prompt_fingerprint"]
