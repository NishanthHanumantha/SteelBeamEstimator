"""
P2.5.0 — Beam Evidence Rendering & Crop QA.
MODEL_VERSION: 10.6.0
DIAGNOSTIC ONLY — no Claude, no engineering changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

MODEL_VERSION = "10.6.0"
PHASE_ID = "P2.5.0"
PHASE_NAME = "Beam Evidence Rendering & Crop QA"
OUTPUT_DIRNAME = "PhaseP250_beam_evidence_crop_qa"
SCOPE = "FOURTH_SET_ONLY"
MODE = "DIAGNOSTIC_ONLY"
ENGINEERING_CHANGES = "NONE"

# Base margin around beam geometry before evidence expansion (mm)
BASE_MARGIN_MM = 250.0
# Extra pad after evidence union (mm)
EVIDENCE_PAD_MM = 120.0
# Max expansion iterations when following leaders outside crop
MAX_EXPAND_ITERS = 4
# Clutter heuristic: too many non-target annotations in crop
CLUTTER_ANN_THRESHOLD = 25
# Render settings
RENDER_MAX_DIM_PX = 1200
RENDER_DPI = 110


@dataclass(frozen=True)
class P250Config:
    set_key: str = "Fourth"
    drawing_set: str = "Fourth Set Drawings"
    base_margin_mm: float = BASE_MARGIN_MM
    evidence_pad_mm: float = EVIDENCE_PAD_MM
    max_expand_iters: int = MAX_EXPAND_ITERS
    clutter_ann_threshold: int = CLUTTER_ANN_THRESHOLD
    render_max_dim_px: int = RENDER_MAX_DIM_PX
    render_dpi: int = RENDER_DPI
    mutate_production: bool = False


DEFAULT_CONFIG = P250Config()

GateStatus = str  # PASS | FAIL | NOT_APPLICABLE
BBox = Tuple[float, float, float, float]
