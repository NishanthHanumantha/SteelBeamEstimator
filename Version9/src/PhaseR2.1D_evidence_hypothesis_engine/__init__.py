"""
PhaseR2.1D — Evidence & Intent Hypothesis Engine
MODEL_VERSION: 8.9.1

Upgrades Phase R.2.1C EngineeringFacts with two new deterministic concepts:

  ObservableEvidence  — Structured capture of every observable drawing fact.
                        Contains NO engineering inference or assumptions.

  IntentHypothesis    — Deterministic ranked hypothesis replacing the unordered
                        intent_candidates list. Priority is sequential ordering,
                        NOT probability or confidence.

Pipeline position (web D.5.2):
  R.2.1C Engineering Fact Normalization
  ↓
  R.2.1D Evidence & Intent Hypothesis Engine  ← this phase
  ↓
  L.2.2 / R.3 (later milestones)
"""

MODEL_VERSION = "8.9.1"
PHASE_ID = "R.2.1D"
