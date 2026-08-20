# P2.6.10-B.3 — Target Anchor Truth + Geometry-Bounded Context Recovery

Shadow / validation only. Overlay recovery. Known-good B.1 renders are frozen.
No Claude Vision. No production mutation.

**STATUS:** PARTIAL
**DECISION:** PASS_WITH_LIMITATIONS
**Model:** 10.11.14  **Gate:** P2610B3_TARGET_ANCHOR_GEOMETRY_CONTEXT_RECOVERY_V1_0

## Population

- unique beams: 135
- frozen-good: 0
- target-recovery: 90
- review-only: 45
- known-good regression: 0
- B.1 reused / B.2 retained / B.3 improved / fallback: 90 / 14 / 8 / 82

## Performance

- total runtime s: 1497.3311579999863
- targeted beams: 90
- avg recovery s/targeted: 14.89849565999854
- parallelism: False workers=1

## Known visual cases

### blank_black
- B32: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B33: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B34: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B35: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B36: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B37: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B38: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B39: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1

### longitudinal_clipping
- B19: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B24: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B24A: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B152: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B176: class=TARGET_RECOVERY action=improved ctx=BORDER_CLIPPING_SUSPECT src=P2610B3

### low_context_quality
- B26: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B68A: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B69: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B70: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1
- B99: class=TARGET_RECOVERY action=unchanged ctx=LOW_INFORMATION_RENDER src=P2610B2
- B99A: class=TARGET_RECOVERY action=fallback_to_baseline ctx=BORDER_CLIPPING_SUSPECT src=P2610B1

## Anti-hardcoding / regression / production

- anti-hardcoding: PASS
- unit tests: 18/18 success=True
- production mutation count: 0
- live Claude Vision: False

## Recommendation

A. Proceed to Detail Candidate Selection + Visual Completeness Gate + Claude Vision Shadow Benchmark

**PASS**

This phase does not authorize Claude Vision or production promotion.
