# QA.4.1 Engineering Recommendations

Based ONLY on the Fourth Set 104-entity audit evidence.

Principle: **Recover candidates, then let the existing ownership engine decide.**

Categories: `{'LEADER_CHAIN_FAILURE': 23, 'ENVELOPE_NEVER_CANDIDATE': 77, 'GEOMETRY_FAILURE': 4}`
Potentials: `{'LOW': 26, 'HIGH': 52, 'MEDIUM': 25, 'UNKNOWN': 1}`

## Priority 1: Candidate / Search Envelope Recovery

77/104 dropped entities never became candidates. 51 rated HIGH potential (barely outside production envelope). Implement a diagnostic recovery envelope only after validating representative HIGH cases — do not change ownership rules first.

## Priority 2: Leader Chain Recovery

23/104 leader-chain failures; 1 HIGH potential. Focus on LEADER_TIP_OUTSIDE cases near the production envelope.

## Priority 3: Geometry Recovery

Only 4 geometry failures. Inspect all cases before any geometry-rule change.

## Next implementation sequence
- 1. Candidate / Search Envelope Recovery
- 2. Leader Chain Recovery
- 3. Geometry Recovery
- 4. Full QA.4 recovery benchmark
- 5. Fifth/Sixth Set generalization validation
