# Phase QA.3.3 Execution Summary

- MODEL_VERSION: `10.0.3`
- Elapsed: `40.23s`
- Beams analysed: `11`
- Candidate discovery rate: `189.3801`
- Ownership acceptance rate: `58.1142`
- Candidate rejection rate: `16.735`
- Conflict frequency: `16.3627`
- Avg competing beams/entity: `1.0`
- Avg ownership score: `0.6427`
- Avg rejection score: `0.0`
- Avg score margin: `0.0`
- Most common rejection reason: `('annotation_on_neighbour_side_of_mark', 28)`
- Most common filtering rule: `('R5_NEIGHBOUR_REJECT', 32)`
- Most common competing scenario: `('3L-Y10@100C/C::B100+B101+B102+B103', 1)`
- Failure frequency: `{'Conflict Resolution': 7, 'Mixed': 4}`
- Validation overall_pass: `True`

## Priorities
### Priority 1: Neighbour / conflict resolution rules (R5)

Most ownership shortfalls are neighbour-side rejects or multi-beam competition. QA.4.0 should focus on R5_NEIGHBOUR_REJECT / side_of_mark logic using these decision traces — without guessing.

- Impact: High
- Expected benchmark: Expected: reduce false neighbour rejects; improve bar/annotation match on stacked beams

### Priority 2: Preserve decision-trace regression gates in QA.4.0

Any ownership change must keep EntityDecisionTrace outcomes explainable and must not silently alter decisions without a before/after trace diff.

- Impact: Medium
- Expected benchmark: Process quality; prevents opaque regressions

### Priority 3: Separate Manual-crop GT issues (QA.3.2) from Ownership defects

QA.3.2 showed Manual crops are unreliable. Ownership improvements should be validated against decision traces and entity registries, not Manual PNG IoU alone.

- Impact: Medium
- Expected benchmark: Cleaner measurement of true ownership gains

