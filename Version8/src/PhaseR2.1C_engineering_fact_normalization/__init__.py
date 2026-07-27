"""
PhaseR2.1C — Engineering Fact Normalization Engine
MODEL_VERSION: 7.12.0

Removes premature engineering intent from R.2.1B semantic objects and
produces geometry-independent EngineeringFact records.

The only facts preserved are:
  - Role        (observable from annotation)
  - Placement   (observable from position zone)
  - Modifiers   (observable from text)
  - Quantity / Diameter / Grade / Spacing  (parsed from annotation)
  - Intent candidates  (possible intents, geometry required to resolve)

Intent is set to UNKNOWN — resolved by future R.3 Geometry Context Engine.

Pipeline position:
  R.2.1B Engineering Semantic Interpreter
  ↓
  R.2.1C Engineering Fact Normalization  ← this phase
  ↓
  R.3 Geometry Context Engine (future)
  ↓
  Engineering Intent Resolver (future)
"""

MODEL_VERSION = "7.12.0"
PHASE_ID = "R.2.1C"
