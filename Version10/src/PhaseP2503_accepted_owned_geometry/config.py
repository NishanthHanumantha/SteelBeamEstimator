"""
Phase P2.5.0.3 — Accepted OWN TOP_BAR Evidence Packaging Fix.
MODEL_VERSION: 10.6.2 (evidence-layer production artifact change)
"""
from __future__ import annotations

MODEL_VERSION = "10.6.2"
PHASE_ID = "P2.5.0.3"
PHASE_NAME = "Accepted OWN TOP_BAR Evidence Packaging Fix"
OUTPUT_DIRNAME = "PhaseP2503_accepted_owned_geometry"
SCOPE = "FOURTH_SET_ONLY"
MODE = "EVIDENCE_LAYER_FIX"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "NONE"

FOCUS = {
    "B97A": {
        "rejected_bars": ["BAR::2B7B3233", "BAR::5B1BFCC2"],
        "own_entity": "OWN::B97A::1247FFF",
        "own_handle": "1247FFF",
        "entity_type": "LWPOLYLINE",
        "layer": "-STR-BEAM",
        "ann_4y25": "ANN-d7128f62",
        "annotation_text": "4-Y25",
        "leader": "LDR::E83C245B",
    },
    "B98A": {
        "rejected_bars": ["BAR::E6591903", "BAR::4D469A4E"],
        "own_entity": "OWN::B98A::1247FFE",
        "own_handle": "1247FFE",
        "entity_type": "LWPOLYLINE",
        "layer": "-STR-BEAM",
        "ann_4y25": "ANN-2a9913fa",
        "annotation_text": "4-Y25",
        "leader": "LDR::1812F192",
    },
}
