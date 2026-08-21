# Review B119

- Fourth Set provenance: Fourth
- Context source: B.1 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B1_population_generalization\context\B119.png`
- Detail source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\detail\final\B119.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: True
- Why selected: {"strata": ["SIMPLE_LONGITUDINAL", "STIRRUP_SEMANTIC_COMPLEXITY", "LIMITED_RENDER"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": ["LIMITED_RENDER", "SIMPLE_LONGITUDINAL", "STIRRUP_SEMANTIC_COMPLEXITY"], "mixed_source": true, "deterministic_group_count": 3}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 3-Y25 / count 3 / role MAIN / length LONGER / span FULL_SPAN
- G2 BOTTOM / 3L-Y10@100C/125/100/E / count 3 / role MAIN / length LONGER / span FULL_SPAN

Stirrups:

- 3L-Y10@100C/125/100/E conf=0.75

## Deterministic (detected / R.1)

- BOTTOM / 3Y16 / count 3 / role MAIN
- TOP / 3Y25 / count 3 / role MAIN
- STIRRUP / 3L-Y10 / count 3 / role STIRRUP

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 3Y25 / count 3 / role MAIN
DETERMINISTIC:
  TOP / 3Y25 / count 3 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION ONLY: BOTTOM / 3L-Y10@100C/125/100/E / role MAIN
DETERMINISTIC ONLY: BOTTOM / 3Y16 / role MAIN