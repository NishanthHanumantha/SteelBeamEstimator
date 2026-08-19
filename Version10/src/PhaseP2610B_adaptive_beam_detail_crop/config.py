"""
Phase P2.6.10-B — Adaptive Beam Detail Completeness & Reinforcement Evidence Crop Benchmark.
MODEL_VERSION: 10.11.11

Shadow / research only. Does not change P2.6.6–P2.6.10-A routing.
No Claude Vision. No production mutation.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.11"
PHASE_ID = "P2.6.10-B"
PHASE_NAME = "Adaptive Beam Detail Completeness & Reinforcement Evidence Crop Benchmark"
OUTPUT_DIRNAME = "PhaseP2610B_adaptive_beam_detail_crop"
SCOPE = "ADAPTIVE_BEAM_DETAIL_COMPLETENESS"
MODE = "SHADOW_RESEARCH"
ENGINEERING_CHANGES = "NONE"

GATE_VERSION = "P2610B_ADAPTIVE_BEAM_DETAIL_COMPLETENESS_V1_0"
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

MODE_OFFLINE = "OFFLINE_BENCHMARK"

DETAIL_MAX_PX = 1800
CONTEXT_MAX_PX = 1400
RENDER_DPI = 150
EVIDENCE_PAD_MM = 220.0
TITLE_BELOW_PAD_MM = 720.0
ROW_TITLE_GAP_MM = 120.0
MIN_STACK_ABOVE_MM = 2600.0
MAX_DETAIL_WIDTH_MM = 8200.0
MAX_DETAIL_HEIGHT_MM = 6800.0
SAME_ROW_Y_MM = 2000.0
NEXT_ROW_MIN_DY_MM = 900.0

LOCALIZATION_METHOD = "title_anchor_plus_spatial_evidence_envelope"
LOCALIZATION_SOURCE = "reinforcement_dxf_title_outline_text_dimension_leader"

P2610A_OUTPUT_DIRNAME = "PhaseP2610A_beam_region_crop_audit"
P266_OUTPUT_DIRNAME = "PhaseP266_semantic_longitudinal_resolver"
P267_OUTPUT_DIRNAME = "PhaseP267_live_semantic_arbitration"
P268_OUTPUT_DIRNAME = "PhaseP268_evidence_conflict_arbitration"
P269_OUTPUT_DIRNAME = "PhaseP269_reinforcement_group_interpretation"
