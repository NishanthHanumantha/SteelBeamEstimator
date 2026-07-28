"""
PhaseR3 — Geometry Context Engine
MODEL_VERSION: 8.9.3

The bridge between semantic interpretation (R.2.x) and engineering intent
resolution (future).

R.3 answers ONLY:
  "Where is this reinforcement annotation located relative to the beam?"

Intent remains UNKNOWN throughout this phase.

Pipeline position (web D.5.4):
  R.2.1D + L.2.2
  ↓
  R.3 Geometry Context Engine  ← this phase
  ↓
  R.3.1 / downstream (later — D.5.5)
"""

MODEL_VERSION = "8.9.3"
PHASE_ID = "R.3"
