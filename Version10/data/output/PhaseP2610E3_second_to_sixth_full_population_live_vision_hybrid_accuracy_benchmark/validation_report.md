# P2.6.10-E.3 — Second-to-Sixth Set Full-Population Live Vision Hybrid Accuracy Benchmark & Performance Report

MODEL_VERSION: 10.11.24
GATE: P2610E3_SECOND_TO_SIXTH_FULL_POPULATION_LIVE_VISION_HYBRID_ACCURACY_BENCHMARK_AND_REPORT_V1_0
DECISION: PASS_WITH_LIMITATIONS
MODE: LIVE_BENCHMARK
PRODUCTION_WRITE = False

## TABLE A — POPULATION BY SET

| Set | Model beams | GT beams | Matched | Unmatched model | Unmatched GT |
|---|---|---|---|---|---|
| Second | 65 | 67 | 64 | 1 | 2 |
| Third | 61 | 63 | 57 | 4 | 4 |
| Fourth | 118 | 143 | 112 | 6 | 22 |
| Fifth | 143 | 187 | 143 | 0 | 42 |
| Sixth | 143 | 145 | 139 | 4 | 6 |

## TABLE B — VISION EXECUTION

| Set | Eligible | Attempted | New live | Reused | Retried | API success | Schema valid | Usable | Hybrid | Fallback |
|---|---|---|---|---|---|---|---|---|---|---|
| Second | 63 | 63 | 63 | 0 | 0 | 63 | 63 | 63 | 63 | 2 |
| Third | 61 | 61 | 61 | 0 | 0 | 61 | 61 | 61 | 61 | 0 |
| Fourth | 76 | 76 | 76 | 0 | 0 | 76 | 76 | 76 | 76 | 42 |
| Fifth | 143 | 0 | 0 | 143 | 0 | 143 | 143 | 143 | 143 | 0 |
| Sixth | 143 | 143 | 143 | 0 | 0 | 143 | 143 | 143 | 143 | 0 |

## TABLE C — ACCURACY BY SET

| Set | Beam ID | Bar ID | Correct-of-detected | Diameter | Steel | Overall |
|---|---|---|---|---|---|---|
| Second | 95.52 | 65.28 | 31.35 | 78.97 | 87.95 | 70.03 |
| Third | 90.48 | 54.29 | 27.27 | 74.31 | 68.25 | 60.07 |
| Fourth | 78.32 | 40.43 | 41.32 | 75.26 | 54.29 | 53.59 |
| Fifth | 76.47 | 39.29 | 36.89 | 76.75 | 47.58 | 50.06 |
| Sixth | 95.86 | 59.83 | 39.38 | 81.85 | 83.18 | 69.56 |

## TABLE D — STEEL TOTALS

| Set | Model kg | Benchmark kg | Signed error | Absolute error | Steel accuracy |
|---|---|---|---|---|---|
| Second | 9163.346 | 10419.298 | -1255.952 | 1255.952 | 87.95 |
| Third | 10952.127 | 16046.150 | -5094.023 | 5094.023 | 68.25 |
| Fourth | 20166.844 | 37144.855 | -16978.011 | 16978.011 | 54.29 |
| Fifth | 27977.137 | 58796.332 | -30819.195 | 30819.195 | 47.58 |
| Sixth | 22045.667 | 26504.009 | -4458.342 | 4458.342 | 83.18 |

## TABLE E — POOLED SECOND–SIXTH

| KPI | Percent | Numerator | Denominator |
|---|---|---|---|
| Beam identification | 85.12 | 515.0 | 605.0 |
| Bar identification | 48.17 | 2008.0 | 4169.0 |
| Correct-of-detected | 36.50 | 733.0 | 2008.0 |
| Diameter | 77.84 | 1563.0 | 2008.0 |
| Steel/weight | 60.64 | 90305.121 | 148910.644 |
| Overall | 57.61 | mean of four pooled KPIs | diameter excluded |

## TABLE F — SEMANTIC ERROR TAXONOMY

| Code | Count |
|---|---|
| ACCEPTABLE_EXTRA | 89 |
| EXTRA | 183 |
| MATCH | 733 |
| MISSING | 2161 |
| PARTIAL_MATCH | 103 |
| WRONG_DIAMETER | 445 |
| WRONG_QUANTITY | 593 |
| WRONG_ROLE | 134 |

## TABLE G — ENGINEERING ERROR TAXONOMY

| Code | Count |
|---|---|
| CUT_LENGTH_DERIVED_FALLBACK | 188 |
| CUT_LENGTH_UNAVAILABLE | 0 |
| INCOMPATIBLE | 0 |
| PARTIAL_CALCULATION | 82 |
| SPACER_ZERO | 242 |
| STIRRUP_ENGINEERING_UNAVAILABLE | 69 |

## TABLE H — COST / EXECUTION

| Item | Value |
|---|---|
| New live | 343 |
| Reused | 143 |
| Retried | 0 |
| API failed | 0 |
| Input tokens | 1088060 |
| Output tokens | 213497 |
| Runtime s | 3854.94 |

## TABLE J — DIAMETER IDENTIFICATION (DETECTED BAR LINES)

| Diameter | GT bar lines | Detected | MATCH | WRONG_DIA | Diameter ID | Note |
|---|---|---|---|---|---|---|
| Ø8 | 358 | 152 | 32 | 3 | 98.03 | Usually right when found; many missing |
| Ø10 | 714 | 214 | 56 | 11 | 94.86 | Usually right when found; many missing |
| Ø12 | 573 | 207 | 68 | 28 | 86.47 | Usually right when found; many missing |
| Ø16 | 588 | 372 | 169 | 112 | 69.89 | Frequent diameter swaps |
| Ø20 | 784 | 436 | 193 | 155 | 64.45 | Frequent diameter swaps |
| Ø25 | 1097 | 616 | 210 | 130 | 78.90 |  |
| Ø32 | 26 | 11 | 5 | 6 | 45.45 | Low volume - percentage unstable |
| TOTAL scored Ø8-Ø32 | 4140 | 2008 | 733 | 445 | 77.84 | Pooled headline from raw counts |

QA.2A diameter_accuracy_pct is an alias of bar matching (MATCH / detected) and is not used. A detected bar is diameter-correct unless status is WRONG_DIAMETER. GT diameter is the estimator line diameter. Pooled % uses summed raw counts, not the average of set percentages. Diameter remains excluded from overall.


## TABLE K — DIAMETER-WISE STEEL QUANTITY

| Diameter | Estimated kg | Automated kg | Difference kg | Abs % diff | Quantity ratio |
|---|---|---|---|---|---|
| Ø8 | 6515.421 | 5051.185 | -1464.236 | 22.47 | 77.53 |
| Ø10 | 24555.441 | 14162.820 | -10392.621 | 42.32 | 57.68 |
| Ø12 | 22252.521 | 12721.515 | -9531.006 | 42.83 | 57.17 |
| Ø16 | 11598.150 | 7678.112 | -3920.038 | 33.80 | 66.20 |
| Ø20 | 35887.539 | 20505.869 | -15381.670 | 42.86 | 57.14 |
| Ø25 | 45293.831 | 28282.361 | -17011.470 | 37.56 | 62.44 |
| Ø32 | 2807.740 | 1901.463 | -906.277 | 32.28 | 67.72 |
| TOTAL | 148910.643 | 90303.325 | -58607.318 | 39.36 | 60.64 |

Quantity ratio = automated kg / estimated kg x 100. It is not accuracy. A ratio above 100% is an overestimate. This is not the same as diameter identification.


## TABLE I — SAFETY / IMMUTABILITY

| Item | Value |
|---|---|
| PRODUCTION_WRITE | False |
| ENGINEERING_CHANGES | NONE |
| production_mutation_delta | 0 |
| changed_keys | [] |
| LIVE_CLAUDE_CALL | True |