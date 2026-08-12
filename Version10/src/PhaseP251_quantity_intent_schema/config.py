"""
Phase P2.5.1 — Quantity Intent Schema.
MODEL_VERSION: 10.6.4

Deterministic only. No Claude. No engineering mutations.
"""
from __future__ import annotations

MODEL_VERSION = "10.6.4"
PHASE_ID = "P2.5.1"
PHASE_NAME = "Quantity Intent Schema"
OUTPUT_DIRNAME = "PhaseP251_quantity_intent_schema"
SCOPE = "FOURTH_SET_ONLY"
MODE = "DETERMINISTIC_SCHEMA_ONLY"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "NONE"

# Consume P2.5.0 evidence packages (updated by P2.5.0.3/0.4 for OWN geometry)
P250_EVIDENCE_DIRNAME = "PhaseP250_beam_evidence_crop_qa"

# Quantity status
STATUS_EXPLICIT = "EXPLICIT"
STATUS_INFERRED = "INFERRED"
STATUS_COMPOSITE = "COMPOSITE"
STATUS_SPACING_BASED = "SPACING_BASED"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_INVALID = "INVALID"

# Quantity source
SOURCE_ANNOTATION_TEXT = "ANNOTATION_TEXT"
SOURCE_LEADER_CHAIN = "LEADER_CHAIN"
SOURCE_OWNED_GEOMETRY = "OWNED_GEOMETRY"
SOURCE_STIRRUP_PATTERN = "STIRRUP_PATTERN"
SOURCE_UNRESOLVED = "UNRESOLVED"

# Semantic types (aligned with T18 BarCallout / StirrupNote)
SEM_LONGITUDINAL_BAR = "LONGITUDINAL_BAR"
SEM_STIRRUP = "STIRRUP"
SEM_SIDE_FACE = "SIDE_FACE_REINFORCEMENT"
SEM_SPACER = "SPACER"
SEM_UNKNOWN = "UNKNOWN"

# Roles (existing project terminology)
ROLE_TOP_BAR = "TOP_BAR"
ROLE_BOTTOM_BAR = "BOTTOM_BAR"
ROLE_SIDE_FACE = "SIDE_FACE"
ROLE_STIRRUP = "STIRRUP"
ROLE_SPACER = "SPACER"
ROLE_UNKNOWN = "UNKNOWN"

VALIDATION_PASS = "PASS"
VALIDATION_FAIL = "FAIL"
VALIDATION_PARTIAL = "PARTIAL"

GOLDEN_B97A = {
    "beam_id": "B97A",
    "annotation_id": "ANN-d7128f62",
    "raw_text": "4-Y25",
    "quantity_value": 4,
    "diameter_value_mm": 25.0,
    "semantic_type": SEM_LONGITUDINAL_BAR,
    "role": ROLE_TOP_BAR,
    "leader_id": "LDR::E83C245B",
    "ownership_id": "OWN::B97A::1247FFF",
}
