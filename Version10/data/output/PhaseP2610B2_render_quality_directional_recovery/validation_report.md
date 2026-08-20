# P2.6.10-B.2 — Render Quality & Direction-Aware Adaptive Crop Recovery

Shadow / validation only. Fourth drawing set only. No Claude Vision.
Context is validated before Detail. PNG generated is not treated as Vision-usable.

**Phase:** P2.6.10-B.2
**Model version:** 10.11.13
**Gate version:** P2610B2_RENDER_QUALITY_DIRECTIONAL_RECOVERY_V1_0
**STATUS:** PARTIAL
**DECISION:** PASS_WITH_LIMITATIONS

## Population

- source DXF: `C:\Users\nishanth.h\SteelBeamEstimator\Test_Input\4th Set Drawings-Inizio_B1\reinforcement\SE-204_BASEMENT-01 FLOOR BEAM REINFORCEMENT DETAILS(SH-01 TO 03).dxf`
- discovered unique beams: 135
- initial context generated: 135
- context valid before recovery: 50
- context valid after recovery: 131
- initial detail generated: 135
- detail valid after recovery: 109
- empty renders: 0
- black renders: 0
- low-information renders: 27
- horizontal clipping suspects: 127
- vertical clipping suspects: 117
- context recovery attempts / successes: 255 / 81
- detail recovery attempts / successes: 158 / 27
- unresolved context / detail: 4 / 23
- final vision-usable: 108 / 135 (0.8)
- skipped / true render failures: 0 / 0

## Context / detail / population metrics

- context: {"total_beams": 135, "initial_valid": 50, "recovery_required": 85, "recovered": 81, "unresolved": 4, "blank_black_initial": 24, "blank_black_final": 0, "horizontal_recovery_count": 58, "vertical_recovery_count": 20}
- detail: {"total_processed": 135, "initial_valid": 82, "recovery_required": 53, "recovered": 27, "unresolved": 23}
- population: {"total_unique_beams": 135, "context_complete": 131, "detail_complete": 109, "both_complete": 108, "incomplete": 27, "skipped": 0, "render_failures": 0}

## SAFE_STOP_RECORD (pre-optimization)

Pre-optimization partial run is preserved under `pre_optimization_partial/`.
It is **not** final population validation evidence.

## PRE_VS_POST_OPTIMIZATION_COMPARISON

- pre-optimization partial rate: 125.277 s/beam (8 beams)
- post-optimization total runtime: 1680.1710960000055 s
- post-optimization avg: 12.445711833333458 s/beam
- context screening: 47.6059410002199 s
- detail runtime: 106.48282570025185 s
- recovery runtime: 292.64467680006055 s
- diagnostic I/O: 2.077772200049367 s
- cache hits/misses: 0 / 408
- parallelism: enabled=False workers=1 renderer_parallel_safe=False

## Failures

- B96A [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B99A [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, HORIZONTAL_TRUNCATION_SUSPECT usable=False
- B101A [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B191 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B180 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, HORIZONTAL_TRUNCATION_SUSPECT usable=False
- B182 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B185 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B173 [CONTEXT]: BORDER_CLIPPING_SUSPECT flags=BORDER_CLIPPING_SUSPECT, RIGHT_BORDER_CONTACT, EMPTY_REGION_PRESENT, EMPTY_LEFT usable=False
- B170 [CONTEXT]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B168 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B144 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, HORIZONTAL_TRUNCATION_SUSPECT usable=False
- B154 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B136 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, HORIZONTAL_TRUNCATION_SUSPECT usable=False
- B140 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, EMPTY_REGION_PRESENT, EMPTY_LEFT usable=False
- B121 [CONTEXT]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, VERTICAL_TRUNCATION_SUSPECT usable=False
- B129 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B100 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, HORIZONTAL_TRUNCATION_SUSPECT, VERTICAL_TRUNCATION_SUSPECT usable=False
- B103 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B98 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B120 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B86 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B85 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B83 [CONTEXT]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B71 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, EMPTY_REGION_PRESENT, EMPTY_LEFT usable=False
- B56 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B57 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER usable=False
- B25 [DETAIL]: LOW_INFORMATION_RENDER flags=LOW_INFORMATION_RENDER, HORIZONTAL_TRUNCATION_SUSPECT usable=False

## Known visual cases

### blank_black
- B32: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B33: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=COMPACT ctx_attempts=0
- B34: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=VERTICAL ctx_attempts=3
- B35: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=COMPACT ctx_attempts=0
- B36: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B37: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B38: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=COMPACT ctx_attempts=0
- B39: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=VERTICAL ctx_attempts=3

### longitudinal_clipping
- B19: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B24: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B24A: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B152: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=COMPACT ctx_attempts=0
- B176: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3

### low_context_quality
- B26: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B68A: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=0
- B70: ctx=BORDER_CLIPPING_SUSPECT det=VALID usable=True orient=HORIZONTAL ctx_attempts=0
- B99: ctx=BORDER_CLIPPING_SUSPECT det=BORDER_CLIPPING_SUSPECT usable=True orient=HORIZONTAL ctx_attempts=3
- B99A: ctx=BORDER_CLIPPING_SUSPECT det=LOW_INFORMATION_RENDER usable=False orient=VERTICAL ctx_attempts=3

## Anti-hardcoding

- source guard: PASS
- translation invariance: PASS
- DXF-copy translation: PASS
- spatial-distance robustness: PASS
- packed-sheet robustness: PASS

## Original six-beam regression

- Fourth/B141: complete=True b2_usable=True
- Fourth/B66: complete=True b2_usable=True
- Fourth/B161: complete=True b2_usable=True
- Fifth/B128: complete=True b2_usable=True
- Fifth/B55: complete=True b2_usable=True
- Fifth/B65: complete=True b2_usable=True

## Prior regressions

- P2.6.6: PASS
- P2.6.10-A: PASS
- P2.6.10-B: PASS
- P2.6.10-B.1: PASS
- P2.6.10-B.2 unit tests: 29/29 success=True

## Production firewall

- production mutation count: 0
- steel quantity delta: 0
- BBS delta: 0
- workbook delta: 0
- live Claude Vision calls: False

## Final decision

**PASS_WITH_LIMITATIONS**

This phase does not authorize Claude Vision or production promotion.
