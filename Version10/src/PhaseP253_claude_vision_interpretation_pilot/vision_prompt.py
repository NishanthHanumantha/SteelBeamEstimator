"""P2.5.3 Claude Vision prompts."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from .config import PROMPT_VERSION, SCHEMA_VERSION

MODEL_VERSION = "10.7.0"

SYSTEM_PROMPT = """You are interpreting structural reinforcement notation from an engineering drawing.

Use ONLY the supplied image evidence and metadata.
Identify only what is visually/evidentially supported.

Rules:
- Do not guess missing information.
- Do not infer a quantity merely because it would be typical engineering practice.
- If the annotation is unreadable or evidence is insufficient, return interpretation_status = INSUFFICIENT_EVIDENCE.
- If the image and text disagree, return interpretation_status = CONFLICT.
- If the notation can be interpreted but some component is uncertain, return interpretation_status = PARTIAL.
- Only return RESOLVED when the interpretation is sufficiently supported by the evidence.
- For OCR-corrupted notation, you may normalize obvious OCR corruption ONLY when the visual evidence supports the correction.
- Never silently convert uncertain text into a definite answer.
- For STIRRUP notation: do NOT populate longitudinal quantity; use legs, diameter_mm, spacing_mm, spacing_pattern.
- Return ONLY valid JSON matching the required schema. No markdown fences. No prose outside JSON.
"""


def build_user_prompt(metadata: Dict[str, Any]) -> str:
    schema_hint = {
        "candidate_id": metadata.get("candidate_id"),
        "interpretation_status": "RESOLVED | PARTIAL | INSUFFICIENT_EVIDENCE | CONFLICT",
        "reinforcement_type": "LONGITUDINAL_BAR | STIRRUP | SIDE_FACE | DEVELOPMENT_NOTE | OTHER | UNKNOWN",
        "quantity": None,
        "diameter_mm": None,
        "legs": None,
        "spacing_mm": [],
        "spacing_pattern": None,
        "normalized_notation": None,
        "confidence": None,
        "visual_evidence": [],
        "reasoning_summary": "",
        "warnings": [],
    }
    return (
        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"
        "Evidence metadata (deterministic upstream; not ground truth):\n"
        f"{json.dumps(metadata, indent=2, default=str)}\n\n"
        "Images attached:\n"
        "- Image 1: local refined/render-safe crop of the target annotation/beam region\n"
        "- Image 2 (if present): medium beam-context crop\n\n"
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


__all__ = ["SYSTEM_PROMPT", "build_user_prompt", "prompt_fingerprint"]
