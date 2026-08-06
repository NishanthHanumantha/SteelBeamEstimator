# Execution Summary — Phase QA.3.0

- MODEL_VERSION: 10.0.0
- Generated: 2026-08-06T15:04:26.701866+00:00
- Overall elapsed (s): 1229.45
- Production elapsed (s): 1146.47
- Benchmark elapsed (s): 75.78
- QA overall_pass: True

## Drawing sets

- Fourth Set Drawings (Fourth): success=True reuse=False run=qa2_Fourth_Set_Drawings_20260806_121946 elapsed=1.32s
- Fifth Set Drawings (Fifth): success=True reuse=False run=qa2_Fifth_Set_Drawings_20260806_142822 elapsed=9979.18s
- Sixth Set Drawings (Sixth): success=True reuse=False run=qa2_Sixth_Set_Drawings_20260806_171449 elapsed=1137.86s

## Overall metrics

- Beam Detection: 82.95%
- Bar Detection: 46.04%
- Bar Matching: 36.74%
- Steel Accuracy: 72.21%
- Overall Accuracy: 59.48%
- Total beams (estimator GT): 475

## Top engineering failure categories

- Missing bars: 2235
- Diameter mismatch: 356
- Extra bars: 255
- Ownership issues: 105
- Missing beams: 81

## Estimator Excel policy

- Estimator Output Excel opened during production: **NO**
- Estimator Output Excel opened during benchmark: **YES**

Discovered unseen targets: ['Fifth Set Drawings', 'Fourth Set Drawings', 'Sixth Set Drawings']
