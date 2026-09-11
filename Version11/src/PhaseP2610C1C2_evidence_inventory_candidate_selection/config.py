"""
P2.6.10-C.1+C.2 — Evidence Inventory & Preference-Preserving Candidate Selection.
MODEL_VERSION: 10.11.15

SHADOW ONLY. Read-only over B.1/B.2/B.3 artefacts.
Does not render, recover, crop, or call Claude Vision.

DESIGN NOTE
-----------
Candidate discovery (actual repo paths):
  B.1 context/detail: data/output/PhaseP2610B1_population_generalization/{context,detail}/{id}.png
                      + validation/{id}.json completeness
  B.2 context/detail: .../PhaseP2610B2_.../{context,detail}/final/{id}.png
                      + diagnostics/{id}.json
  B.3 unique renders: .../PhaseP2610B3_.../review/{id}/selected/{context,detail}.png
                      and review/{id}/b3_candidate/*.png
                      (only if the file exists and SHA differs from B.1)

Population: unique IDs from B.1 validation/*.json (135). No DXF load.

Evidence: reuse B.2 validate_render on existing PNGs + recorded phase diagnostics.
CLIP is not a critical failure. B.1 is retained unless the challenger is
non-critical AND (clears a baseline critical failure OR beats a material
score+foreground margin without coverage regression).

Thresholds live only in this module.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.15"
PHASE_ID = "P2.6.10-C.1+C.2"
PHASE_NAME = "Evidence Inventory & Preference-Preserving Candidate Selection"
OUTPUT_DIRNAME = "PhaseP2610C1C2_evidence_inventory_candidate_selection"
GATE_VERSION = "P2610C1C2_EVIDENCE_INVENTORY_CANDIDATE_SELECTION_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"
ENGINEERING_CHANGES = "NONE"
LIVE_VISION_CALLS = False

DRAWING_SET_KEY = "Fourth"
MODE_OFFLINE = "OFFLINE_VALIDATION"

SOURCE_B1 = "B.1"
SOURCE_B2 = "B.2"
SOURCE_B3 = "B.3"
PREFERRED_SOURCE = SOURCE_B1

# Reporting / regression identifiers only. Never imported by inventory or selector.
REPORT_BLANK_BEAMS = ("B32", "B33", "B34", "B35", "B36", "B37", "B38", "B39")
REPORT_CLIP_BEAMS = ("B19", "B24", "B24A", "B152", "B176")
REPORT_QUALITY_BEAMS = ("B26", "B68A", "B69A", "B70", "B99", "B99A")
REPORT_ALIAS_DISCOVERED = (("B69A", "B69"),)

CRITICAL_STATUSES = (
    "EMPTY_RENDER",
    "BLACK_RENDER",
    "LOW_INFORMATION_RENDER",
    "RENDER_MISSING",
)

MATERIAL_SCORE_MARGIN = 0.35
MIN_FOREGROUND_GAIN = 0.020
MAX_COVERAGE_REGRESSION = 0.080

P2610B1_OUTPUT_DIRNAME = "PhaseP2610B1_population_generalization"
P2610B2_OUTPUT_DIRNAME = "PhaseP2610B2_render_quality_directional_recovery"
P2610B3_OUTPUT_DIRNAME = "PhaseP2610B3_target_anchor_geometry_context_recovery"
P2610B_OUTPUT_DIRNAME = "PhaseP2610B_adaptive_beam_detail_crop"
P2610A_OUTPUT_DIRNAME = "PhaseP2610A_beam_region_crop_audit"
P266_OUTPUT_DIRNAME = "PhaseP266_semantic_longitudinal_resolver"
