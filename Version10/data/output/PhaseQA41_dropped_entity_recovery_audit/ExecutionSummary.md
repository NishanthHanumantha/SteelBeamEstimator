# Phase QA.4.1 Execution Summary

- MODEL_VERSION: `10.5.0`
- Elapsed: `9.242s`

QA.4.1 is a Fourth Set controlled audit-only phase.
It audits the 104 dropped entities from the 11 Fourth Set priority
beams. No dropped entity was recovered, no ownership decision was
changed, and no production engineering logic was modified.

Fifth and Sixth Set drawings were not included in the QA.4.1
baseline and will be used only for later generalization validation.

## Baseline
- Status: `PASS`
- Fourth Set entities in scope: `104`
- Fifth excluded: `0`
- Sixth excluded: `0`

## Category counts
`{'LEADER_CHAIN_FAILURE': 23, 'ENVELOPE_NEVER_CANDIDATE': 77, 'GEOMETRY_FAILURE': 4}`

## Recovery potential
`{'LOW': 26, 'HIGH': 52, 'MEDIUM': 25, 'UNKNOWN': 1}`

## Key answers
1. Envelope problems: `77`
2. Leader-chain problems: `23`
3. Geometry problems: `4`
4. Envelope distances: `{'count_with_distance': 77, 'min': 0.0, 'max': 4744.771, 'avg': 831.134, 'spatial_relationship_counts': {'NEAR_OUTSIDE': 3, 'BOUNDARY': 48, 'MODERATE_OUTSIDE': 20, 'FAR_OUTSIDE': 6}}`
5. Envelope HIGH potential: `51`
6. Leader HIGH potential: `1`
8. First recovery mechanism: `candidate_search_envelope_recovery`

## Evidence-driven P1
`ENVELOPE_NEVER_CANDIDATE`

## Recommended next implementation sequence
- 1. Candidate / Search Envelope Recovery
- 2. Leader Chain Recovery
- 3. Geometry Recovery
- 4. Full QA.4 recovery benchmark
- 5. Fifth/Sixth Set generalization validation

- Regression: `PASS`
- QA validation: `True`
- STATUS: `PASS`
