# P2.6.10-D.4 — Shadow Hybrid Engineering Calculation & Accuracy Benchmark

MODEL_VERSION: 10.11.22
GATE: P2610D4_SHADOW_HYBRID_ENGINEERING_CALCULATION_ACCURACY_BENCHMARK_V1_0
DECISION: PASS_WITH_LIMITATIONS

SHADOW ONLY. Hybrid engineering calculation versus frozen deterministic baseline and estimator truth.
Weight formula: `W = (pi * d^2 / 4) * L * qty * 7850 / 1e9` (PieceGeometry / V.B.1).
Error formula: `abs(predicted - benchmark) / benchmark * 100` (QA.2A metric8 / P258).
Accuracy formula: `max(0, 100 - weight_error_percent)`.
Accuracy improvement delta = hybrid_accuracy_pct − deterministic_accuracy_pct (percentage points).
Do not treat ENGINEERING_BINDING_COVERAGE as accuracy. This phase reports steel-weight accuracy only where benchmark truth exists.

- LIVE_CLAUDE_CALL = False
- PRODUCTION_WRITE = False

## TABLE A — POPULATION

| metric | count |
|---|---|
| total discovered | 16 |
| SHADOW_COMPLETE | 15 |
| SHADOW_PARTIAL | 0 |
| SHADOW_AMBIGUOUS | 1 |
| SHADOW_INCOMPATIBLE | 0 |
| NO_BENCHMARK_TRUTH | 1 |

## TABLE B — WEIGHT COMPARISON

| beam | hybrid kg | deterministic kg | benchmark kg | hybrid error % | deterministic error % | winner |
|---|---:|---:|---:|---:|---:|---|
| B100 | 129.256 | 133.588 | 168.475 | 23.280 | 20.710 | DETERMINISTIC |
| B100A | 215.633 | 130.335 | 202.158 | 6.670 | 35.530 | HYBRID |
| B103 | 139.330 | 163.255 | 112.536 | 23.810 | 45.070 | HYBRID |
| B119 | 221.488 | 228.519 | 384.625 | 42.410 | 40.590 | DETERMINISTIC |
| B128 | 298.124 | 270.668 | 469.276 | 36.470 | 42.320 | HYBRID |
| B129 | 197.643 | 136.882 | 149.376 | 32.310 | 8.360 | DETERMINISTIC |
| B133 | 273.616 | 301.098 | 310.829 | 11.970 | 3.130 | DETERMINISTIC |
| B139 | 29.831 | 39.932 | — | — | — | NO_BENCHMARK_TRUTH |
| B141 | 179.627 | 68.263 | 90.590 | 98.290 | 24.650 | DETERMINISTIC |
| B161 | 344.500 | 405.181 | 325.176 | 5.940 | 24.600 | HYBRID |
| B17 | 86.312 | 124.169 | 46.676 | 84.920 | 166.020 | HYBRID |
| B46 | 63.528 | 61.160 | 96.909 | 34.450 | 36.890 | HYBRID |
| B55 | 170.953 | 214.412 | 221.452 | 22.800 | 3.180 | DETERMINISTIC |
| B65 | 265.241 | 280.198 | 222.693 | 19.110 | 25.820 | HYBRID |
| B66 | 281.680 | 222.804 | 183.888 | 53.180 | 21.160 | DETERMINISTIC |
| B68 | 120.934 | 113.764 | 91.600 | 32.020 | 24.200 | DETERMINISTIC |

## TABLE C — POPULATION TOTALS (beams with benchmark truth only)

| metric | value |
|---|---|
| hybrid total kg | 2987.865 |
| deterministic total kg | 2854.296 |
| benchmark total kg | 3076.259 |
| hybrid absolute error kg | 88.394 |
| deterministic absolute error kg | 221.963 |
| hybrid error % | 2.870 |
| deterministic error % | 7.220 |
| hybrid accuracy % | 97.130 |
| deterministic accuracy % | 92.780 |
| accuracy improvement delta (pp) | 4.350 |

## TABLE D — DIAMETER PERFORMANCE

| diameter | hybrid predicted kg | deterministic predicted kg | benchmark kg | hybrid error % | deterministic error % |
|---|---:|---:|---:|---:|---:|
| Y8 | 275.428 | 235.401 | 377.958 | 27.130 | 37.720 |
| Y10 | 269.362 | 224.296 | 417.638 | 35.500 | 46.290 |
| Y12 | 75.002 | 68.752 | 267.486 | 71.960 | 74.300 |
| Y16 | 429.341 | 632.365 | 310.309 | 38.360 | 103.790 |
| Y20 | 1269.017 | 876.220 | 1084.837 | 16.980 | 19.230 |
| Y25 | 669.716 | 817.263 | 618.031 | 8.360 | 32.240 |

## TABLE E — CONTRIBUTION ANALYSIS

| category | count |
|---|---:|
| hybrid improvements | 7 |
| hybrid regressions | 8 |
| ambiguous withheld beams | 1 |
| AMBIGUOUS_GROUP_WITHHELD | 1 |
| DETERMINISTIC_CUT_LENGTH_CONTRIBUTION | 15 |
| DETERMINISTIC_GEOMETRY_CONTRIBUTION | 9 |
| DETERMINISTIC_ONLY_PRESERVED | 4 |
| DETERMINISTIC_SPACER_CONTRIBUTION | 9 |
| DETERMINISTIC_STIRRUP_ENGINEERING_CONTRIBUTION | 11 |
| POSSIBLE_DUPLICATE_UNMERGED | 2 |
| VISION_BAR_COUNT_CORRECTION | 5 |
| VISION_DIAMETER_CORRECTION | 5 |
| VISION_GROUP_RECOVERY | 8 |
| VISION_LAYER_CORRECTION | 7 |
| VISION_ROLE_CORRECTION | 5 |
| VISION_SPECIFICATION_CORRECTION | 15 |

outcomes: `{"HYBRID_REGRESSION": 8, "HYBRID_IMPROVEMENT": 7, "NO_BENCHMARK_TRUTH": 1}`

## TABLE F — AMBIGUITY

| beam | group | reason | calculated | completeness impact |
|---|---|---|---|---|
| B55 | VG2 | CALCULATION_WITHHELD_AMBIGUITY | False | withheld from beam total |

## Tests / firewall

- D.4 unit tests: 28/28 success=True
- anti-hardcoding: True
- fingerprints unchanged: True
- production mutation: 0

No production interpretation change. No R1.3 / SI / steel / BBS / workbook mutation.
