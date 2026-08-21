# Review B103

- Fourth Set provenance: Fourth
- Context source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\context\B103.png`
- Detail source: B.3 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B3_target_anchor_geometry_context_recovery\review\B103\selected\detail.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: True
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY", "STIRRUP_SEMANTIC_COMPLEXITY", "LIMITED_RENDER", "OTHER_HIGH_INFORMATION_COMPLEXITY"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": [], "mixed_source": true, "deterministic_group_count": 5}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: True
- usable: True status=OK

- G1 TOP / 3-Y16 / count 3 / role MAIN / length UNKNOWN / span UNKNOWN
- G2 BOTTOM / 3-Y20 / count 3 / role MAIN / length UNKNOWN / span UNKNOWN

Stirrups:

- 3L-Y10@100C/C conf=0.95

## Deterministic (detected / R.1)

- BOTTOM / 5Y20 / count 5 / role MAIN
- TOP / 3Y16 / count 3 / role EXTRA
- TOP / 3Y20 / count 3 / role MAIN
- SPACER / 2Y25 / count 2 / role SPACER
- STIRRUP / 3L-Y10 / count 3 / role STIRRUP

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'ROLE_ONLY_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 3Y16 / count 3 / role MAIN
DETERMINISTIC:
  TOP / 3Y16 / count 3 / role EXTRA
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE DISAGREE
  COUNT EXACT

VISION ONLY: BOTTOM / 3-Y20 / role MAIN
DETERMINISTIC ONLY: BOTTOM / 5Y20 / role MAIN
DETERMINISTIC ONLY: OTHER / 2Y25 / role SPACER
DETERMINISTIC ONLY: TOP / 3Y20 / role MAIN