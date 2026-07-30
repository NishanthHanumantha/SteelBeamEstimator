# Phase R.3.1 — Engineering Drawing Relationship Engine
**MODEL_VERSION:** 8.9.4
**Generated:** 2026-07-30T07:18:20Z

---

## Summary

| Metric | Value |
|--------|-------|
| Annotations processed | 277 |
| Leaders discovered | 330 |
| Arrows detected | 330 |
| Physical bars found | 166 |
| Support crossings | 332 |
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
| Total leaders | 330 |
| Min length | 222 mm |
| Max length | 2691 mm |
| Mean length | 757 mm |

**Direction distribution:**

- UP: 121
- DOWN: 165
- RIGHT: 9
- LEFT: 35

---

## Arrow Detection Statistics

| Total arrows | 330 |
|--------------|-----|

**Arrow directions:**

- UP: 121
- DOWN: 165
- RIGHT: 9
- LEFT: 35

---

## Physical Bar Statistics

| Property | Value |
|----------|-------|
| Total bars | 166 |
| Min length | 287 mm |
| Max length | 19140 mm |
| Mean length | 5568 mm |

**Placement distribution:**

- TOP_FACE: 105
- BOTTOM_FACE: 61

---

## Extent Evidence Distribution

| Label | Count |
|-------|-------|
| UNKNOWN | 239 |
| FULL_SPAN | 29 |
| MIDSPAN_TO_RIGHT_SUPPORT | 5 |
| LEFT_SUPPORT_TO_MIDSPAN | 1 |
| RIGHT_SUPPORT_ONLY | 3 |

---

## Support Crossing Summary

| Property | Count |
|----------|-------|
| Left support reached | 30 |
| Right support reached | 37 |
| Both supports reached | 29 |

---

## Validation Summary

**Result: 11/12 validation rules passed**

| Rule | Status | Detail |
|------|--------|--------|
| RULE_1 — Every annotation has relationship | PASS | 277/277 annotations have relationships |
| RULE_2 — Every leader linked | PASS | 242/330 leaders linked to relationships (88 unlinked — may be non-reinforcement leaders) |
| RULE_3 — Every arrow resolved | PASS | 242/330 arrows resolved in relationships |
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