"""
PhaseR2.1D — Evidence & Intent Hypothesis Engine
MODEL_VERSION: 7.12.1

Upgrades Phase R.2.1C EngineeringFacts with two new deterministic concepts:

  ObservableEvidence  — Structured capture of every observable drawing fact.
                        Contains NO engineering inference or assumptions.

  IntentHypothesis    — Deterministic ranked hypothesis replacing the unordered
                        intent_candidates list. Priority is sequential ordering,
                        NOT probability or confidence.

Philosophy:
  Observable Evidence → Engineering Facts → Ranked Intent Hypotheses → R.3 Geometry

This phase is the final geometry-independent stage before Phase R.3.
No geometry, support locations, span continuity, development length,
or engineering calculations are introduced here.

Pipeline position:
  R.2.1C Engineering Fact Normalization
  ↓
  R.2.1D Evidence & Intent Hypothesis Engine  ← this phase
  ↓
  R.3 Geometry Context Engine (future)
  ↓
  Engineering Intent Resolver (future)
"""

MODEL_VERSION = "7.12.1"
PHASE_ID      = "R.2.1D"
