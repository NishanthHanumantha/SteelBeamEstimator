"""Drawing title anchor patterns for region detection."""

import re
from dataclasses import dataclass
from typing import List, Pattern, Tuple

AnchorPattern = Tuple[str, Pattern[str], float]


@dataclass(frozen=True)
class AnchorRule:
    anchor_type: str
    pattern: Pattern[str]
    confidence: float


ANCHOR_RULES: List[AnchorRule] = [
    AnchorRule("framing_plan", re.compile(r"FRAMING\s+PLAN", re.IGNORECASE), 1.0),
    AnchorRule(
        "beam_reinforcement",
        re.compile(r"REINFORCEMENT\s+GFC\s+DETAILS", re.IGNORECASE),
        0.98,
    ),
    AnchorRule(
        "beam_reinforcement",
        re.compile(r"BEAM\s+REINFORCEMENT", re.IGNORECASE),
        0.90,
    ),
    AnchorRule(
        "typical_stirrup",
        re.compile(r"TYPICAL\s+STIRRUP\s+DETAILS", re.IGNORECASE),
        1.0,
    ),
    AnchorRule("general_notes", re.compile(r"GENERAL\s+NOTES", re.IGNORECASE), 1.0),
]

REGION_TYPES = (
    "framing_plan",
    "beam_reinforcement",
    "typical_stirrup",
    "general_notes",
    "unassigned",
)

GEOMETRY_ENTITY_TYPES = frozenset(
    {"LINE", "LWPOLYLINE", "POLYLINE", "TEXT", "MTEXT", "DIMENSION"}
)

# Layers that strongly indicate framing-plan geometry.
FRAMING_LAYER_HINTS = frozenset(
    {
        "SLAB LINE",
        "-STR-COLUMN",
        "-STR-RF-DIM",
        "SEC TEXT",
    }
)

# Layers that strongly indicate reinforcement-detail geometry.
REINFORCEMENT_LAYER_HINTS = frozenset(
    {
        "-STR-TEXT",
        "-STR-REINF",
        "-S-STIRUP",
        "-S-DIM",
        "-STR-RF-DIM",
    }
)
