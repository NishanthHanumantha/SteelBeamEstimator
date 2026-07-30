# Phase R.2.1B — Engineering Semantic Interpreter
**MODEL_VERSION**: 8.9.0  |  **Generated**: 2026-07-30T07:18:15.111398

---

## 1. Architecture Summary

Phase R.2.1B sits between the R.2.1A Semantic Dictionary and the
EngineeringBarBuilder. It converts raw R.1 parsed annotations into
structured `EngineeringSemanticObject`s with full engineering meaning.

```
DXF → R.1 Discovery → R.2.0 MTEXT → R.2.1A Dict → R.2.1B Interpreter
    → EngineeringBarBuilder → EngineeringBarModel → Steel → BBS → Excel
```

## 2. Semantic Pipeline

1. **SemanticContextBuilder** — gather annotation facts + dictionary lookup
2. **SemanticModifierParser** — detect O.E.F., S.F.R., BOTH FACE, etc.
3. **SemanticRoleResolver** — Explicit Modifier > Dictionary > Regex
4. **SemanticQuantityResolver** — preserve qty without multiplication
5. **SemanticPlacementResolver** — NEAR/FAR/BOTH/SIDE/TOP/BOTTOM
6. **SemanticConflictResolver** — adjudicate, set confidence/source
7. **EngineeringMeaningBuilder** — produce final EngineeringSemanticObject

## 3. Statistics

| Metric | Value |
|--------|-------|
| Total semantic objects | 277 |
| Beams covered | 61 |
| UNKNOWN count | 20 |
| Role overrides | 5 |
| Objects with modifiers | 13 |
| Semantic coverage | 92.8% |
| Dictionary coverage | 1.8% |
| Semantic confidence | 1.8% |

### 3a. Role Distribution

- `EXTRA_BAR`: 121
- `MAIN_BAR`: 98
- `UNKNOWN`: 20
- `STIRRUP`: 17
- `SPACER_BAR`: 16
- `SIDE_FACE`: 5

### 3b. Meaning Distribution

- `TOP_EXTRA`: 90
- `TOP_MAIN`: 61
- `BOTTOM_MAIN`: 37
- `BOTTOM_EXTRA`: 31
- `UNKNOWN`: 20
- `STIRRUP`: 17
- `SPACER`: 16
- `SIDE_FACE_REINFORCEMENT`: 5

### 3c. Modifier Distribution

- `BOTH_FACES`: 9
- `SIDE_FACE_REINFORCEMENT`: 5
- `TYPICAL`: 1

### 3d. Placement Distribution

- `TOP`: 170
- `BOTTOM`: 77
- `UNKNOWN`: 18
- `BOTH_FACE`: 12

## 4. Validation Summary

**Result**: 12/12 validation rules passed

| Rule | Status | Detail |
|------|--------|--------|
| RULE_1 | ✓ PASS | 277/277 annotations produced semantic objects |
| RULE_2 | ✓ PASS | 0 objects missing engineering_meaning |
| RULE_3 | ✓ PASS | 0 dictionary-covered reinforcement bars still UNKNOWN |
| RULE_4 | ✓ PASS | 0 quantity mismatches |
| RULE_5 | ✓ PASS | 0 diameter mismatches |
| RULE_6 | ✓ PASS | 0 stirrups lost spacing |
| RULE_7 | ✓ PASS | S.F.R.: 5/3 detected; O.E.F.: 0/0 detected |
| RULE_8 | ✓ PASS | 0 objects missing placement |
| RULE_9 | ✓ PASS | Semantic interpreter uses no hardcoded beam IDs (verified by code review) |
| RULE_10 | ✓ PASS | Backward compatible: 5 role overrides applied, 272 preserved |
| RULE_11 | ✓ PASS | No engineering equations modified (forbidden files untouched: steel_weight_compl |
| RULE_12 | ✓ PASS | Production workbook generated |

## 5. Pipeline Integration

The semantic interpreter enriches R.1 beam models before
EngineeringBarBuilder processes them. Role overrides are applied
to the groups JSON so existing bar-building logic picks up
the correct engineering role.

## 6. Production Run

| Metric | Value |
|--------|-------|
| Steel weight (kg) | 14812.2 |
| Beams reaching steel | 61 |
| BBS rows | 405 |
| Workbook generated | Yes |

## 7. Remaining Engineering Limitations

- Quantity multiplier for O.E.F. / BOTH FACE deferred to future calculation engine
- Top/bottom placement for MAIN_BAR / EXTRA_BAR requires geometry context from R.3
- Lap and development length semantic role detection is pattern-based (no equation)
- UNKNOWN annotations without bar specs (e.g. label-only S.F.R. text) are not
  counted as reinforcement — this is correct engineering behaviour

**MODEL_VERSION**: 8.9.0