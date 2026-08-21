# Review B139

- Fourth Set provenance: Fourth
- Context source: B.2 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B2_render_quality_directional_recovery\context\final\B139.png`
- Detail source: B.3 `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseP2610B3_target_anchor_geometry_context_recovery\review\B139\selected\detail.png`
- Visual gate: VISION_READY
- Gate limitations: ['SUFFICIENT_TARGET_EVIDENCE']
- Mixed source: True
- Why selected: {"strata": ["MULTI_GROUP_LONGITUDINAL", "MAIN_EXTRA_COMPLEXITY"], "gate_status": "VISION_READY", "new_strata": [], "mixed_source": true, "deterministic_group_count": 2}

## Vision

- target identified: True confidence=0.95
- neighbour evidence: False
- usable: True status=OK

- G1 TOP / 5-Y16 / count 5 / role MAIN / length LONGER / span FULL_SPAN
- G2 BOTTOM / 5-Y20 / count 5 / role MAIN / length LONGER / span FULL_SPAN

Stirrups:

- 2L-Y8@100C/C conf=0.9

## Deterministic (detected / R.1)

- TOP / 5Y16 / count 5 / role EXTRA
- TOP / 5Y20 / count 5 / role MAIN

## Automated comparison (not ground truth)

- taxonomy: ['GROUP_STRUCTURE_DISAGREEMENT', 'ROLE_ONLY_DISAGREEMENT', 'STIRRUP_DISAGREEMENT']

VISION:
  TOP / 5Y16 / count 5 / role MAIN
DETERMINISTIC:
  TOP / 5Y16 / count 5 / role EXTRA
RESULT:
  LAYER MATCH
  SPEC MATCH
  PHYSICAL_GROUP MATCH
  ROLE DISAGREE
  COUNT EXACT

VISION ONLY: BOTTOM / 5-Y20 / role MAIN
DETERMINISTIC ONLY: TOP / 5Y20 / role MAIN