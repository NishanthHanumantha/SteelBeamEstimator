"""
PhaseM.1 — Engineering Vision Dataset Generator
MODEL_VERSION: 9.0.0

Generates a structured dataset from deterministic engineering pipeline outputs:
  - Beam images (PNG, vector-rendered from DXF)
  - Annotation JSON (from R.1 / R.1.3 deterministic labels)
  - Beam metadata
  - Visual previews (for quality inspection)
  - Dataset manifest
  - Validation report

This is a RESEARCH FOUNDATION phase.
It does NOT modify engineering logic, calculations, or production pipeline.
Version 8.9.5 remains the production baseline.
"""

MODEL_VERSION = "9.0.0"
PHASE         = "M.1"
PHASE_NAME    = "Engineering Vision Dataset Generator"
DATASET_SCHEMA_VERSION = "M.1.0"
