"""
PhaseR3 — Geometry Context Engine
MODEL_VERSION: 8.0.0

The bridge between semantic interpretation (R.2.x) and engineering intent
resolution (future R.4).

R.3 answers ONLY:
  "Where is this reinforcement annotation located relative to the beam?"

R.3 DOES NOT answer:
  "What does this reinforcement mean?"

Intent remains UNKNOWN throughout this phase.

Geometry evidence produced:
  - Beam axis (start/end/length/orientation)
  - Support locations (left/right, position fraction, support width)
  - Projection of annotation onto beam axis
  - Normalized position along beam span (0.0 = left end, 1.0 = right end)
  - Support zone membership
  - Span zone classification (SUPPORT / TRANSITION / MIDSPAN)
  - Extent evidence (observable position label — NOT engineering intent)

Pipeline position:
  R.2.1D Evidence & Intent Hypothesis Engine
  ↓
  R.3 Geometry Context Engine  ← this phase
  ↓
  R.4 Engineering Intent Resolver (future)
"""

MODEL_VERSION = "8.0.0"
PHASE_ID      = "R.3"
