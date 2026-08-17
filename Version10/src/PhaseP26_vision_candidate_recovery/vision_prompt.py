"""P2.6 Vision prompt — recover visually supported missed reinforcement. No GT."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from .config import PROMPT_VERSION, SCHEMA_VERSION

from PhaseP254_semantic_reinforcement_vision_benchmark.vision_prompt import (
    BANNED_KEYS,
    assert_no_truth_leak,
)

SYSTEM_PROMPT = """You are inspecting a localized structural beam region from an engineering drawing.

Task: list reinforcement annotations that are VISUALLY PRESENT in the image, especially any that may not already be captured in the supplied deterministic annotation list.

Rules:
- Use ONLY the supplied image and deterministic metadata.
- Identify only what is visually supported.
- Do not invent reinforcement because it would be typical practice.
- Do not calculate steel, cut length, or piece counts from span.
- Do not assume nearby text belongs to the TARGET beam.
- If association is unclear, set beam_association = UNCERTAIN.
- If a field is unreadable, set it to null (UNKNOWN). Never guess diameter, quantity, spacing, or legs.
- Do not force an uncertain role into TOP_BAR or BOTTOM_BAR.
- Return ONLY valid JSON matching the required schema. No markdown fences. No prose outside JSON.
"""


def build_user_prompt(*, region_id: str, beam_id: str, metadata: Dict[str, Any]) -> str:
    schema_hint = {
        "region_id": region_id,
        "beam_id": beam_id,
        "candidates": [
            {
                "candidate_index": 1,
                "annotation_text": None,
                "candidate_type": (
                    "LONGITUDINAL_REINFORCEMENT | STIRRUP | SIDE_FACE_REINFORCEMENT | "
                    "SPACER | OTHER_REINFORCEMENT | UNKNOWN"
                ),
                "role": "TOP_BAR | BOTTOM_BAR | STIRRUP | SIDE_FACE | SPACER | ADDITIONAL | UNKNOWN",
                "diameter_mm": None,
                "quantity": None,
                "spacing_mm": [],
                "legs": None,
                "beam_association": "TARGET_BEAM | OTHER_BEAM | UNCERTAIN",
                "approx_location": "short visual description or null",
                "vision_confidence": None,
                "text_confidence": None,
                "evidence_notes": [],
                "listed_in_deterministic_metadata": False,
            }
        ],
    }
    return (
        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"
        "Question: Which reinforcement annotations are visually present in this TARGET BEAM region, "
        "including any that may be missing from the deterministic annotation list?\n\n"
        "Deterministic metadata (NOT ground truth / NOT expected answers):\n"
        f"{json.dumps(metadata, indent=2, default=str)}\n\n"
        "Image 1: localized beam-region crop of the target beam with surrounding context.\n\n"
        "Return exactly one JSON object with this shape:\n"
        f"{json.dumps(schema_hint, indent=2)}\n"
        "If no additional reinforcement is visible, return candidates as an empty list.\n"
        "Prefer candidates that are NOT already listed in deterministic_reinforcement.\n"
        "Return at most 12 candidates. Do not duplicate the same annotation.\n"
        "region_id and beam_id in the response MUST match the provided values.\n"
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
