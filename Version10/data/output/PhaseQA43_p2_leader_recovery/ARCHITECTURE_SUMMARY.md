# QA.4.3 Architecture Summary

## Pipeline

```
Input (QA.4.1 DroppedEntityAudit)
  ↓
Dropped Leader Inventory (LEADER_CHAIN_FAILURE, Fourth Set)
  ↓
P2 Candidate Detection
  ↓
Spatial / Context Validation (QA.4.1 evidence flags)
  ↓
Eligibility (HIGH/MEDIUM; exclude FAR/neighbour/inside-other)
  ↓
Deduplication (accepted_node_ids + T18 leader_results)
  ↓
Existing T18 Ownership (leader_results / evaluate_leader)
  ↓
QA.4.3 Audit
  ↓
Regression / Determinism Gate
```

## Why P2 exists

QA.4.2 showed HIGH envelope satellites were already in T18 accepted nodes.
The remaining ownership gap class from QA.4.1 is LEADER_CHAIN_FAILURE (23).
P2 asks whether those leaders can safely re-enter the candidate path.

## What P2 may recover

- Leaders with HIGH/MEDIUM potential and non-contaminated geometry
- Only as recovery *candidates* passed to existing T18 evaluation

## What P2 must not recover

- Neighbour-ambiguous leaders
- Leaders inside another beam envelope
- Far-outside leaders
- Owned-elsewhere entities
- Anything via a second ownership score

## Why T18 remains authoritative

QA.4.3 reads `leader_results` / rejected annotations, or calls
`evaluate_leader` / `evaluate_annotation_chain` without changing rules.
It never writes BeamOwnership.json or mutates accepted_node_ids.

## Contamination prevention

Eligibility rejects neighbour_ambiguity and inside_other_beam_envelope.
Cross-beam accepted_node_ids checks block illegal multi-beam adds.

## Deduplication

If a leader is already in accepted_node_ids → ALREADY_IN_PRODUCTION_POOL.
If already in T18 leader_results as rejected → ownership_rejected,
recovery_candidate_added_to_pool = false (already scored).

## Production artefacts

Unchanged by design. Append-only QA.4.3 outputs only.
