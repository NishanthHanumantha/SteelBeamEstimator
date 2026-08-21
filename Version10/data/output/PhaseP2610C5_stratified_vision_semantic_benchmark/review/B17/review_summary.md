# Review B17

- Fourth Set provenance: Fourth
- Context source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\context\B17.png`
- Detail source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\detail\B17.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: False
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY", "SAME_SPEC_DISTINCT_GROUPS", "LIMITED_RENDER"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": [], "mixed_source": false, "deterministic_group_count": 4}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 2-Y20 / count 2 / role MAIN / length LONGER / span FULL_SPAN
- G2 BOTTOM / 2-Y20 / count 2 / role MAIN / length SHORTER / span PARTIAL_SUPPORT
- G3 BOTTOM / 2-Y16 / count 2 / role EXTRA / length SHORTER / span PARTIAL_SUPPORT

Stirrups:

- 2L-Y12@100C/C conf=0.9

## Deterministic (detected / R.1)

- BOTTOM / 2Y20 / count 2 / role MAIN
- TOP / 2Y16 / count 2 / role EXTRA
- TOP / 2Y20 / count 2 / role MAIN
- SPACER / 3Y25 / count 3 / role SPACER

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  BOTTOM / 2Y20 / count 2 / role MAIN
DETERMINISTIC:
  BOTTOM / 2Y20 / count 2 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION:
  TOP / 2Y20 / count 2 / role MAIN
DETERMINISTIC:
  TOP / 2Y20 / count 2 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION ONLY: BOTTOM / 2-Y16 / role EXTRA
DETERMINISTIC ONLY: OTHER / 3Y25 / role SPACER
DETERMINISTIC ONLY: TOP / 2Y16 / role EXTRA