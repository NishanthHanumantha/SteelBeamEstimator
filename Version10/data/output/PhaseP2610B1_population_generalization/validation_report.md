# P2.6.10-B.1 — All-Beam Population Generalization & Anti-Hardcoding Validation

Shadow / validation only. Fourth drawing set only. No Claude Vision.

**Phase:** P2.6.10-B.1
**Model version:** 10.11.12
**Gate version:** P2610B1_POPULATION_GENERALIZATION_ANTI_HARDCODING_V1_0
**STATUS:** PARTIAL
**DECISION:** PASS_WITH_LIMITATIONS — GENERALIZATION MOSTLY CONFIRMED, LIMITATIONS DOCUMENTED

## Population

- source DXF: `C:\Users\nishanth.h\SteelBeamEstimator\Test_Input\4th Set Drawings-Inizio_B1\reinforcement\SE-204_BASEMENT-01 FLOOR BEAM REINFORCEMENT DETAILS(SH-01 TO 03).dxf`
- title hits: 160
- unique discovered beams: 135
- collapsed duplicate titles: 15
- context crops: 135
- detail crops: 135
- fully complete: 120
- incomplete: 15
- skipped: 0
- render failures: 0
- completeness rate: 0.8888888888888888

## Failures

- B191: VERTICAL_TRUNCATION, HORIZONTAL_TRUNCATION
- B176: HORIZONTAL_TRUNCATION
- B150: VERTICAL_TRUNCATION
- B123: HORIZONTAL_TRUNCATION
- B101: HORIZONTAL_TRUNCATION
- B99: HORIZONTAL_TRUNCATION
- B119: HORIZONTAL_TRUNCATION, VERTICAL_TRUNCATION
- B120: HORIZONTAL_TRUNCATION
- B96: HORIZONTAL_TRUNCATION
- B63: VERTICAL_TRUNCATION
- B48: VERTICAL_TRUNCATION
- B29: HORIZONTAL_TRUNCATION
- B19: HORIZONTAL_TRUNCATION
- B22: HORIZONTAL_TRUNCATION
- B23: HORIZONTAL_TRUNCATION

## Anti-hardcoding

- source guard: PASS
- translation invariance: PASS
- DXF-copy translation: PASS
- spatial-distance robustness: PASS
- packed-sheet robustness: PASS

## Original six-beam regression

- Fourth/B141: complete=True
- Fourth/B66: complete=True
- Fourth/B161: complete=True
- Fifth/B128: complete=True
- Fifth/B55: complete=True
- Fifth/B65: complete=True

## Prior regressions

- P2.6.6: PASS
- P2.6.10-A: PASS
- P2.6.10-B: PASS
- P2.6.10-B.1 unit tests: 16/16 success=True

## Production firewall

- production mutation count: 0
- steel quantity delta: 0
- BBS delta: 0
- workbook delta: 0
- live Claude Vision calls: False

## Final decision

**PASS_WITH_LIMITATIONS — GENERALIZATION MOSTLY CONFIRMED, LIMITATIONS DOCUMENTED**

This phase does not authorize Claude Vision or production promotion.
