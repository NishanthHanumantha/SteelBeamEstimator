# QA.2B.0 — Execution Summary

**MODEL_VERSION:** 9.6.0
**Generated:** 2026-08-05T10:51:46.980079+00:00
**Overall PASS:** True

## Purpose

Pipeline integration / execution integrity only. Engineering accuracy is not evaluated in this phase.

## Versions connected

- Renderer (T1.8.2): `9.5.2`
- Crop generator (T1 OpenCV): `9.3.3`
- Engineering pipeline: `9.3.0`
- Ownership / shared scope: `9.5.4`
- Benchmark (QA.2A): `9.3.0`

## Totals

- Beams processed: **142**
- Crops resolved: **142**
- Comparisons ready: **142**
- Missing renders: **0**
- Missing crops: **0**
- Benchmark execution success: **True**

## Per drawing set

### First — `qa2_First_Set_Drawings_20260803_132045`

- Success: `True`
- Beams: 18 | Crops: 18 | Comparisons: 18
- Missing crop: 0 | Missing render: 0

  - `T1`: SKIP
  - `T1.6`: SKIP
  - `T1.7`: SKIP
  - `T1.8`: SKIP
  - `T1.8.1`: SKIP
  - `T1.8.2`: SKIP
  - `T1.8.3`: SKIP
  - `T1.8.3.1`: SKIP

### Second — `qa2_Second_Set_Drawings_20260803_132207`

- Success: `True`
- Beams: 63 | Crops: 63 | Comparisons: 63
- Missing crop: 0 | Missing render: 0

  - `T1`: SKIP
  - `T1.6`: SKIP
  - `T1.7`: SKIP
  - `T1.8`: OK
  - `T1.8.1`: OK
  - `T1.8.2`: OK
  - `T1.8.3`: OK
  - `T1.8.3.1`: OK

### Third — `qa2_Third_Set_Drawings_20260803_132502`

- Success: `True`
- Beams: 61 | Crops: 61 | Comparisons: 61
- Missing crop: 0 | Missing render: 0

  - `T1`: SKIP
  - `T1.6`: SKIP
  - `T1.7`: SKIP
  - `T1.8`: SKIP
  - `T1.8.1`: SKIP
  - `T1.8.2`: SKIP
  - `T1.8.3`: SKIP
  - `T1.8.3.1`: SKIP

## Validation checks

- [x] Latest renderer connected
- [x] Latest crop generator connected
- [x] Latest engineering interpreter connected
- [x] Latest ownership engine connected
- [x] Latest stirrup recovery connected
- [x] Shared ownership connected
- [x] Legacy paths removed
- [x] Deprecated renderer removed
- [x] Deprecated crop generator removed
- [x] End-to-end execution PASS
- [x] Every beam has crop
- [x] Every comparison ready
- [x] Benchmark executed

