# QA.3.4 Engineering Architecture Summary

MODEL_VERSION: `10.0.4`

## Principle
Read-only competition validation over QA.3.3 + T18 artefacts.
No ownership scores, registries, or engineering rules are modified.

## Pipeline
```
QA.3.3 traces/scores + T18 BeamOwnership
        ↓
Identity keys (id / leader handle / annotation text)
        ↓
OwnershipCompetitionRegistry
        ↓
Per-reject classification:
  OWNED_ELSEWHERE | LEADER_FAILURE | GEOMETRY_FAILURE |
  SEARCH_ENVELOPE_FAILURE | CONFLICT_FAILURE | UNKNOWN
        ↓
FinalState: OwnedElsewhere OR Dropped
        ↓
Regression gate vs QA.3.3 / T18 fingerprints
```

## Run context
- Drawing set: `Fourth Set Drawings`
- Run root: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\web_runs\qa2_Fourth_Set_Drawings_20260806_121946`
- QA.3.3 root: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA33_ownership_explainability`

## Headline
- Rejected: `123`
- Owned elsewhere: `19`
- Dropped: `104`
- Dominant QA.4.0 target: `dropped_entity_recovery`
