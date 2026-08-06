"""
Phase R.1 — Generalized Reinforcement Discovery & Interpretation Engine
MODEL_VERSION : 9.2.0
Type          : Core Engineering Pipeline

Reads the DXF reinforcement drawing, discovers EVERY beam detail block,
extracts all reinforcement annotations, classifies them deterministically,
and produces a complete BeamReinforcementModel for every beam.

NO hardcoded beam IDs. NO benchmark-specific assumptions. NO LLM.
Engineering logic is entirely rule-based and geometry-driven.

9.2.0: DIMENSION text-override discovery (enable_dimension_text_scan).

Pipeline:
  V.ROOT.1 → R.1 → L.2 → SI.0 → SI.1 → L.2.2 → L.2.1 → L.3 → V.B.1
"""

MODEL_VERSION = "9.2.0"
PHASE_ID      = "R.1"
PHASE_TITLE   = "Generalized Reinforcement Discovery & Interpretation Engine"

GENERALIZED_REINFORCEMENT_ERROR = type("GENERALIZED_REINFORCEMENT_ERROR", (Exception,), {})

__all__ = ["MODEL_VERSION", "PHASE_ID", "PHASE_TITLE", "GENERALIZED_REINFORCEMENT_ERROR"]
