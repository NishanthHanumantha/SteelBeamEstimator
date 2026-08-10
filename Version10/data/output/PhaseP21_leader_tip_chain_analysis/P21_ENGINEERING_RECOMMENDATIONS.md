# P2.1 Engineering Recommendations

DIAGNOSTIC ONLY — do not implement production rule changes in this phase.

Recommended option: `OPTION 2 - Leader-chain evidence enhancement`

Strong chain+bar+context evidence (Policy E/C) can safely recover at least the HIGH candidate without global envelope expansion. Geometric-only Policy D recovers more volume (4 SAFE) but lacks bar proximity and should not be used alone.

## Incorporate later (if production phase approved)
- leader_chain_continuity
- leader_to_bar_proximity
- target_beam_context
- endpoint_near_envelope OR longitudinal_overlap
- explicit neighbour_ambiguity == FALSE
- inside_other_beam_envelope == FALSE

## Do NOT use alone
- distance_to_envelope alone (arbitrary expansion)
- neighbour_ambiguity cases
- inside_other_beam_envelope
- far_outside spatial class
- points_toward_target_beam without bar proximity

## Case taxonomy (5 eligible)
[
  {
    "stable_key": "B16::LDR::7A1FFD68",
    "beam_id": "B16",
    "leader_id": "LDR::7A1FFD68",
    "case": "B",
    "case_meaning": "Associated with beam but rejected because R2 tip test is strict"
  },
  {
    "stable_key": "B18::LDR::0A172EB7",
    "beam_id": "B18",
    "leader_id": "LDR::0A172EB7",
    "case": "B",
    "case_meaning": "Associated with beam but rejected because R2 tip test is strict"
  },
  {
    "stable_key": "B18::LDR::77270BAC",
    "beam_id": "B18",
    "leader_id": "LDR::77270BAC",
    "case": "B",
    "case_meaning": "Associated with beam but rejected because R2 tip test is strict"
  },
  {
    "stable_key": "B18::LDR::FCC2C11A",
    "beam_id": "B18",
    "leader_id": "LDR::FCC2C11A",
    "case": "B",
    "case_meaning": "Associated with beam but rejected because R2 tip test is strict"
  },
  {
    "stable_key": "B19::LDR::4D6F2B85",
    "beam_id": "B19",
    "leader_id": "LDR::4D6F2B85",
    "case": "B",
    "case_meaning": "Associated with beam but rejected because R2 tip test is strict"
  }
]
