# P2.6.10-D.2 — Shadow Hybrid Semantic Resolver

MODEL_VERSION: 10.11.20
SHADOW ONLY. Structural hybrid application of the D.1 authority contract.
Not accuracy. Not production integration.

- LIVE_CLAUDE_CALL = False
- PRODUCTION_WRITE = False
- ENGINEERING_CHANGES = NONE

## Population

- discovered: 16
- expected: 16
- ok: True
- beam_ids: ['B100', 'B100A', 'B103', 'B119', 'B128', 'B129', 'B133', 'B139', 'B141', 'B161', 'B17', 'B46', 'B55', 'B65', 'B66', 'B68']

## Groups

{
  "matched_groups": 33,
  "vision_only_groups": 11,
  "deterministic_only_groups": 5,
  "ambiguous_groups": 1,
  "possible_duplicates": 2
}

## Field resolution

{
  "TARGET_IDENTITY": {
    "vision_accepted": 16
  },
  "LAYER": {
    "vision_accepted": 45,
    "conflicts_recorded": 8,
    "deterministic_authority_or_only": 5
  },
  "ROLE": {
    "vision_accepted": 45,
    "conflicts_recorded": 6,
    "deterministic_authority_or_only": 5
  },
  "BAR_COUNT": {
    "vision_accepted": 45,
    "deterministic_authority_or_only": 5,
    "conflicts_recorded": 7
  },
  "DIAMETER": {
    "vision_accepted": 45,
    "deterministic_authority_or_only": 5,
    "conflicts_recorded": 6
  },
  "SPECIFICATION": {
    "vision_accepted": 45,
    "conflicts_recorded": 31,
    "deterministic_authority_or_only": 5
  },
  "SUPPORT_SCOPE": {
    "vision_accepted": 42,
    "deterministic_fallback": 3,
    "conflicts_recorded": 13,
    "deterministic_authority_or_only": 5
  },
  "STIRRUP_IDENTIFICATION": {
    "vision_accepted": 16,
    "deterministic_authority_or_only": 10
  }
}

## Provenance (not accuracy)

{
  "counts": {
    "VISION": 299,
    "DETERMINISTIC": 43,
    "UNRESOLVED": 0
  },
  "total_fields": 342,
  "percent": {
    "VISION": 87.43,
    "DETERMINISTIC": 12.57,
    "UNRESOLVED": 0.0
  }
}

## Stirrups

{
  "vision_semantic_identification_accepted": 16,
  "deterministic_engineering_references_retained": 26,
  "conflicts_recorded": 0
}

## Engineering fields

{
  "deterministic_authority_retained": 66,
  "unavailable_cut_length_references": 12
}

No production interpretation change.
