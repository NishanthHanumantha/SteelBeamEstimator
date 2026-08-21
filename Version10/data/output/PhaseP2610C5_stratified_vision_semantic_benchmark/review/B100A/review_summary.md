# Review B100A

- Fourth Set provenance: Fourth
- Context source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\context\B100A.png`
- Detail source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\detail\B100A.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: False
- Why selected: {"strata": ["STIRRUP_SEMANTIC_COMPLEXITY", "LIMITED_RENDER"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": [], "mixed_source": false, "deterministic_group_count": 2}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: True
- usable: True status=OK

- G1 TOP / 4-Y25 / count 4 / role MAIN / length UNKNOWN / span FULL_SPAN
- G2 BOTTOM / 4-Y25 / count 4 / role MAIN / length UNKNOWN / span FULL_SPAN

Stirrups:

- 4L-Y10@100/150/100C/C conf=0.95

## Deterministic (detected / R.1)

- TOP / 4Y25 / count 4 / role MAIN
- STIRRUP / 4L-Y10 / count 4 / role STIRRUP

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 4Y25 / count 4 / role MAIN
DETERMINISTIC:
  TOP / 4Y25 / count 4 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION ONLY: BOTTOM / 4-Y25 / role MAIN