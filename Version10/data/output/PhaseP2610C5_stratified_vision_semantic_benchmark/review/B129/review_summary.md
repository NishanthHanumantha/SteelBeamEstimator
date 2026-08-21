# Review B129

- Fourth Set provenance: Fourth
- Context source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\context\B129.png`
- Detail source: B.3 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B3_target_anchor_geometry_context_recovery\review\B129\selected\detail.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: True
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY", "LIMITED_RENDER"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": [], "mixed_source": true, "deterministic_group_count": 3}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 4-Y20 / count 4 / role MAIN / length LONGER / span FULL_SPAN
- G2 TOP / 2-Y16 / count 2 / role EXTRA / length SHORTER / span PARTIAL_SUPPORT
- G3 BOTTOM / 4-Y20 / count 4 / role MAIN / length LONGER / span FULL_SPAN
- G4 BOTTOM / 2-Y16 / count 2 / role EXTRA / length SHORTER / span PARTIAL_SUPPORT

Stirrups:

- 4L-Y12@100C/C conf=0.95

## Deterministic (detected / R.1)

- TOP / 2Y16 / count 2 / role EXTRA
- TOP / 4Y20 / count 4 / role MAIN
- SPACER / 3Y25 / count 3 / role SPACER

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 2Y16 / count 2 / role EXTRA
DETERMINISTIC:
  TOP / 2Y16 / count 2 / role EXTRA
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

VISION ONLY: BOTTOM / 2-Y16 / role EXTRA
VISION ONLY: BOTTOM / 4-Y20 / role MAIN
DETERMINISTIC ONLY: OTHER / 3Y25 / role SPACER