# Phase QA.3.2 — Ground Truth Crop Verification

MODEL_VERSION: `10.0.2`

Diagnostic-only validation of Manual Beam Comparison Crops used in QA.3.0.

## Constraints
- No engineering / ownership / rendering / crop / estimation changes
- Read-only consumption of QA.3.0 / Track1 artefacts

## Key paths
- Drawing set: `Fourth Set Drawings`
- Run root: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\web_runs\qa2_Fourth_Set_Drawings_20260806_121946`
- Reinforcement DXF: `C:\Users\nishanth.h\SteelBeamEstimator\Test_Input\Fourth Set Drawings\reinforcement\SE-204_BASEMENT-01 FLOOR BEAM REINFORCEMENT DETAILS(SH-01 TO 03).dxf`

## Headline result
- Categories A/B/C: `{'A': 0, 'B': 4, 'C': 7}`
- Dominant finding: `manual_crops_are_regenerated_tight_envelopes_not_true_autocad_gt`
- Baseline trustworthy: `False`

See `ExecutionSummary.md` and `GroundTruthDecisionMatrix.json`.
