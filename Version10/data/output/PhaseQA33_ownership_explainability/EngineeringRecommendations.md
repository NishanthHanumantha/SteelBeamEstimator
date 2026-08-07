# QA.3.3 Engineering Recommendations

Based ONLY on collected evidence. NO ownership code changes in this phase.

Summary: top_fail=('Conflict Resolution', 7); top_reject=('annotation_on_neighbour_side_of_mark', 28); top_rule=('R5_NEIGHBOUR_REJECT', 32); accept_rate=58.1142

## Priority 1: Neighbour / conflict resolution rules (R5)

Most ownership shortfalls are neighbour-side rejects or multi-beam competition. QA.4.0 should focus on R5_NEIGHBOUR_REJECT / side_of_mark logic using these decision traces — without guessing.

- Engineering impact: **High**
- Expected benchmark improvement: Expected: reduce false neighbour rejects; improve bar/annotation match on stacked beams
- Evidence: `{'top_failure_category': ('Conflict Resolution', 7), 'most_common_rejection_reason': ('annotation_on_neighbour_side_of_mark', 28), 'most_common_filtering_rule': ('R5_NEIGHBOUR_REJECT', 32), 'ownership_acceptance_rate': 58.1142}`

## Priority 2: Preserve decision-trace regression gates in QA.4.0

Any ownership change must keep EntityDecisionTrace outcomes explainable and must not silently alter decisions without a before/after trace diff.

- Engineering impact: **Medium**
- Expected benchmark improvement: Process quality; prevents opaque regressions
- Evidence: `{'beams_analysed': 11}`

## Priority 3: Separate Manual-crop GT issues (QA.3.2) from Ownership defects

QA.3.2 showed Manual crops are unreliable. Ownership improvements should be validated against decision traces and entity registries, not Manual PNG IoU alone.

- Engineering impact: **Medium**
- Expected benchmark improvement: Cleaner measurement of true ownership gains
- Evidence: `{'conflict_frequency': 16.3627, 'average_score_margin': 0.0}`
