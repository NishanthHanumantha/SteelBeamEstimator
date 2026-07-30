# Phase R.2.1B — Engineering Semantic Interpreter
**MODEL_VERSION**: 8.9.0  |  **Generated**: 2026-07-30T07:16:15.722933

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
| Total semantic objects | 65 |
| Beams covered | 18 |
| UNKNOWN count | 1 |
| Role overrides | 2 |
| Objects with modifiers | 5 |
| Semantic coverage | 98.5% |
| Dictionary coverage | 3.1% |
| Semantic confidence | 3.1% |

### 3a. Role Distribution

- `EXTRA_BAR`: 31
- `MAIN_BAR`: 29
- `SPACER_BAR`: 2
- `SIDE_FACE`: 2
- `UNKNOWN`: 1

### 3b. Meaning Distribution

- `TOP_EXTRA`: 21
- `TOP_MAIN`: 18
- `BOTTOM_MAIN`: 11
- `BOTTOM_EXTRA`: 10
- `SPACER`: 2
- `SIDE_FACE_REINFORCEMENT`: 2
- `UNKNOWN`: 1

### 3c. Modifier Distribution

- `BOTH_FACES`: 4
- `SIDE_FACE_REINFORCEMENT`: 2

### 3d. Placement Distribution

- `TOP`: 39
- `BOTTOM`: 21
- `BOTH_FACE`: 5

## 4. Validation Summary

**Result**: 12/12 validation rules passed

| Rule | Status | Detail |
|------|--------|--------|
| RULE_1 | ✓ PASS | 65/65 annotations produced semantic objects |
| RULE_2 | ✓ PASS | 0 objects missing engineering_meaning |
| RULE_3 | ✓ PASS | 0 dictionary-covered reinforcement bars still UNKNOWN |
| RULE_4 | ✓ PASS | 0 quantity mismatches |
| RULE_5 | ✓ PASS | 0 diameter mismatches |
| RULE_6 | ✓ PASS | 0 stirrups lost spacing |
| RULE_7 | ✓ PASS | S.F.R.: 2/1 detected; O.E.F.: 0/0 detected |
| RULE_8 | ✓ PASS | 0 objects missing placement |
| RULE_9 | ✓ PASS | Semantic interpreter uses no hardcoded beam IDs (verified by code review) |
| RULE_10 | ✓ PASS | Backward compatible: 2 role overrides applied, 63 preserved |
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
| Steel weight (kg) | 1633.0 |
| Beams reaching steel | 18 |
| BBS rows | 98 |
| Workbook generated | Yes |

## 7. Remaining Engineering Limitations

- Quantity multiplier for O.E.F. / BOTH FACE deferred to future calculation engine
- Top/bottom placement for MAIN_BAR / EXTRA_BAR requires geometry context from R.3
- Lap and development length semantic role detection is pattern-based (no equation)
- UNKNOWN annotations without bar specs (e.g. label-only S.F.R. text) are not
  counted as reinforcement — this is correct engineering behaviour

**MODEL_VERSION**: 8.9.0