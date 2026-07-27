"""
PhaseR2.1B — Engineering Semantic Interpreter
MODEL_VERSION: 7.11.0

Converts parsed reinforcement notation into structured EngineeringSemanticObject
before EngineeringBarModel generation. Uses the R.2.1A Semantic Dictionary as the
single source of truth.

Pipeline position:
  R.2.1A Semantic Dictionary
  ↓
  R.2.1B Semantic Interpreter   ← this phase
  ↓
  EngineeringBarBuilder
  ↓
  EngineeringBarModel
"""

MODEL_VERSION = "7.11.0"
PHASE_ID = "R.2.1B"
