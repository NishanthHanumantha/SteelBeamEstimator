"""
Phase M.2 — Deterministic Spacer Bar Rule Engine
MODEL_VERSION: 9.2.0

Pure estimation-team rule: emit SPACER_BAR where ≥2 longitudinal bar
groups coexist on the same face. Hardcoded Ø25 @ 1000 mm.

Does NOT modify discovery, association, or role classification.
"""

MODEL_VERSION = "9.2.0"
PHASE = "M.2"
PHASE_NAME = "Deterministic Spacer Bar Rule Engine"
RULE_VERSION = "M.2"

__all__ = ["MODEL_VERSION", "PHASE", "PHASE_NAME", "RULE_VERSION"]
