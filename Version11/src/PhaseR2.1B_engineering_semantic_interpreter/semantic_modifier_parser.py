"""
semantic_modifier_parser.py — Parse engineering modifiers from annotation text.
MODEL_VERSION: 7.11.0

Interprets modifiers such as:
  O.E.F. / (O.E.F) / OEF → ONE_EACH_FACE
  BOTH FACE / BOTH FACES   → BOTH_FACES
  N.F. / NF               → NEAR_FACE
  F.F. / FF               → FAR_FACE
  TYP. / TYPICAL          → TYPICAL
  U-BAR / U BAR           → U_BAR
  S.F.R. / SFR            → SIDE_FACE_REINFORCEMENT (both modifier AND role signal)

Returns List[SemanticModifier] ordered by priority (highest first).
"""
from __future__ import annotations

import re
from typing import List

from .semantic_models import (
    SemanticModifier,
    MODIFIER_ONE_EACH_FACE,
    MODIFIER_BOTH_FACES,
    MODIFIER_NEAR_FACE,
    MODIFIER_FAR_FACE,
    MODIFIER_TYPICAL,
    MODIFIER_U_BAR,
    MODIFIER_SIDE_FACE_REINF,
)

# Each rule: (pattern, canonical_name, priority)
# Higher priority = more authoritative.
_MODIFIER_RULES: List[tuple] = [
    # S.F.R. — side face reinforcement (highest priority: role signal)
    (re.compile(r"S\.?F\.?R\.?", re.I),            MODIFIER_SIDE_FACE_REINF, 100),

    # O.E.F. — one each face
    (re.compile(r"\(?\bO\.?E\.?F\.?\)?", re.I),     MODIFIER_ONE_EACH_FACE, 90),
    (re.compile(r"\bONE\s+EACH\s+FACE\b", re.I),    MODIFIER_ONE_EACH_FACE, 90),

    # BOTH FACE / BOTH FACES
    (re.compile(r"\bBOTH\s+FACE[S]?\b", re.I),      MODIFIER_BOTH_FACES, 85),

    # N.F. / NF / NEAR FACE
    (re.compile(r"\bN\.?F\.?\b", re.I),              MODIFIER_NEAR_FACE, 80),
    (re.compile(r"\bNEAR\s+FACE\b", re.I),           MODIFIER_NEAR_FACE, 80),

    # F.F. / FF / FAR FACE
    (re.compile(r"\bF\.?F\.?\b", re.I),              MODIFIER_FAR_FACE, 80),
    (re.compile(r"\bFAR\s+FACE\b", re.I),            MODIFIER_FAR_FACE, 80),

    # TYP. / TYPICAL
    (re.compile(r"\bTYP\.?\b", re.I),                MODIFIER_TYPICAL, 50),
    (re.compile(r"\bTYPICAL\b", re.I),               MODIFIER_TYPICAL, 50),

    # U-BAR / U BAR
    (re.compile(r"\bU[-\s]?BAR\b", re.I),            MODIFIER_U_BAR, 60),
]


class SemanticModifierParser:
    """
    Scan annotation text for all engineering modifiers.

    Returns a de-duplicated list of SemanticModifier objects sorted by
    descending priority. When the same canonical modifier is matched by
    multiple patterns, the highest-priority match is kept.
    """

    def parse(self, clean_text: str, raw_text: str = "") -> List[SemanticModifier]:
        seen: dict = {}   # canonical → SemanticModifier
        combined = clean_text + " " + raw_text

        for pattern, canonical, priority in _MODIFIER_RULES:
            match = pattern.search(combined)
            if match:
                existing = seen.get(canonical)
                if existing is None or priority > existing.priority:
                    seen[canonical] = SemanticModifier(
                        raw_token   = match.group(0),
                        canonical   = canonical,
                        source_text = match.group(0),
                        priority    = priority,
                    )

        result = sorted(seen.values(), key=lambda m: m.priority, reverse=True)
        return result
