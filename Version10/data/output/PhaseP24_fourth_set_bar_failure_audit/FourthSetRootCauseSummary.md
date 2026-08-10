# Fourth Set Root Cause Summary (P2.4)

- MODEL_VERSION: `10.6.0`
- SCOPE: `FOURTH_SET_ONLY`
- MODE: `DIAGNOSTIC_ONLY`
- ENGINEERING_CHANGES: `NONE`

## Headline metrics

- GT bars: **907**
- Matched: **136**
- Partially matched: **227**
- Unmatched: **544**
- Extra model bars: **51**

## Stage rates (over all GT bars)

- Physical detection: 78.61%
- Ownership: 78.61%
- Annotation association (CORRECT): 64.39%
- Leader-chain valid: 56.12%
- Role accuracy: 58.88%
- Diameter accuracy: 48.51%
- Quantity accuracy: 29.22%
- Engineering propagation: 62.18%
- VB1 consumption: 40.02%

## First-failure distribution (% of failing GT bars)

- `QUANTITY_RESOLUTION`: 23.99% (185)
- `ROLE_RESOLUTION`: 18.68% (144)
- `DIAMETER_RESOLUTION`: 14.4% (111)
- `LEADER_CHAIN`: 13.88% (107)
- `PHYSICAL_BAR_DETECTION`: 13.75% (106)
- `DXF_GEOMETRY`: 11.28% (87)
- `VB1_INTEGRATION`: 3.76% (29)
- `ANNOTATION_ASSOCIATION`: 0.26% (2)

## Answers to mandatory questions

1. Missing at PhysicalBar detection: **106**
2. Wrong-beam ownership first-fail: **0**
3. Annotation association first-fail: **2**
4. Role/diameter/quantity first-fail: **213**
5. Engineering/VB1 first-fail: **29**
6. Largest first-fail category: **QUANTITY_RESOLUTION**
7. Second largest: **ROLE_RESOLUTION**
8. B10/B12/B13: see SpecialAnalyses — NOT_A_FOURTH_SET_BEAM — cannot attribute Fourth Set render failure to this ID.
9. Top reinforcement dominant failure: **DXF_GEOMETRY** — Missing/failing top bars are dominated by DXF_GEOMETRY (49/149 = 32.9%).
10. Shared B8/B9/B10: Fourth Set shared-beam case is SIDE_FACE_REINFORCEMENT scope on ['B100A', 'B101A', 'B96A', 'B97A', 'B98A', 'B99A'], not B8/B9/B10.

## Recommended next engineering phase

**QUANTITY INTERPRETATION ENHANCEMENT**

Chosen strictly from the measured first-failure distribution.
