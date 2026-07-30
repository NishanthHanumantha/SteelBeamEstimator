# Phase R.3 — Geometry Context Engine
**MODEL_VERSION:** 8.9.3
**Generated:** 2026-07-30T07:17:10Z

---

## Summary

| Metric | Value |
|--------|-------|
| Beams processed | 62 |
| GeometryContexts produced | 229 |
| Validation rules passed | 11/12 validation rules passed |
| Phase intent status | UNKNOWN (geometry-only) |

---

## Architecture

```
R.2.1D Evidence & Intent Hypothesis Engine
    |
    v
R.3 Geometry Context Engine  [this phase]
    |
    v
R.4 Engineering Intent Resolver  [future]
```

> R.3 answers ONLY: **Where is this reinforcement annotation located?**
> R.3 does NOT answer: What does this reinforcement mean?

---

## Beam Axis Statistics

| Property | Value |
|----------|-------|
| Beam count | 62 |
| Min span | 1551 mm |
| Max span | 8821 mm |
| Mean span | 4508 mm |

**Orientations:**

- HORIZONTAL: 62

**Geometry sources:**

- ORIGINAL: 57
- RECOVERED: 5

---

## Support Statistics

| Property | Value |
|----------|-------|
| Total supports | 124 |
| Avg support width | 313 mm |
| Beams with supports | 62 |

---

## Projection Statistics

| Property | Value |
|----------|-------|
| Min projection | -1121 mm |
| Max projection | 9844 mm |
| Mean projection | 2877 mm |

**Confidence distribution:**

- HIGH: 229

**Position source distribution:**

- REINFORCEMENT_ANNOTATIONS_DXF: 229

---

## Normalized Position Histogram (0.0 → 1.0)

| Bin | Count |
|-----|-------|
| 0.0-0.1 | 7 |
| 0.1-0.2 | 10 |
| 0.2-0.3 | 7 |
| 0.3-0.4 | 19 |
| 0.4-0.5 | 28 |
| 0.5-0.6 | 45 |
| 0.6-0.7 | 32 |
| 0.7-0.8 | 34 |
| 0.8-0.9 | 20 |
| 0.9-1.0 | 27 |

---

## Span Zone Distribution

| Zone | Count |
|------|-------|
| MIDSPAN_ZONE | 152 |
| RIGHT_TRANSITION_ZONE | 35 |
| LEFT_TRANSITION_ZONE | 14 |
| RIGHT_SUPPORT_ZONE | 22 |
| LEFT_SUPPORT_ZONE | 6 |

---

## Extent Evidence Distribution

| Label | Count |
|-------|-------|
| MIDSPAN_ONLY | 151 |
| RIGHT_TRANSITION | 33 |
| LEFT_TRANSITION | 14 |
| RIGHT_SUPPORT_ONLY | 22 |
| LEFT_SUPPORT_ONLY | 5 |
| FULL_SPAN | 4 |

---

## Validation Summary

**Result: 11/12 validation rules passed**

| Rule | Status | Detail |
|------|--------|--------|
| RULE_1 — Every EngineeringFact receives GeometryContext | PASS | 229/229 facts have GeometryContext |
| RULE_2 — No missing beam IDs | PASS | 0 contexts missing beam_id |
| RULE_3 — Projection on beam axis | FAIL | 7 projections outside beam axis (tolerance=500.0mm) |
| RULE_4 — Normalized position in [0.0, 1.0] | PASS | 0 contexts with normalized_position outside [0.0, 1.0] |
| RULE_5 — Every beam has BeamAxis | PASS | 0 beams missing BeamAxis: [] |
| RULE_6 — Every beam has SupportLocation | PASS | 0 beams missing SupportLocation |
| RULE_7 — No duplicate contexts | PASS | 0 duplicate annotation_ids in contexts |
| RULE_8 — No hardcoded beam names | PASS | Geometry engine uses no hardcoded beam IDs (verified by architecture) |
| RULE_9 — Intent unchanged (UNKNOWN) | PASS | 0 facts with non-UNKNOWN intent |
| RULE_10 — No engineering equations modified | PASS | Phase R.3 is additive: no steel/BBS/Excel equations modified |
| RULE_11 — Backward compatibility maintained | PASS | R.3 reads R.2.1D facts without modification; backward compatible |
| RULE_12 — Production workbook generated | PASS | Production pipeline unchanged (R.3 is additive) |

---

## Geometry Confidence Distribution

| Confidence | Count |
|------------|-------|
| HIGH | 217 |
| MEDIUM | 12 |

---

## Design Principles

- Intent remains **UNKNOWN** — this phase provides geometry evidence only
- All geometry computations are **deterministic** (no AI, no heuristics)
- Beam axis derived from `geometry_registry.json` (local coordinate space)
- Annotation position derived from `reinforcement_annotations.json` (DXF space)
- Support zones derived from `geometry_registry.support_locations`
- No engineering equations, BBS, steel calculations, or Excel modified

---

*R.3 Geometry Context Engine | MODEL_VERSION: 8.9.3*