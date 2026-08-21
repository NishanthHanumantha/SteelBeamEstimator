# Review B46

- Fourth Set provenance: Fourth
- Context source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\context\final\B46.png`
- Detail source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\detail\B46.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'DETAIL_VERTICAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: True
- Why selected: {"strata": ["SIMPLE_LONGITUDINAL", "SAME_SPEC_DISTINCT_GROUPS", "LIMITED_RENDER"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": [], "mixed_source": true, "deterministic_group_count": 2}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: True
- usable: True status=OK

- G1 TOP / 4-Y20 / count 4 / role MAIN / length LONGER / span FULL_SPAN
- G2 BOTTOM / 4-Y20 / count 4 / role MAIN / length LONGER / span FULL_SPAN

Stirrups:

- 4L-Y10@100/150/100C/C conf=0.95

## Deterministic (detected / R.1)

- BOTTOM / 4Y20 / count 4 / role MAIN
- TOP / 4Y20 / count 4 / role MAIN

## Automated comparison (not ground truth)

- taxonomy: ['STIRRUP_DISAGREEMENT']

VISION:
  BOTTOM / 4Y20 / count 4 / role MAIN
DETERMINISTIC:
  BOTTOM / 4Y20 / count 4 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION:
  TOP / 4Y20 / count 4 / role MAIN
DETERMINISTIC:
  TOP / 4Y20 / count 4 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT
