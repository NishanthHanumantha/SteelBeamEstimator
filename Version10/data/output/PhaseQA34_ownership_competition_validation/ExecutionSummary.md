# Phase QA.3.4 Execution Summary

- MODEL_VERSION: `10.0.4`
- Elapsed: `13.49s`
- Total rejected: `123`
- Owned elsewhere: `19`
- Dropped: `104`
- Leader failures: `23`
- Geometry failures: `4`
- Envelope failures: `77`
- Conflict failures: `0`
- Unknown: `0`
- Avg ownership margin: `0.0`
- Median margin: `0.0`
- Dropped fraction: `0.8455`
- Regression overall_pass: `True`
- Ownership decisions changed: `False`
- QA validation overall_pass: `True`
- Dominant QA.4.0 target: `dropped_entity_recovery`

## Priorities
### Priority 1: Target disappearing entities (Dropped), not only R5

A large share of rejects are Owned nowhere (Dropped). QA.4.0 must not assume neighbour ownership transfers — many entities simply disappear. Focus root-cause work on DroppedEntities.json (leader=23, geometry=4, envelope=77, conflict-marked-dropped subset inside conflict_failures=0).

### Priority 2: Secondary target: search_envelope

Among Dropped/failure subtypes, `search_envelope` leads with 77 cases. Instrument QA.4.0 changes against EntityDecisionTrace + this competition registry.

### Priority 3: Keep competition regression gates

Any QA.4.0 ownership change must re-run QA.3.4 and show an intentional diff in Dropped vs OwnedElsewhere — never silent decision changes.

