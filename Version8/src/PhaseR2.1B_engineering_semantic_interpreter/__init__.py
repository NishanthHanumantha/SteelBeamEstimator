"""
PhaseR2.1B — Engineering Semantic Interpreter
MODEL_VERSION: 8.9.0

Converts parsed reinforcement notation into structured EngineeringSemanticObject
before EngineeringBarModel generation. Uses the R.2.1A Semantic Dictionary as the
single source of truth.

Pipeline position (web D.5.1):
  R.1 annotations
  ↓
  R.2.1B Semantic Interpreter   ← this phase
  ↓
  R.2.1C Fact Normalization
"""

MODEL_VERSION = "8.9.0"
PHASE_ID = "R.2.1B"
