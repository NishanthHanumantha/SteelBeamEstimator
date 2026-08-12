"""
Phase P2.5.0.2 — Top Reinforcement Evidence Trace & Completeness Diagnostic.
MODEL_VERSION: 10.6.1 (diagnostic only — no production version bump)
"""
from __future__ import annotations

MODEL_VERSION = "10.6.1"
PHASE_ID = "P2.5.0.2"
PHASE_NAME = "Top Reinforcement Evidence Trace & Completeness Diagnostic"
OUTPUT_DIRNAME = "PhaseP2502_top_reinforcement_trace"
SCOPE = "FOURTH_SET_ONLY"
MODE = "DIAGNOSTIC_ONLY"
ENGINEERING_CHANGES = "NONE"

FOCUS = {
    "B97A": {
        "rejected_bars": ["BAR::2B7B3233", "BAR::5B1BFCC2"],
        "own_entity": "OWN::B97A::1247FFF",
        "own_handle": "1247FFF",
        "ann_4y25": "ANN-d7128f62",
        "leader": "LDR::E83C245B",
    },
    "B98A": {
        "rejected_bars": ["BAR::E6591903", "BAR::4D469A4E"],
        "own_entity": "OWN::B98A::1247FFE",
        "own_handle": "1247FFE",
        "ann_4y25": "ANN-2a9913fa",
        "leader": "LDR::1812F192",
    },
}

# Known DXF handle mapping for rejected R.3.1 bars (from coordinate match)
# R.3.1 bar_id is UUID-like, not the DXF handle.
BAR_DXF_HANDLE_HINTS = {
    "BAR::2B7B3233": "1221B7C",
    "BAR::5B1BFCC2": "12469C4",
    "BAR::E6591903": "11CD1B5",
    "BAR::4D469A4E": "11CD1B7",
}

CLASSIFICATIONS = (
    "ACTUAL_TOP_REINFORCEMENT",
    "FALSE_CANDIDATE",
    "WRONG_ENTITY_MAPPING",
    "COORDINATE_ERROR",
    "DUPLICATE_REPRESENTATION",
    "NEIGHBOUR_REINFORCEMENT",
    "UNRESOLVED",
)
