"""
PhaseR2.1C — Engineering Fact Normalization Engine
MODEL_VERSION: 8.9.0

Removes premature engineering intent from R.2.1B semantic objects and
produces geometry-independent EngineeringFact records.

Pipeline position (web):
  R.2.1B Engineering Semantic Interpreter
  ↓
  R.2.1C Engineering Fact Normalization  ← this phase
  ↓
  R.2.1D (later) → R.3 (later)
"""

MODEL_VERSION = "8.9.0"
PHASE_ID = "R.2.1C"
