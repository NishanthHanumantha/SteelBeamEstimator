# Phase QA.3.3 — Ownership Explainability & Decision Trace Engine

MODEL_VERSION: `10.0.3`

Diagnostic-only instrumentation of Ownership decisions.
Does **not** modify discovery, scoring, conflict resolution, or rendering.

## Outputs
- `CandidateDiscovery.json` / `.xlsx`
- `OwnershipScores.json`
- `ConflictResolution.json`
- `EntityDecisionTrace.json`
- `OwnershipCoverage.json`
- `OwnershipFailureClassification.json`
- `OwnershipStatistics.json`
- Visual folders: `CandidateEnvelopeOverlays/`, `CompetingBeamOverlays/`, `DecisionFlowCharts/`

## Run
- Drawing set: `Fourth Set Drawings`
- Run root: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\web_runs\qa2_Fourth_Set_Drawings_20260806_121946`
- Dominant failure: `{'Conflict Resolution': 7, 'Mixed': 4}`

See `ExecutionSummary.md`.
