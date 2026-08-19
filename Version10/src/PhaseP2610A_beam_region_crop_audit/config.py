"""
Phase P2.6.10-A — Existing Beam-Region Crop Capability Audit.
MODEL_VERSION: 10.11.10

Shadow / research only. Does not change P2.6.6–P2.6.9 routing.
No Claude Vision. No production mutation.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.10"
PHASE_ID = "P2.6.10-A"
PHASE_NAME = "Existing Beam-Region Crop Capability Audit"
OUTPUT_DIRNAME = "PhaseP2610A_beam_region_crop_audit"
SCOPE = "BEAM_REGION_CROP_AUDIT"
MODE = "SHADOW_RESEARCH"
ENGINEERING_CHANGES = "NONE"

GATE_VERSION = "P2610A_BEAM_REGION_CROP_AUDIT_V1_0"
RENDERER_VERSION = "9.3.3"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"

TARGET_BEAMS = 6
BENCHMARK_BEAMS = (
    ("Fourth", "B141"),
    ("Fourth", "B66"),
    ("Fourth", "B161"),
    ("Fifth", "B128"),
    ("Fifth", "B55"),
    ("Fifth", "B65"),
)

MODE_OFFLINE = "OFFLINE_AUDIT"

DETAIL_PAD_MM = 250.0
CONTEXT_PAD_MM = 2200.0
DETAIL_MAX_PX = 1800
CONTEXT_MAX_PX = 1400
RENDER_DPI = 150
OTHER_ROW_TITLE_MM = 900.0

LOCALIZATION_METHOD = "beam_title_plus_outline_geometry"
LOCALIZATION_SOURCE = "reinforcement_dxf_text_and_line_geometry"

ALLOWED_FINAL = (
    "RENDERING_READY_FOR_P2_6_10",
    "RENDERING_READY_WITH_ADAPTER",
    "LOCALIZATION_GAP_REQUIRES_IMPLEMENTATION",
    "EXISTING_RENDERER_NOT_SUITABLE",
    "INVESTIGATION_FAILED",
)

P266_OUTPUT_DIRNAME = "PhaseP266_semantic_longitudinal_resolver"
P267_OUTPUT_DIRNAME = "PhaseP267_live_semantic_arbitration"
P268_OUTPUT_DIRNAME = "PhaseP268_evidence_conflict_arbitration"
P269_OUTPUT_DIRNAME = "PhaseP269_reinforcement_group_interpretation"
