"""Versioned Claude Vision prompt for P2.6.10-C.3. Observational interpretation only."""
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
- Interpret ONLY the requested target beam. Do not treat neighbouring beam annotations as target evidence.
- Do not infer reinforcement that is not visually supported.
- Do not merge two groups only because specification is identical.
- Group identity is layer + role + specification + support-scope/evidence context.
- A TOP MAIN group and a BOTTOM MAIN group with the same qYd specification are physically distinct.
- A MAIN group and an EXTRA group with the same qYd may be physically distinct.
- LEFT and RIGHT extras may be BOTH_SUPPORTS only if visual evidence shows the same group at both supports.
- If target association is uncertain, set target_beam_identified=false and say so in uncertainties.
- UNKNOWN is preferable to hallucination.
- Confidence is not permission for production action.
- Do not calculate steel weight, quantity totals, BBS, cut length, or development length.
- Do not recommend recovery or production changes.
- Return ONLY a JSON object. No markdown fences. No prose outside JSON.
"""


def build_user_prompt(*, beam_id: str, context_source: str, detail_source: str) -> str:
    schema = {
        "target_beam_id": beam_id,
        "target_beam_identified": True,
        "target_association_confidence": 0.0,
        "visual_assessment": {
            "title_visible": True,
            "stirrup_region_visible": True,
            "bottom_region_visible": True,
            "top_region_visible": True,
            "dimension_extra_region_visible": True,
        },
        "reinforcement_groups": [
            {
                "layer": "TOP|BOTTOM|SIDE|STIRRUP|SPACER|SUPPORT_TOP_ZONE|SUPPORT_BOTTOM_ZONE|UNKNOWN",
                "role": "MAIN|EXTRA|STIRRUP|SPACER|UNKNOWN",
                "spec": "e.g. 3Y16",
                "support_scope": "FULL_SPAN|LEFT_SUPPORT|RIGHT_SUPPORT|BOTH_SUPPORTS|UNKNOWN",
                "confidence": 0.0,
                "evidence": "short visual note",
            }
        ],
        "stirrups": [{"spec": "e.g. 3L-Y10@100/125/100C/C", "confidence": 0.0}],
        "uncertainties": [],
        "neighbor_evidence_detected": False,
        "response_status": "OK",
    }
    return (
        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"
        f"TARGET BEAM ID: {beam_id}\n"
        f"Context image provenance (not a quality ranking): {context_source}\n"
        f"Detail image provenance (not a quality ranking): {detail_source}\n\n"
        "Image 1 is CONTEXT. Image 2 is DETAIL.\n"
        "Interpret reinforcement groups belonging only to the target beam.\n"
        "Return exactly one JSON object with this shape:\n"
        f"{json.dumps(schema, indent=2)}\n"
        "target_beam_id MUST equal the TARGET BEAM ID above.\n"
    )


def prompt_fingerprint(system_prompt: str, user_prompt: str) -> str:
    raw = json.dumps(
        {"system": system_prompt, "user": user_prompt, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def prompt_contract_markdown() -> str:
    return "\n".join(
        [
            f"# {PROMPT_VERSION}",
            "",
            SYSTEM_PROMPT,
            "",
            "## User prompt template",
            "",
            build_user_prompt(beam_id="<TARGET_BEAM_ID>", context_source="<phase>", detail_source="<phase>"),
            "",
        ]
    )


__all__ = ["SYSTEM_PROMPT", "build_user_prompt", "prompt_contract_markdown", "prompt_fingerprint"]
