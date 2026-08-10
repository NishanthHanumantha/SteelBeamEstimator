"""
P2.4 configuration — Fourth Set Generalized Bar Failure Attribution Audit.
MODEL_VERSION: 10.6.0
DIAGNOSTIC ONLY — no engineering changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

MODEL_VERSION = "10.6.0"
PHASE_ID = "P2.4"
SCOPE = "FOURTH_SET_ONLY"
MODE = "DIAGNOSTIC_ONLY"
ENGINEERING_CHANGES = "NONE"

PRIORITY_BEAMS: Tuple[str, ...] = (
    "B14",
    "B15",
    "B16",
    "B18",
    "B19",
    "B22",
    "B23",
    "B29",
    "B42A",
    "B45",
    "B46",
)

PROBLEM_RENDER_BEAMS: Tuple[str, ...] = ("B10", "B12", "B13")
SHARED_CASE_BEAMS: Tuple[str, ...] = ("B8", "B9", "B10")

TOP_ROLES = frozenset(
    {"TOP_MAIN", "TOP_EXTRA", "TOP_SUPPORT", "EXTRA_TOP", "CONTINUOUS_TOP"}
)
TEXT_PRIMARY_ROLES = frozenset(
    {"STIRRUP", "STIRRUP_HOOK", "SPACER_BAR", "CHAIR_BAR", "SIDE_FACE"}
)

FIRST_FAIL_STAGES: Tuple[str, ...] = (
    "DXF_GEOMETRY",
    "PHYSICAL_BAR_DETECTION",
    "OWNERSHIP",
    "ANNOTATION_ASSOCIATION",
    "LEADER_CHAIN",
    "ROLE_RESOLUTION",
    "DIAMETER_RESOLUTION",
    "QUANTITY_RESOLUTION",
    "ENGINEERING_OBJECT",
    "VB1_INTEGRATION",
    "FINAL_STEEL",
    "NO_FAILURE",
    "UNKNOWN",
)

RECOMMENDATION_MAP = {
    "PHYSICAL_BAR_DETECTION": "BAR CANDIDATE / GEOMETRY RECOVERY",
    "OWNERSHIP": "CONTROLLED OWNERSHIP IMPROVEMENT",
    "ANNOTATION_ASSOCIATION": "ANNOTATION ↔ BAR RESOLUTION",
    "LEADER_CHAIN": "LEADER CHAIN RECOVERY",
    "ROLE_RESOLUTION": "ENGINEERING ROLE RESOLUTION",
    "DIAMETER_RESOLUTION": "DIAMETER RESOLUTION ENHANCEMENT",
    "QUANTITY_RESOLUTION": "QUANTITY INTERPRETATION ENHANCEMENT",
    "ENGINEERING_OBJECT": "OWNERSHIP → ENGINEERING BRIDGE",
    "VB1_INTEGRATION": "OWNERSHIP → ENGINEERING BRIDGE",
    "DXF_GEOMETRY": "BAR CANDIDATE / GEOMETRY RECOVERY",
    "FINAL_STEEL": "OWNERSHIP → ENGINEERING BRIDGE",
}


@dataclass(frozen=True)
class P24Config:
    set_key: str = "Fourth"
    drawing_set: str = "Fourth Set Drawings"
    mutate_production: bool = False
    run_determinism_twice: bool = True
    max_visuals_per_class: int = 3
    priority_beams: Tuple[str, ...] = field(default_factory=lambda: PRIORITY_BEAMS)


DEFAULT_CONFIG = P24Config()
