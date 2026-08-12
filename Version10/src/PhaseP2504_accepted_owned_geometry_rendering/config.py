"""
Phase P2.5.0.4 — Accepted OWN TOP_BAR Engineering Crop Rendering Fix.
MODEL_VERSION: 10.6.3
"""
from __future__ import annotations

MODEL_VERSION = "10.6.3"
PHASE_ID = "P2.5.0.4"
PHASE_NAME = "Accepted OWN TOP_BAR Engineering Crop Rendering Fix"
OUTPUT_DIRNAME = "PhaseP2504_accepted_owned_geometry_rendering"
SCOPE = "FOURTH_SET_ONLY"
MODE = "RENDERING_LAYER_FIX"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "NONE"

# Reuse P2.5.0.3 focus targets
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
        "approx_crop_wh_mm": (5410.0, 3219.0),
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
        "approx_crop_wh_mm": (3585.0, 3049.0),
    },
}

ROOT_CAUSE = (
    "OWN TOP_BAR LWPOLYLINEs on -STR-BEAM use BYLAYER ACI color 7 (white). "
    "ezdxf MatplotlibBackend draws them as white strokes on a white PNG "
    "background, so they are present in the draw pass but invisible. "
    "The diagnostic overlay redraws the same coordinates in magenta, which "
    "is why overlay showed OWN while engineering crop did not."
)
