"""P2.6.1 neutral Vision prompt. No gap_reasons / stratum / selection_reason."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.vision_prompt import (
    BANNED_KEYS,
    assert_no_truth_leak,
)

from .config import PROMPT_VERSION, SCHEMA_VERSION
from .policy import BANNED_VISION_METADATA_KEYS

SYSTEM_PROMPT = """You are inspecting a localized structural beam region from an engineering drawing.

Inspect this structural reinforcement drawing region.
Identify reinforcement annotations visibly associated with the target beam.

Report reinforcement that is visibly present.

Do not infer reinforcement merely because engineering practice would normally require it.
Do not invent missing reinforcement.
Do not assume nearby annotations belong to the beam.
Do not calculate steel, cut length, or piece counts from span.
Use UNKNOWN / null when evidence is insufficient.
If association is unclear, set beam_association = UNCERTAIN.
Do not force an uncertain role into TOP_BAR or BOTTOM_BAR.
Return ONLY valid JSON matching the required schema. No markdown fences. No prose outside JSON.
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
            }
        ],
    }
    return (
        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"
        "Inspect this structural reinforcement drawing region. "
        "Identify reinforcement annotations visibly associated with the target beam. "
        "Report reinforcement that is visibly present.\n\n"
        "Target-beam context (NOT ground truth / NOT expected answers / NOT a failure hint):\n"
        f"{json.dumps(metadata, indent=2, default=str)}\n\n"
        "Image 1: localized beam-region crop of the target beam with surrounding context.\n\n"
        "Return exactly one JSON object with this shape:\n"
        f"{json.dumps(schema_hint, indent=2)}\n"
        "If no reinforcement is visibly associated with the TARGET beam, return candidates as an empty list.\n"
        "Return at most 12 candidates. Do not duplicate the same annotation.\n"
        "region_id and beam_id in the response MUST match the provided values.\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps(
        {"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_prompt_neutral(text: str) -> List[str]:
    hits = []
    blob = text.lower()
    for token in BANNED_VISION_METADATA_KEYS:
        if token.lower() in blob:
            hits.append(token)
    for token in ("difficult", "stratum", "missing stirrup", "expected missing"):
        if token in blob:
            hits.append(token)
    return hits


__all__ = [
    "BANNED_KEYS",
    "SYSTEM_PROMPT",
    "assert_no_truth_leak",
    "assert_prompt_neutral",
    "build_user_prompt",
    "prompt_fingerprint",
]
