# P2.6.10-D.3 — Hybrid Engineering Binding & Deterministic Calculation Compatibility

MODEL_VERSION: 10.11.21
GATE: P2610D3_HYBRID_ENGINEERING_BINDING_COMPATIBILITY_V1_0
DECISION: PASS

SHADOW ONLY. Binding and compatibility. Not a calculation phase. Not accuracy.

- LIVE_CLAUDE_CALL = False
- PRODUCTION_WRITE = False
- ENGINEERING_CHANGES = NONE

## Required questions

1. Was the 16-beam population discovered successfully? **YES** (discovered=16, expected=16)
2. How many beams are ENGINEERING_COMPATIBLE? **15**
3. How many are partially compatible? **0**
4. How many are ambiguous? **1**
5. How many are incompatible? **0**
6. How many total groups were processed? **50**
7. How many groups are BOUND? **49**
8. How many are PARTIALLY_BOUND? **0**
9. How many are AMBIGUOUS? **1**
10. How many failed due to missing geometry? **0**
11. How many failed due to missing support references? **0**
12. How many failed due to missing rule references? **0**
13. How many are unsupported? **0**
14. Can Vision-only groups bind to deterministic engineering references? **YES** (vision-only=11, bound=11)
15. Are deterministic-only groups preserved? **YES** (count=5, bound=5)
16. Are ambiguous groups preserved without forced resolution? **YES** (unresolved=1)
17. Are possible duplicates preserved without merging? **YES** (preserved=4)
18. Is Vision-preferred diameter preserved? **YES**
19. Is Vision-preferred MAIN/EXTRA role preserved? **YES**
20. Are spacers still deterministic-only? **YES**
21. Is the Vision stirrup semantic / deterministic stirrup engineering split preserved? **YES**
22. Was any cut length calculated? **NO**
23. Was any development length calculated? **NO**
24. Was any steel weight calculated? **NO**
25. Was Claude called? **NO** (LIVE_CLAUDE_CALL=False)
26. Was production modified? **NO** (mutation_delta=0, steel_delta=0, bbs_delta=0, workbook_delta=0)
27. What is the engineering binding coverage? **1.0** — labelled ENGINEERING_BINDING_COVERAGE / COMPATIBILITY COVERAGE, **NOT ACCURACY**.
28. What are the top unresolved engineering-binding failure categories? `[["VISION_ONLY_RULE_FAMILY_BOUND_INSTANCE_UNAVAILABLE", 12], ["AMBIGUOUS", 1]]`
29. Based on the evidence, is the hybrid semantic object ready to enter a SHADOW calculation phase? **YES — evidence supports P2.6.10-D.4 shadow calculation preparation**

## Coverage (not accuracy)

{
  "label": "ENGINEERING_BINDING_COVERAGE",
  "note": "COMPATIBILITY COVERAGE, NOT ACCURACY. Not estimator truth. Not production promotion.",
  "formula": "fully_bound_required_references / total_required_references",
  "all_groups": 1.0,
  "matched_groups": 1.0,
  "vision_only_groups": 1.0,
  "deterministic_only_groups": 1.0,
  "counts": {
    "matched": {
      "bound": 297,
      "total": 297
    },
    "vision_only": {
      "bound": 99,
      "total": 99
    },
    "deterministic_only": {
      "bound": 45,
      "total": 45
    },
    "all": {
      "bound": 450,
      "total": 450
    }
  },
  "engineering_reference_coverage": {
    "geometry": 1.0,
    "section_geometry": 1.0,
    "direction": 1.0,
    "support": 1.0,
    "cut_length_rule": 1.0,
    "development_length_rule": 1.0,
    "anchorage": 1.0,
    "hook_bend": 1.0
  }
}

## Tests

- D.3 unit tests: 24/24 success=True
- prior D.1 frozen: True
- prior D.2 frozen: True
- anti-hardcoding: True
- fingerprints unchanged: True

No production interpretation change. No R1.3 / SI / steel / BBS / workbook mutation.
