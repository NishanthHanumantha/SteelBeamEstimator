# QA.3.4 Engineering Recommendations

Based ONLY on competition validation evidence.

Summary: rejected=123 owned_elsewhere=19 dropped=104 leader=23 geometry=4 envelope=77 conflict=0; dominant=dropped_entity_recovery

## Priority 1: Target disappearing entities (Dropped), not only R5

A large share of rejects are Owned nowhere (Dropped). QA.4.0 must not assume neighbour ownership transfers — many entities simply disappear. Focus root-cause work on DroppedEntities.json (leader=23, geometry=4, envelope=77, conflict-marked-dropped subset inside conflict_failures=0).

- QA.4.0 target: `dropped_entity_recovery`
- Impact: High
- Expected: Recover callouts/bars that currently vanish from all beam ownership sets

## Priority 2: Secondary target: search_envelope

Among Dropped/failure subtypes, `search_envelope` leads with 77 cases. Instrument QA.4.0 changes against EntityDecisionTrace + this competition registry.

- QA.4.0 target: `search_envelope`
- Impact: Medium-High
- Expected: Reduce search_envelope driven drops

## Priority 3: Keep competition regression gates

Any QA.4.0 ownership change must re-run QA.3.4 and show an intentional diff in Dropped vs OwnedElsewhere — never silent decision changes.

- QA.4.0 target: `process_gate`
- Impact: Medium
- Expected: Prevents opaque ownership regressions
