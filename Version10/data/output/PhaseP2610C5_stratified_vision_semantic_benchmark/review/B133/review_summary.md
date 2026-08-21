# Review B133

- Fourth Set provenance: Fourth
- Context source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\context\final\B133.png`
- Detail source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\detail\final\B133.png`
- Visual gate: VISION_READY_WITH_LIMITATIONS
- Gate limitations: ['CONTEXT_CLIP', 'DETAIL_CLIP', 'MINOR_CLIP_OR_SLIVER']
- Mixed source: False
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY", "SAME_SPEC_DISTINCT_GROUPS", "STIRRUP_SEMANTIC_COMPLEXITY", "LIMITED_RENDER", "OTHER_HIGH_INFORMATION_COMPLEXITY"], "gate_status": "VISION_READY_WITH_LIMITATIONS", "new_strata": ["OTHER_HIGH_INFORMATION_COMPLEXITY", "SAME_SPEC_DISTINCT_GROUPS"], "mixed_source": false, "deterministic_group_count": 5}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 5-Y20 / count 5 / role MAIN / length LONGER / span FULL_SPAN
- G2 BOTTOM / 5-Y20 / count 5 / role MAIN / length LONGER / span FULL_SPAN
- G3 BOTTOM / 2-Y16 / count 2 / role EXTRA / length SHORTER / span PARTIAL_RIGHT

Stirrups:

- 4L-Y8@100/125/100C/C conf=0.9

## Deterministic (detected / R.1)

- BOTTOM / 3Y25 / count 3 / role MAIN
- TOP / 2Y16 / count 2 / role EXTRA
- TOP / 5Y20 / count 5 / role MAIN
- SPACER / 3Y25 / count 3 / role SPACER
- STIRRUP / 4L-Y8 / count 4 / role STIRRUP

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 5Y20 / count 5 / role MAIN
DETERMINISTIC:
  TOP / 5Y20 / count 5 / role MAIN
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE MATCH
  COUNT EXACT

VISION ONLY: BOTTOM / 2-Y16 / role EXTRA
VISION ONLY: BOTTOM / 5-Y20 / role MAIN
DETERMINISTIC ONLY: BOTTOM / 3Y25 / role MAIN
DETERMINISTIC ONLY: OTHER / 3Y25 / role SPACER
DETERMINISTIC ONLY: TOP / 2Y16 / role EXTRA