"""C.5 Vision prompt. Physical groups first. Role is a hypothesis only."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from .config import PROMPT_VERSION, SCHEMA_VERSION

SYSTEM_PROMPT = """You are interpreting reinforcement evidence from two engineering-drawing images of ONE target beam.

You receive:
- Image 1 CONTEXT: locates the target beam relative to neighbouring beam details.
- Image 2 DETAIL: primary evidence for that target beam's reinforcement.

Rules:
- Identify the requested target beam first. Use both context and detail.
- Interpret ONLY the requested target beam. Neighbouring annotations are not target evidence.
- Identify physical reinforcement groups independently of MAIN/EXTRA labels.
- Classify layer (TOP / BOTTOM / SIDE_FACE / OTHER) independently from role.
- Read specification carefully (count, diameter, spacing).
- Preserve physically distinct groups even when specification is identical.
- Do not merge two groups merely because they have the same specification.
- MAIN versus EXTRA is a hypothesis only (role_hypothesis). Physical group identity does not require a confident role.
- If bar length or span is visually unclear, set relative_length_evidence and span_relationship to UNKNOWN. Do not invent length from text labels.
- Report uncertainty rather than guessing.
- Do not calculate steel weight, quantity totals, BBS, cut length, or development length.
- Do not recommend recovery or production changes.
- Return ONLY a JSON object. No markdown fences. No prose outside JSON.
"""


def build_user_prompt(*, beam_id: str, context_source: str, detail_source: str) -> str:
    schema = {
        "target_beam_id": beam_id,
        "target_identified": True,
        "association_confidence": 0.0,
        "groups": [
            {
                "physical_group_id": "G1",
                "layer": "TOP|BOTTOM|SIDE_FACE|OTHER",
                "spec": "5-Y20",
                "bar_count": 5,
                "role_hypothesis": "MAIN|EXTRA|UNKNOWN",
                "role_confidence": 0.0,
                "support_scope": "FULL_SPAN|LEFT_SUPPORT|RIGHT_SUPPORT|BOTH_SUPPORTS|UNKNOWN",
                "relative_length_evidence": "LONGER|SHORTER|SIMILAR|UNKNOWN",
                "span_relationship": "FULL_SPAN|PARTIAL_LEFT|PARTIAL_RIGHT|PARTIAL_SUPPORT|UNKNOWN",
                "confidence": 0.0,
                "evidence": "short visual note",
            }
        ],
        "stirrups": [
            {
                "spec": "4L-Y8@100C/C",
                "confidence": 0.0,
                "evidence": "short visual note",
            }
        ],
        "ambiguities": [],
        "neighbour_evidence_detected": False,
        "response_status": "OK",
    }
    return (
        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"
        f"TARGET BEAM ID: {beam_id}\n"
        f"Context image provenance (not a quality ranking): {context_source}\n"
        f"Detail image provenance (not a quality ranking): {detail_source}\n\n"
        "Image 1 is CONTEXT. Image 2 is DETAIL.\n"
        "Identify the target beam first, then its physical reinforcement groups.\n"
        "Return exactly one JSON object with this shape:\n"
        f"{json.dumps(schema, indent=2)}\n"
        "target_beam_id MUST equal the TARGET BEAM ID above.\n"
        "Do not include production_action, steel_quantity, BBS, or recover fields.\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps(
        {"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["SYSTEM_PROMPT", "build_user_prompt", "prompt_fingerprint"]
