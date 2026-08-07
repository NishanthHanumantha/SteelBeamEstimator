# Engineering Recommendations — QA.3.1

Based ONLY on diagnostic evidence. No code was modified in this phase.

## Hypothesis

- ownership_or_scoping_before_render_is_dominant: **True**
- renderer_mostly_faithful_to_owned_set: **True**
- evidence_confidence: **High**

## Priorities

### Priority 1: Ownership

- Frequency: 7
- Supporting beams: B14, B15, B16, B18, B19, B22, B46
- Estimated impact: High
- Recommendation: Priority confirmed by diagnostics: ownership/scoping fails before render on multiple beams. Investigate Ownership failures first (n=7).
- Note: Deferred to next engineering phase

### Priority 2: Annotation Association

- Frequency: 0
- Supporting beams: -
- Estimated impact: Medium-High impact on Bar Matching / diameter roles
- Recommendation: Repair leader-to-beam association for multi-beam clusters and neighbour-side marks.
- Note: Deferred to next engineering phase

### Priority 3: Crop Window

- Frequency: 0
- Supporting beams: -
- Estimated impact: Medium impact on incomplete crops before ownership
- Recommendation: Review adaptive extent margins where annotation/leader clipping is flagged.
- Note: Deferred to next engineering phase
