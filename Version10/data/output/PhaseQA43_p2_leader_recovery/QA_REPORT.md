# QA.4.3 — P2 Leader Recovery Report

- MODEL_VERSION: `10.5.2`
- Overall gate: `PASS`

## Population
- Dropped leaders inspected: `23`
- HIGH / MEDIUM / LOW / UNKNOWN: `1` / `4` / `17` / `1`

## Recovery
- Candidates generated: `5`
- Eligible: `5`
- Excluded / diagnostic: `18`
- Already in production accepted: `0`
- Newly added: `0`
- T18 accepted / rejected: `0` / `23`

## Safety
- Neighbour ambiguity: `5`
- Inside other beam: `1`
- Far outside: `7`
- Duplicates: `0`
- Contamination: `0`
- Fifth / Sixth: `0` / `0`
- Production ownership changed: `False`
- Production envelope changed: `False`

## Gates
- QA.4.2 regression: `PASS`
- T18 regression: `PASS`
- Determinism: `PASS`
- Failed gates: `[]`

## Outcomes
`{'diagnostic_only': 18, 'ownership_rejected': 5}`

P3 geometry recovery was NOT implemented.
