"""
P2.6.10-C.3 — Visual Completeness Gate + Claude Vision Shadow Benchmark.
MODEL_VERSION: 10.11.16

SHADOW ONLY. Consumes C.1+C.2 selection_manifest.json.
Does not rerender, reselect, or mutate production.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.16"
PHASE_ID = "P2.6.10-C.3"
PHASE_NAME = "Visual Completeness Gate + Claude Vision Shadow Benchmark"
OUTPUT_DIRNAME = "PhaseP2610C3_visual_completeness_claude_shadow"
GATE_VERSION = "P2610C3_VISUAL_COMPLETENESS_CLAUDE_SHADOW_BENCHMARK_V1_0"
PROMPT_VERSION = "P2610C3_VISION_PROMPT_V1"
SCHEMA_VERSION = "P2610C3_REINFORCEMENT_EVIDENCE_SCHEMA_V1"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"
ENGINEERING_CHANGES = "NONE"

MODE_OFFLINE = "OFFLINE_VALIDATION"
MODE_LIVE = "LIVE_SHADOW"

P2610C1C2_OUTPUT_DIRNAME = "PhaseP2610C1C2_evidence_inventory_candidate_selection"
P269_OUTPUT_DIRNAME = "PhaseP269_reinforcement_group_interpretation"
SELECTION_MANIFEST_NAME = "selection_manifest.json"

STATUS_READY = "VISION_READY"
STATUS_LIMITED = "VISION_READY_WITH_LIMITATIONS"
STATUS_REVIEW = "VISION_REVIEW_ONLY"
STATUS_NOT_READY = "VISION_NOT_READY"

CRITICAL_STATUSES = (
    "EMPTY_RENDER",
    "BLACK_RENDER",
    "LOW_INFORMATION_RENDER",
    "RENDER_MISSING",
)

STILL_CRITICAL_SELECTION = (
    "RETAIN_PREFERRED_STILL_CRITICAL",
    "FALLBACK_STILL_CRITICAL",
    "UNRESOLVED_MISSING",
)

COVERAGE_AMBIGUOUS_MAX = 0.40
EMPTY_SIDES_AMBIGUOUS_MIN = 3
MAX_SCHEMA_PARSE_ATTEMPTS = 1
SIX_BEAM_UNUSABLE_STOP_RATE = 0.50

ALLOWED_LAYERS = (
    "TOP",
    "BOTTOM",
    "SIDE",
    "STIRRUP",
    "SPACER",
    "SUPPORT_TOP_ZONE",
    "SUPPORT_BOTTOM_ZONE",
    "UNKNOWN",
)
ALLOWED_ROLES = ("MAIN", "EXTRA", "STIRRUP", "SPACER", "UNKNOWN")
ALLOWED_SCOPES = ("FULL_SPAN", "LEFT_SUPPORT", "RIGHT_SUPPORT", "BOTH_SUPPORTS", "UNKNOWN")
FORBIDDEN_CLAUDE_FIELDS = (
    "recover",
    "production_action",
    "steel_quantity",
    "weight",
    "BBS",
    "bbs",
    "cut_length",
    "workbook",
    "estimator_kg",
    "steel_weight",
)

# Reporting / regression / benchmark controls only. Never imported by gate/runtime.
REPORT_BLANK_BEAMS = ("B32", "B33", "B34", "B35", "B36", "B37", "B38", "B39")
REPORT_CLIP_BEAMS = ("B19", "B24", "B24A", "B152", "B176")
REPORT_QUALITY_BEAMS = ("B26", "B68A", "B69", "B70", "B99", "B99A")
REPORT_BENCHMARK_BEAMS = (
    ("Fourth", "B141"),
    ("Fourth", "B66"),
    ("Fourth", "B161"),
    ("Fifth", "B128"),
    ("Fifth", "B55"),
    ("Fifth", "B65"),
)
