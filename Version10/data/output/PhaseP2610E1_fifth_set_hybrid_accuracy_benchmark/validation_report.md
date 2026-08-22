# P2.6.10-E.1 — Fifth Set Hybrid Architecture Accuracy Benchmark & Performance Report

MODEL_VERSION: 10.11.22
GATE: P2610E1_FIFTH_SET_HYBRID_ARCHITECTURE_ACCURACY_BENCHMARK_V1_0
DECISION: PASS_WITH_LIMITATIONS

Standalone Fifth Set benchmark of the **current hybrid architecture**.
No historical comparison. No other drawing sets.

Hybrid semantic authority: Claude Vision preferred after validation (D.1 contract).
Deterministic engineering authority: geometry, cut length, development length, spacers, stirrup engineering, steel calculation.

- LIVE_CLAUDE_CALL = False
- PRODUCTION_WRITE = False
- execution_mode = OFFLINE_REPLAY

## EXECUTIVE SUMMARY

| KPI | result |
|---|---:|
| Beam identification | 76.47% |
| Bar identification | 36.68% |
| Correct of detected bars | 35.58% |
| Diameter identification | 74.34% |
| Steel accuracy | 48.00% |
| Overall accuracy | 49.18% |

- GT beams: 187 · detected: 143
- GT bars: 1456 · identified: 534 · MATCH: 190
- Hybrid kg: 28219.705 · Benchmark kg: 58796.332 · abs error kg: 30576.627

## 1. FIFTH SET PERFORMANCE

| KPI | Raw calculation | Result |
|---|---|---:|
| Beam identification | 143 / 187 × 100 | 76.47% |
| Bar identification | 534 / 1456 × 100 | 36.68% |
| Correct of detected | 190 / 534 × 100 | 35.58% |
| Diameter identification | 397 / 534 × 100 | 74.34% |
| Steel accuracy | `max(0, 100 - abs(model_kg - benchmark_kg) / benchmark_kg * 100)` | 48.00% |
| Overall accuracy | mean of four KPIs above excluding diameter | 49.18% |

## 2. WHAT THE KPIs MEAN

Beam identification: what share of estimator beams are present in the hybrid model.
Bar identification: what share of estimator bars are paired to a model bar (QA.2A BarMatcher).
Correct of detected: of paired bars, how many are full MATCH (role + diameter + quantity).
Steel accuracy: QA.2A metric8 on total kg.
Overall: mean of beam ID, bar ID, correct-of-detected, and steel accuracy.

## 3. BAR INTERPRETATION PERFORMANCE

{
  "MATCH": 190,
  "WRONG_ROLE": 25,
  "WRONG_QUANTITY": 159,
  "MISSING": 922,
  "WRONG_DIAMETER": 137,
  "PARTIAL_MATCH": 23,
  "ACCEPTABLE_EXTRA": 24,
  "EXTRA": 34
}

## 4. DIAMETER PERFORMANCE

| diameter | estimator kg | hybrid kg | difference kg | difference % |
|---|---:|---:|---:|---:|
| Y1 | 0.000 | 0.000 | 0.000 | 0.00 |
| Y8 | 1561.051 | 1067.239 | -493.812 | 31.63 |
| Y10 | 9375.228 | 4378.097 | -4997.131 | 53.30 |
| Y12 | 9171.753 | 2696.752 | -6475.001 | 70.60 |
| Y16 | 2871.897 | 1405.991 | -1465.906 | 51.04 |
| Y20 | 12026.043 | 5220.985 | -6805.058 | 56.59 |
| Y25 | 22638.393 | 11779.509 | -10858.884 | 47.97 |
| Y32 | 1151.967 | 1671.131 | 519.164 | 45.07 |

## 5. STEEL QUANTITY PERFORMANCE

- Hybrid total kg: 28219.705
- Benchmark kg: 58796.332
- Absolute difference kg: 30576.627
- Absolute error %: 52.00
- Steel accuracy %: 48.00
- Formula: `max(0, 100 - abs(model_kg - benchmark_kg) / benchmark_kg * 100)`
- Source: PhaseQA.2A_ground_truth_benchmark.metrics_engine.MetricsEngine._steel / QA.2A metric8

## 6. HYBRID ARCHITECTURE ANALYSIS

Vision preferred (after D.1 validation): target, layer, physical groups, bar count, diameter, specification, MAIN/EXTRA, support scope, stirrup identification.
Deterministic: geometry, cut length, development length, hooks/bends, spacers, stirrup engineering, piece generation, weight.
Vision usable beams this run: 0 (offline replay).

## 7. ERROR BREAKDOWN

Semantic interpretation errors:
[
  {
    "code": "MISSED_REINFORCEMENT_GROUPS",
    "count": 922
  },
  {
    "code": "WRONG_BAR_COUNT",
    "count": 159
  },
  {
    "code": "WRONG_DIAMETER",
    "count": 137
  },
  {
    "code": "MISSED_BEAMS",
    "count": 44
  },
  {
    "code": "SPURIOUS",
    "count": 34
  },
  {
    "code": "WRONG_MAIN_EXTRA_ROLE",
    "count": 25
  },
  {
    "code": "PARTIAL_SEMANTIC_MATCH",
    "count": 23
  }
]

Engineering calculation errors:
[
  {
    "code": "SPACER_ZERO",
    "count": 57
  },
  {
    "code": "STIRRUP_ENGINEERING_UNAVAILABLE",
    "count": 34
  }
]

## 8. HYBRID PROVENANCE SUMMARY (coverage, not accuracy)

{
  "label": "PROVENANCE_COVERAGE_NOT_ACCURACY",
  "field_counts": {
    "VISION": 0,
    "DETERMINISTIC": 2244,
    "FALLBACK": 0,
    "UNRESOLVED": 0,
    "WITHHELD": 0
  },
  "field_percent": {
    "VISION": 0.0,
    "DETERMINISTIC": 100.0,
    "FALLBACK": 0.0,
    "UNRESOLVED": 0.0,
    "WITHHELD": 0.0
  },
  "beam_kinds": {
    "HYBRID": 0,
    "FALLBACK": 143,
    "DETERMINISTIC": 0
  },
  "withheld_groups": 0,
  "unresolved_samples": [],
  "total_semantic_fields": 2244
}

## 9. CURRENT MODEL STATUS

This is a benchmark of the current hybrid architecture on the Fifth Set only.
It does not represent Second, Third, Fourth, or Sixth Sets, all-set generalization, or production readiness.
No historical comparison is generated.

## 10. METHODOLOGY AND LIMITATIONS

- truth source: ESTIMATOR_EXCEL
- mode: OFFLINE_REPLAY
- vision usable: 0 scanned=73 api_failed=16 other_set_skipped=57
- withheld ambiguity groups: 0
- formulas: beam/bar = QA.2A matchers; steel = QA.2A metric8; overall = QA.2A/QA.3.0 four-KPI mean

- unit tests: 31/31
- fingerprints unchanged: True
- production mutation: 0
