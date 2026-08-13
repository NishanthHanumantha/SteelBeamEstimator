"""P2.5.4 Claude Vision semantic prompt."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from .config import PROMPT_VERSION, SCHEMA_VERSION

MODEL_VERSION = "10.8.0"

SYSTEM_PROMPT = """You are interpreting structural reinforcement notation from an engineering drawing.

Task: determine what reinforcement is represented by the supplied annotation in the context of the supplied TARGET BEAM.

Distinguish READING THE TEXT from UNDERSTANDING THE ENGINEERING MEANING.

Rules:
- Use ONLY the supplied image evidence and deterministic metadata.
- Identify only what is visually/evidentially supported.
- Do not guess missing information.
- Do not infer a quantity merely because it would be typical engineering practice.
- Do not assume that "4-Y20" is a TOP_BAR. Role requires spatial/visual/context evidence (position, leader, surrounding reinforcement).
- If role cannot be established, set role = UNKNOWN and interpretation_status may be PARTIAL.
- If the annotation is unreadable or evidence is insufficient, return interpretation_status = INSUFFICIENT_EVIDENCE.
- If the image and text disagree, return interpretation_status = CONFLICT.
- If the notation can be interpreted but some component is uncertain, return interpretation_status = PARTIAL.
- Only return RESOLVED when the interpretation is sufficiently supported by the evidence.
- For OCR-corrupted notation, you may normalize obvious OCR corruption ONLY when the visual evidence supports the correction.
- Never silently convert uncertain text into a definite answer.
- For STIRRUP: do NOT populate longitudinal quantity; use legs, diameter_mm, spacing_mm, spacing_pattern. Do not calculate stirrup piece count.
- For LONGITUDINAL_BAR: quantity and diameter_mm when supported; role separately.
- For SIDE_FACE_REINFORCEMENT: classify semantic type/role when supported; do not invent number/diameter.
- beam_association must be TARGET_BEAM, OTHER_BEAM, or UNCERTAIN based on leader/position/geometry — not from text alone.
- Return ONLY valid JSON matching the required schema. No markdown fences. No prose outside JSON.
"""

BANNED_KEYS = {
    "ground_truth",
    "expected_role",
    "expected_type",
    "expected_quantity",
    "expected_diameter_mm",
    "expected_spacing_mm",
    "semantic_class",
    "benchmark_answer",
}


def build_user_prompt(metadata: Dict[str, Any]) -> str:
    schema_hint = {
        "candidate_id": metadata.get("candidate_id"),
        "interpretation_status": "RESOLVED | PARTIAL | INSUFFICIENT_EVIDENCE | CONFLICT",
        "semantic_type": (
            "LONGITUDINAL_BAR | STIRRUP | SIDE_FACE_REINFORCEMENT | "
            "SUPPORT_REINFORCEMENT | ADDITIONAL_REINFORCEMENT | "
            "DEVELOPMENT_NOTE | OTHER | UNKNOWN"
        ),
        "role": (
            "TOP_BAR | BOTTOM_BAR | STIRRUP | SIDE_FACE | "
            "SUPPORT_TOP | SUPPORT_BOTTOM | ADDITIONAL | UNKNOWN"
        ),
        "quantity": None,
        "diameter_mm": None,
        "legs": None,
        "spacing_mm": [],
        "spacing_pattern": None,
        "beam_association": "TARGET_BEAM | OTHER_BEAM | UNCERTAIN",
        "zone": "SPAN | SUPPORT | END | UNKNOWN",
        "normalized_notation": None,
        "confidence": None,
        "evidence_basis": [],
        "warnings": [],
    }
    return (
        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"
        "Question: What reinforcement is represented by this annotation "
        "in the context of the supplied target beam?\n\n"
        "Evidence metadata (deterministic upstream; NOT ground truth / NOT expected answers):\n"
        f"{json.dumps(metadata, indent=2, default=str)}\n\n"
        "Images attached:\n"
        "- Image 1: local refined/render-safe crop of the target annotation/beam region "
        "(or beam engineering crop when annotation-local crop is not in the frozen set)\n"
        "- Image 2 (if present and distinct): medium beam-context crop\n\n"
        "Return exactly one JSON object with this shape:\n"
        f"{json.dumps(schema_hint, indent=2)}\n\n"
        "candidate_id in the response MUST match the provided candidate_id.\n"
        "confidence should be a number from 0 to 1, or null if abstaining.\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps(
        {"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_no_truth_leak(payload: Dict[str, Any]) -> List[str]:
    leaked: List[str] = []

    def _walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{path}.{k}" if path else k
                if k in BANNED_KEYS:
                    leaked.append(p)
                _walk(v, p)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")

    _walk(payload, "")
    return leaked


__all__ = [
    "SYSTEM_PROMPT",
    "assert_no_truth_leak",
    "build_user_prompt",
    "prompt_fingerprint",
]
