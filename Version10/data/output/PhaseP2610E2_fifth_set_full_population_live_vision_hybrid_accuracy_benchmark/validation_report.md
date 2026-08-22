# P2.6.10-E.2 — Fifth Set Full-Population Live Vision Hybrid Accuracy Benchmark

MODEL_VERSION: 10.11.23
GATE: P2610E2_FIFTH_SET_FULL_POPULATION_LIVE_VISION_HYBRID_ACCURACY_BENCHMARK_V1_0
DECISION: PASS_WITH_LIMITATIONS
LIVE_COMPLETION: COMPLETE_LIVE_BENCHMARK
MODE: LIVE_BENCHMARK

Standalone Fifth Set live-Vision hybrid benchmark. No historical comparison.
PRODUCTION_WRITE = False

## 1. MODEL VERSION
10.11.23

## 2. GATE
P2610E2_FIFTH_SET_FULL_POPULATION_LIVE_VISION_HYBRID_ACCURACY_BENCHMARK_V1_0

## 3. FINAL DECISION
PASS_WITH_LIMITATIONS
COMPLETE_LIVE_BENCHMARK

## 4. POPULATION DISCOVERY
{
  "discovered_model_beam_count": 143,
  "discovered_estimator_beam_count": 187,
  "matched_benchmark_population": 143,
  "discovery_method": "WEB_RUN_NAME_TOKEN"
}

## 5. VISION COVERAGE
{
  "VISION_READY": 143,
  "VISION_READY_WITH_LIMITATIONS": 0,
  "VISION_NOT_READY": 0,
  "VISION_REVIEW_ONLY": 0,
  "VISION_ELIGIBLE": 143,
  "VISION_BLOCKED_NOT_READY": 0,
  "visual_source_available": 143,
  "claude_attempted": 143,
  "api_success": 143,
  "api_failed": 0,
  "schema_valid": 143,
  "semantic_usable": 143
}

## 6. EXECUTION PROVENANCE
{
  "hybrid_count": 143,
  "fallback_count": 0,
  "hybrid_percent": 100.0,
  "fallback_percent": 0.0,
  "VISION_NEW_LIVE_CALL": 135,
  "VISION_RETRIED_AFTER_HISTORICAL_FAILURE": 8
}

## 7–13. ACCURACY (HYBRID / FALLBACK / FULL)

| cohort | beam % | bar % | correct % | diameter % | steel % | overall % | kg model | kg bench |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HYBRID_ONLY | 98.62 | 51.81 | 36.89 | 76.75 | 67.82 | 63.78 | 27977.137 | 41250.823 |
| FALLBACK_ONLY | — | — | — | — | — | — | — | — |
| FULL_POPULATION | 76.47 | 39.29 | 36.89 | 76.75 | 47.58 | 50.06 | 27977.137 | 58796.332 |

## 14. SEMANTIC ERROR TAXONOMY
{
  "FULL_POPULATION": {
    "MATCH": 211,
    "WRONG_QUANTITY": 164,
    "MISSING": 884,
    "WRONG_DIAMETER": 133,
    "PARTIAL_MATCH": 31,
    "WRONG_ROLE": 33,
    "EXTRA": 50,
    "ACCEPTABLE_EXTRA": 23
  },
  "HYBRID_ONLY": {
    "MATCH": 211,
    "WRONG_QUANTITY": 164,
    "MISSING": 532,
    "WRONG_DIAMETER": 133,
    "PARTIAL_MATCH": 31,
    "WRONG_ROLE": 33,
    "EXTRA": 50,
    "ACCEPTABLE_EXTRA": 23
  },
  "FALLBACK_ONLY": null
}

## 15. ENGINEERING ERROR SUMMARY
{
  "kind": "ENGINEERING_CALCULATION_ERROR",
  "counts": {
    "CUT_LENGTH_DERIVED_FALLBACK": 53,
    "CUT_LENGTH_UNAVAILABLE": 0,
    "STIRRUP_ENGINEERING_UNAVAILABLE": 34,
    "PARTIAL_CALCULATION": 23,
    "INCOMPATIBLE": 0,
    "SPACER_ZERO": 57
  },
  "ranked": [
    {
      "code": "SPACER_ZERO",
      "count": 57
    },
    {
      "code": "CUT_LENGTH_DERIVED_FALLBACK",
      "count": 53
    },
    {
      "code": "STIRRUP_ENGINEERING_UNAVAILABLE",
      "count": 34
    },
    {
      "code": "PARTIAL_CALCULATION",
      "count": 23
    }
  ],
  "note": "Engineering counts are calculation-trace based, not GT identity matches."
}

## 16. STIRRUP PERFORMANCE
{
  "semantic_identification_authority": "VISION_PREFERRED",
  "engineering_calculation_authority": "DETERMINISTIC_ENGINEERING",
  "identification_conflicts": 0,
  "engineering_unavailable_beams": 34,
  "hybrid_stirrup_kg": 8018.8975,
  "gt_match": 31,
  "gt_missing": 415,
  "gt_other_errors": 91
}

## 17. SPACER CONTRIBUTION
{
  "authority": "DETERMINISTIC_ONLY",
  "vision_matched": false,
  "weight_kg": 422.1536,
  "beams_with_spacers": 86,
  "group_count": 104
}

## 18. HYBRID PROVENANCE (coverage, not accuracy)
{
  "label": "PROVENANCE_COVERAGE_NOT_ACCURACY",
  "field_counts": {
    "VISION": 1914,
    "DETERMINISTIC": 588,
    "FALLBACK": 255,
    "UNRESOLVED": 45,
    "WITHHELD": 0
  },
  "field_percent": {
    "VISION": 68.31,
    "DETERMINISTIC": 20.99,
    "FALLBACK": 9.1,
    "UNRESOLVED": 1.61,
    "WITHHELD": 0.0
  },
  "beam_kinds": {
    "HYBRID": 143,
    "FALLBACK": 0,
    "DETERMINISTIC": 0
  },
  "withheld_groups": 8,
  "unresolved_samples": [
    {
      "beam_id": "B122",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B129",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B129",
      "group_id": "G2",
      "field": "specification"
    },
    {
      "beam_id": "B145",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B146",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B146",
      "group_id": "G3",
      "field": "specification"
    },
    {
      "beam_id": "B146",
      "group_id": "G3",
      "field": "support_scope"
    },
    {
      "beam_id": "B169",
      "group_id": "G4",
      "field": "layer"
    },
    {
      "beam_id": "B169",
      "group_id": "G4",
      "field": "bar_count"
    },
    {
      "beam_id": "B169",
      "group_id": "G4",
      "field": "diameter"
    },
    {
      "beam_id": "B169",
      "group_id": "G4",
      "field": "specification"
    },
    {
      "beam_id": "B170",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B170",
      "group_id": "G3",
      "field": "specification"
    },
    {
      "beam_id": "B170",
      "group_id": "G3",
      "field": "support_scope"
    },
    {
      "beam_id": "B177",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B181",
      "group_id": "G5",
      "field": "layer"
    },
    {
      "beam_id": "B181",
      "group_id": "G5",
      "field": "bar_count"
    },
    {
      "beam_id": "B181",
      "group_id": "G5",
      "field": "support_scope"
    },
    {
      "beam_id": "B45",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B63",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B68",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B68",
      "group_id": "G2",
      "field": "specification"
    },
    {
      "beam_id": "B70A",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B70A",
      "group_id": "G3",
      "field": "bar_count"
    },
    {
      "beam_id": "B70A",
      "group_id": "G3",
      "field": "specification"
    },
    {
      "beam_id": "B73",
      "group_id": "G3",
      "field": "layer"
    },
    {
      "beam_id": "B73",
      "group_id": "G3",
      "field": "bar_count"
    },
    {
      "beam_id": "B73",
      "group_id": "G3",
      "field": "specification"
    },
    {
      "beam_id": "B78",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B78",
      "group_id": "G2",
      "field": "bar_count"
    },
    {
      "beam_id": "B78",
      "group_id": "G2",
      "field": "specification"
    },
    {
      "beam_id": "B79",
      "group_id": "G4",
      "field": "layer"
    },
    {
      "beam_id": "B79",
      "group_id": "G4",
      "field": "specification"
    },
    {
      "beam_id": "B92",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B97A",
      "group_id": "G2",
      "field": "layer"
    },
    {
      "beam_id": "B97A",
      "group_id": "G2",
      "field": "specification"
    },
    {
      "beam_id": "B97A",
      "group_id": "G2",
      "field": "support_scope"
    },
    {
      "beam_id": "B97A",
      "group_id": "G4",
      "field": "layer"
    },
    {
      "beam_id": "B97A",
      "group_id": "G4",
      "field": "role"
    },
    {
      "beam_id": "B97A",
      "group_id": "G4",
      "field": "specification"
    },
    {
      "beam_id": "B97A",
      "group_id": "G4",
      "field": "support_scope"
    },
    {
      "beam_id": "B97A",
      "group_id": "G5",
      "field": "layer"
    },
    {
      "beam_id": "B97A",
      "group_id": "G5",
      "field": "role"
    },
    {
      "beam_id": "B97A",
      "group_id": "G5",
      "field": "specification"
    },
    {
      "beam_id": "B97A",
      "group_id": "G5",
      "field": "support_scope"
    }
  ],
  "total_semantic_fields": 2802
}

## 19. AMBIGUOUS / WITHHELD
{
  "withheld_groups": 8,
  "forced_resolutions": 0
}

## 20. VISION FAILURE ANALYSIS
{
  "counts": {
    "API_FAILED": 0,
    "SCHEMA_FAILED": 0,
    "SEMANTIC_UNUSABLE": 0,
    "TARGET_NOT_IDENTIFIED": 0,
    "VISUAL_NOT_READY": 0,
    "OTHER": 0
  },
  "historical_api_recovered": 8,
  "note": "Recovered historical API failures are not counted as current permanent failures."
}

## 21. COST / EXECUTION
{
  "attempted": 143,
  "api_success": 143,
  "api_failed": 0,
  "schema_valid": 143,
  "semantic_usable": 143,
  "retries": 0,
  "reused": 0,
  "historical_retried_recovered": 8,
  "input_tokens": 420680,
  "output_tokens": 86796
}

## 22. METHODOLOGY
QA.2A BeamMatcher, BarMatcher, MetricsEngine metric8, QA.3.0 four-KPI overall mean. Diameter excluded from overall.
Ground truth source: ESTIMATOR_EXCEL. Workbook mapping may not perfectly represent physical drawing interpretation.

## 27. LIMITATIONS
[
  "ESTIMATOR_WORKBOOK_MAPPING_LIMITATION",
  "STIRRUP_ENGINEERING_UNAVAILABLE",
  "AMBIGUOUS_WITHHELD"
]

## 28. CONCLUSION
HYBRID coverage is 100.0% of executed model beams. Subset overall scores are not both applicable; full-population overall is 50.06.
