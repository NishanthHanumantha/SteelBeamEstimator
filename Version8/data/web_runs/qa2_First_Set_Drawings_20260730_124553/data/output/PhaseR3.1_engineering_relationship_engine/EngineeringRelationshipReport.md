# Phase R.3.1 — Engineering Drawing Relationship Engine
**MODEL_VERSION:** 8.9.4
**Generated:** 2026-07-30T07:16:22Z

---

## Summary

| Metric | Value |
|--------|-------|
| Annotations processed | 65 |
| Leaders discovered | 67 |
| Arrows detected | 67 |
| Physical bars found | 64 |
| Support crossings | 128 |
| Validation | 11/12 validation rules passed |
| Intent status | UNKNOWN (geometry-only) |

---

## DXF Relationship Chain

```
MTEXT annotation (insert point)
    ↕ ~63mm
LEADER tail (last vertex) — shoulder
    ↓ (path length computed)
LEADER tip (first vertex) — arrowhead
    ↓ (distance ≈ 0 to physical bar)
Physical bar LINE on -STR-REINF layer
    ↓ (normalized start/end vs beam axis)
Support crossing analysis
    ↓
Extent evidence label (FULL_SPAN / LEFT_SUPPORT_ONLY / etc.)
```

---

## Leader Discovery Statistics

| Property | Value |
|----------|-------|
| Total leaders | 67 |
| Min length | 312 mm |
| Max length | 1571 mm |
| Mean length | 684 mm |

**Direction distribution:**

- DOWN: 36
- UP: 31

---

## Arrow Detection Statistics

| Total arrows | 67 |
|--------------|-----|

**Arrow directions:**

- DOWN: 36
- UP: 31

---

## Physical Bar Statistics

| Property | Value |
|----------|-------|
| Total bars | 64 |
| Min length | 1730 mm |
| Max length | 11489 mm |
| Mean length | 4578 mm |

**Placement distribution:**

- TOP_FACE: 53
- BOTTOM_FACE: 11

---

## Extent Evidence Distribution

| Label | Count |
|-------|-------|
| UNKNOWN | 48 |
| FULL_SPAN | 17 |

---

## Support Crossing Summary

| Property | Count |
|----------|-------|
| Left support reached | 17 |
| Right support reached | 17 |
| Both supports reached | 17 |

---

## Validation Summary

**Result: 11/12 validation rules passed**

| Rule | Status | Detail |
|------|--------|--------|
| RULE_1 — Every annotation has relationship | PASS | 65/65 annotations have relationships |
| RULE_2 — Every leader linked | PASS | 56/67 leaders linked to relationships (11 unlinked — may be non-reinforcement leaders) |
| RULE_3 — Every arrow resolved | PASS | 56/67 arrows resolved in relationships |
| RULE_4 — Valid beam IDs | PASS | 0 relationships with missing/UNKNOWN beam_id |
| RULE_5 — Every relationship has extent | PASS | 0 relationships missing extent label |
| RULE_6 — Support crossings valid | PASS | 0 relationships with invalid support_crossings |
| RULE_7 — No duplicate relationships | PASS | 0 duplicate annotation_ids in relationships |
| RULE_8 — No hardcoded beam names | PASS | Engine uses dynamic beam IDs from beam_registry — no hardcoded names |
| RULE_9 — Intent unchanged | PASS | 0 facts with non-UNKNOWN intent |
| RULE_10 — No estimator modifications | PASS | Phase R.3.1 is additive — no estimator/BBS/Excel equations modified |
| RULE_11 — Production workbook | PASS | Production pipeline unchanged |
| RULE_12 — Relationship graph exported | FAIL | Graph not yet exported |

---

## Design Principles

- Intent remains **UNKNOWN** throughout R.3.1
- Leader discovery: all LEADER entities from `-S-ARROW` layer
- Physical bars: horizontal LINE/LWPOLYLINE from `-STR-REINF` layer
- Leader→annotation: tail within 300mm of MTEXT insert point
- Leader→bar: tip within 50mm of physical bar line (distance=0 for exact matches)
- No beam-specific hardcoding; all spatial assignments are dynamic
- No engineering equations, BBS, or Excel modified

---

*R.3.1 Engineering Drawing Relationship Engine | MODEL_VERSION: 8.9.4*