# Engineering Recommendations (P2.4)

Diagnostic only — no recovery implemented in this phase.

## Measured dominant first-fail: `QUANTITY_RESOLUTION`

## Recommended next phase: **QUANTITY INTERPRETATION ENHANCEMENT**

### Decision framework applied

Recommendation is taken from `RECOMMENDATION_MAP` using the largest
first-failure category among failing GT bars (NO_FAILURE excluded).

### Evidence notes

- Ownership is **not** the dominant first-fail (0 wrong-beam ownership first-fails among unmatched GT bars).
- Combined semantic interpretation (QUANTITY + ROLE + DIAMETER) is 57.1% of all failures; quantity alone is the single largest bucket (24.0%).
- Quantity failures concentrate on STIRRUP / STIRRUP_HOOK / SPACER_BAR rows (callout quantity / zone multiplicity interpretation).
- Do **not** start with Ownership→Engineering Bridge: ENGINEERING_OBJECT/VB1 is only 3.8% of failures.

### Supporting evidence

- QUANTITY_RESOLUTION: 185 (23.99%)
- ROLE_RESOLUTION: 144 (18.68%)
- DIAMETER_RESOLUTION: 111 (14.4%)

### Explicit non-recommendations

- Do not choose ownership solely because prior phases studied it.
- Do not implement Ownership→Engineering Bridge unless ENGINEERING_OBJECT/VB1 dominates.
