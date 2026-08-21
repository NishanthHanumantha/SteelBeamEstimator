# Review B68

- Fourth Set provenance: Fourth
- Context source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\context\final\B68.png`
- Detail source: B.3 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B3_target_anchor_geometry_context_recovery\review\B68\selected\detail.png`
- Visual gate: VISION_READY
- Gate limitations: ['SUFFICIENT_TARGET_EVIDENCE']
- Mixed source: True
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY", "STIRRUP_SEMANTIC_COMPLEXITY"], "gate_status": "VISION_READY", "new_strata": ["MAIN_EXTRA_COMPLEXITY", "MULTI_GROUP_LONGITUDINAL"], "mixed_source": true, "deterministic_group_count": 4}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 4-Y20 / count 4 / role MAIN / length LONGER / span FULL_SPAN
- G2 BOTTOM / 4-Y20 / count 4 / role MAIN / length LONGER / span FULL_SPAN
- G3 TOP / 4-Y16 / count 4 / role EXTRA / length SHORTER / span PARTIAL_RIGHT

Stirrups:

- 4L-Y8@100/150/100C/C conf=0.95

## Deterministic (detected / R.1)

- TOP / 4Y16 / count 4 / role EXTRA
- TOP / 4Y20 / count 4 / role MAIN
- SPACER / 2Y25 / count 2 / role SPACER
- STIRRUP / 4L-Y8 / count 4 / role STIRRUP

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 4Y16 / count 4 / role EXTRA
DETERMINISTIC:
  TOP / 4Y16 / count 4 / role EXTRA
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

VISION ONLY: BOTTOM / 4-Y20 / role MAIN
DETERMINISTIC ONLY: OTHER / 2Y25 / role SPACER