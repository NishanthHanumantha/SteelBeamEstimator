# Review B100

- Fourth Set provenance: Fourth
- Context source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\context\final\B100.png`
- Detail source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\detail\B100.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_VERTICAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: True
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY", "STIRRUP_SEMANTIC_COMPLEXITY", "LIMITED_RENDER"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": [], "mixed_source": true, "deterministic_group_count": 4}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 3-Y16 / count 3 / role MAIN / length SHORTER / span PARTIAL_SUPPORT
- G2 TOP / 3-Y20 / count 3 / role MAIN / length LONGER / span FULL_SPAN
- G3 BOTTOM / 2-Y20 / count 2 / role MAIN / length UNKNOWN / span FULL_SPAN

Stirrups:

- 3L-Y10@100C/C conf=0.95

## Deterministic (detected / R.1)

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

VISION:
  TOP / 3Y20 / count 3 / role MAIN
DETERMINISTIC:
  TOP / 3Y20 / count 3 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION ONLY: BOTTOM / 2-Y20 / role MAIN
DETERMINISTIC ONLY: OTHER / 2Y25 / role SPACER