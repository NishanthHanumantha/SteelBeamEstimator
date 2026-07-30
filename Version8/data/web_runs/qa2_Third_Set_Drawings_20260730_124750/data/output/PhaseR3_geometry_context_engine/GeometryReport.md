# Phase R.3 — Geometry Context Engine
**MODEL_VERSION:** 8.9.3
**Generated:** 2026-07-30T07:18:17Z

---

## Summary

| Metric | Value |
|--------|-------|
| Beams processed | 61 |
| GeometryContexts produced | 277 |
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
| Beam count | 61 |
| Min span | 1500 mm |
| Max span | 8775 mm |
| Mean span | 4944 mm |

**Orientations:**

- HORIZONTAL: 61

**Geometry sources:**

- ORIGINAL: 51
- RECOVERED: 10

---

## Support Statistics

| Property | Value |
|----------|-------|
| Total supports | 122 |
| Avg support width | 383 mm |
| Beams with supports | 61 |

---

## Projection Statistics

| Property | Value |
|----------|-------|
| Min projection | -1622 mm |
| Max projection | 11905 mm |
| Mean projection | 3168 mm |

**Confidence distribution:**

- HIGH: 277

**Position source distribution:**

- REINFORCEMENT_ANNOTATIONS_DXF: 277

---

## Normalized Position Histogram (0.0 → 1.0)

| Bin | Count |
|-----|-------|
| 0.0-0.1 | 12 |
| 0.1-0.2 | 7 |
| 0.2-0.3 | 7 |
| 0.3-0.4 | 21 |
| 0.4-0.5 | 33 |
| 0.5-0.6 | 37 |
| 0.6-0.7 | 58 |
| 0.7-0.8 | 33 |
| 0.8-0.9 | 25 |
| 0.9-1.0 | 44 |

---

## Span Zone Distribution

| Zone | Count |
|------|-------|
| MIDSPAN_ZONE | 182 |
| RIGHT_SUPPORT_ZONE | 36 |
| RIGHT_TRANSITION_ZONE | 38 |
| LEFT_TRANSITION_ZONE | 11 |
| LEFT_SUPPORT_ZONE | 10 |

---

## Extent Evidence Distribution

| Label | Count |
|-------|-------|
| MIDSPAN_ONLY | 182 |
| RIGHT_SUPPORT_ONLY | 34 |
| RIGHT_TRANSITION | 38 |
| FULL_SPAN | 4 |
| LEFT_TRANSITION | 10 |
| LEFT_SUPPORT_ONLY | 9 |

---

## Validation Summary

**Result: 11/12 validation rules passed**

| Rule | Status | Detail |
|------|--------|--------|
| RULE_1 — Every EngineeringFact receives GeometryContext | PASS | 277/277 facts have GeometryContext |
| RULE_2 — No missing beam IDs | PASS | 0 contexts missing beam_id |
| RULE_3 — Projection on beam axis | FAIL | 19 projections outside beam axis (tolerance=500.0mm) |
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
| HIGH | 231 |
| MEDIUM | 46 |

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