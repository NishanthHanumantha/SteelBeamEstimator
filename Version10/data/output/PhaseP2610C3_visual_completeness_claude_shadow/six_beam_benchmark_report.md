# P2.6.10-C.3 six-beam Claude Vision control report

Shadow only. Manual/R1/P2.6.9 disagreement is preserved as provenance, not silently resolved.

## Fourth / B141

- selected context source: B.1
- selected detail source: B.1
- completeness gate: VISION_READY_WITH_LIMITATIONS
- gate reasons: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'MINOR_CLIP_OR_SLIVER']
- Claude called: True reason=SIX_BEAM_CONTROL skip=None
- target identified: True assoc_conf=0.95
- neighbor evidence detected: True
- usable: True unusable=None
- Claude groups: [{"layer": "TOP", "role": "MAIN", "spec": "5-Y20", "support_scope": "FULL_SPAN", "confidence": 0.95, "evidence": "Green reinforcement line at top of beam section, labeled 5-Y20 in magenta, visible in both context and detail images"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5-Y16", "support_scope": "FULL_SPAN", "confidence": 0.95, "evidence": "Green reinforcement line at bottom of beam section, labeled 5-Y16 in magenta, visible in detail image"}]
- Claude stirrups: [{"spec": "4L-Y8@100C/C", "confidence": 0.95}]
- P2.6.9 expected count: 2
- deterministic/R1 count: 1
- manual notes: ['Phase sketch: TOP 5-Y20 and BOTTOM 5-Y16 as distinct groups.', 'DXF R.1: TOP MAIN 5-Y16 plus an unclassified stirrup string 4L-Y8@\\X100C/C.', 'Repository DXF wins. B141 is not a B128-style same-specification/different-layer case. Leader/spatial ambiguity is recorded separately from physical-group identity.']
- taxonomy: VISION_DISAGREEMENT
- vs P269: {"expected_count": 2, "predicted_count": 2, "matched": [], "missing": [{"layer": "STIRRUP", "role": "STIRRUP", "spec": "4LY8@\\X100C/C"}, {"layer": "TOP", "role": "MAIN", "spec": "5Y16"}], "spurious": [{"layer": "BOTTOM", "role": "MAIN", "spec": "5Y16"}, {"layer": "TOP", "role": "MAIN", "spec": "5Y20"}], "correctly_matched_count": 0, "missing_count": 2, "spurious_count": 2, "merged_distinct_groups": 0, "identity_rule": "layer+role+specification"}

## Fourth / B66

- selected context source: B.1
- selected detail source: B.2
- completeness gate: VISION_READY_WITH_LIMITATIONS
- gate reasons: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Claude called: True reason=SIX_BEAM_CONTROL skip=None
- target identified: True assoc_conf=0.95
- neighbor evidence detected: True
- usable: True unusable=None
- Claude groups: [{"layer": "TOP", "role": "MAIN", "spec": "5Y16", "support_scope": "FULL_SPAN", "confidence": 0.92, "evidence": "Magenta annotation 5-Y16 positioned above beam centerline in detail view, with visual bars shown in green at top layer spanning full length"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5Y20", "support_scope": "FULL_SPAN", "confidence": 0.9, "evidence": "Magenta annotation 5-Y20 positioned below beam centerline in detail view, with visual bars shown in green at bottom layer spanning full length"}]
- Claude stirrups: [{"spec": "4L-Y8@100/125/100C/C", "confidence": 0.93}]
- P2.6.9 expected count: 3
- deterministic/R1 count: 3
- manual notes: []
- taxonomy: VISION_DISAGREEMENT
- vs P269: {"expected_count": 3, "predicted_count": 2, "matched": [], "missing": [{"layer": "BOTTOM", "role": "MAIN", "spec": "4Y25"}, {"layer": "STIRRUP", "role": "STIRRUP", "spec": "4LY8"}, {"layer": "TOP", "role": "MAIN", "spec": "5Y20"}], "spurious": [{"layer": "BOTTOM", "role": "MAIN", "spec": "5Y20"}, {"layer": "TOP", "role": "MAIN", "spec": "5Y16"}], "correctly_matched_count": 0, "missing_count": 3, "spurious_count": 2, "merged_distinct_groups": 0, "identity_rule": "layer+role+specification"}

## Fourth / B161

- selected context source: B.1
- selected detail source: B.1
- completeness gate: VISION_READY_WITH_LIMITATIONS
- gate reasons: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'MINOR_CLIP_OR_SLIVER']
- Claude called: True reason=SIX_BEAM_CONTROL skip=None
- target identified: True assoc_conf=0.95
- neighbor evidence detected: True
- usable: True unusable=None
- Claude groups: [{"layer": "TOP", "role": "MAIN", "spec": "4-Y20", "support_scope": "FULL_SPAN", "confidence": 0.95, "evidence": "Top layer green bars with 4-Y20 annotation centered above beam, spanning full length"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "4-Y25", "support_scope": "FULL_SPAN", "confidence": 0.92, "evidence": "Bottom layer green bars with 4-Y25 annotation at mid-span, visible spanning full length"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "4-Y16", "support_scope": "FULL_SPAN", "confidence": 0.92, "evidence": "Bottom layer green bars with 4-Y16 annotation adjacent to 4-Y25 at mid-span"}, {"layer": "TOP", "role": "EXTRA", "spec": "4-Y16", "support_scope": "LEFT_SUPPORT", "confidence": 0.88, "evidence": "Top layer bars extending from left support, dimension 800 shown, red dots at support"}, {"layer": "TOP", "role": "EXTRA", "spec": "4-Y16", "support_scope": "RIGHT_SUPPORT", "confidence": 0.88, "evidence": "Top layer bars extending from right support, dimension 800 shown, red dots at support"}]
- Claude stirrups: [{"spec": "4L-Y8@100C/C", "confidence": 0.93}]
- P2.6.9 expected count: 6
- deterministic/R1 count: 6
- manual notes: ['R.1 groups.json merged BOTTOM_EXTRA labels 3Y16+3Y20 into one bucket. Expected groups are derived from annotations, not that merged bucket.']
- taxonomy: VISION_DISAGREEMENT
- vs P269: {"expected_count": 6, "predicted_count": 5, "matched": [{"layer": "TOP", "role": "EXTRA", "spec": "4Y16"}], "missing": [{"layer": "BOTTOM", "role": "EXTRA", "spec": "3Y16"}, {"layer": "BOTTOM", "role": "EXTRA", "spec": "3Y20"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "3Y20"}, {"layer": "STIRRUP", "role": "STIRRUP", "spec": "4LY8"}, {"layer": "TOP", "role": "MAIN", "spec": "4Y25"}], "spurious": [{"layer": "BOTTOM", "role": "MAIN", "spec": "4Y16"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "4Y25"}, {"layer": "TOP", "role": "MAIN", "spec": "4Y20"}], "correctly_matched_count": 1, "missing_count": 5, "spurious_count": 3, "merged_distinct_groups": 0, "identity_rule": "layer+role+specification"}

## Fifth / B128

- selected context source: B.1
- selected detail source: B.1
- completeness gate: VISION_READY_WITH_LIMITATIONS
- gate reasons: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Claude called: True reason=SIX_BEAM_CONTROL skip=None
- target identified: True assoc_conf=0.95
- neighbor evidence detected: True
- usable: True unusable=None
- Claude groups: [{"layer": "TOP", "role": "MAIN", "spec": "5Y20", "support_scope": "FULL_SPAN", "confidence": 0.95, "evidence": "Green line at top of beam with 5-Y20 annotations at multiple locations along span, dimension 2350 shown"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5Y25", "support_scope": "LEFT_SUPPORT", "confidence": 0.9, "evidence": "Green lines at bottom left support region with 5-Y25 annotation visible"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "3Y20", "support_scope": "LEFT_SUPPORT", "confidence": 0.85, "evidence": "Green line at bottom left support with 3-Y20 annotation near column junction"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5Y25", "support_scope": "RIGHT_SUPPORT", "confidence": 0.9, "evidence": "Green lines at bottom right support region with 5-Y25 annotation visible at right end"}]
- Claude stirrups: [{"spec": "5L-Y12@100C/C", "confidence": 0.95}]
- P2.6.9 expected count: 3
- deterministic/R1 count: 1
- manual notes: ['Phase drawing sketch matches two 3-Y16 groups (TOP and BOTTOM).', 'R.1 associated only one 3-Y16 annotation to TOP_MAIN; the bottom group is a physical-layer control overlay, not a second parsed annotation.']
- taxonomy: VISION_DISAGREEMENT
- vs P269: {"expected_count": 3, "predicted_count": 4, "matched": [], "missing": [{"layer": "BOTTOM", "role": "MAIN", "spec": "3Y16"}, {"layer": "STIRRUP", "role": "STIRRUP", "spec": "2LY8@\\X100/150/100C/C"}, {"layer": "TOP", "role": "MAIN", "spec": "3Y16"}], "spurious": [{"layer": "BOTTOM", "role": "MAIN", "spec": "3Y20"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5Y25"}, {"layer": "TOP", "role": "MAIN", "spec": "5Y20"}], "correctly_matched_count": 0, "missing_count": 3, "spurious_count": 3, "merged_distinct_groups": 0, "identity_rule": "layer+role+specification"}

## Fifth / B55

- selected context source: B.1
- selected detail source: B.1
- completeness gate: VISION_READY_WITH_LIMITATIONS
- gate reasons: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_VERTICAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Claude called: True reason=SIX_BEAM_CONTROL skip=None
- target identified: True assoc_conf=0.95
- neighbor evidence detected: False
- usable: True unusable=None
- Claude groups: [{"layer": "TOP", "role": "MAIN", "spec": "3Y16", "support_scope": "LEFT_SUPPORT", "confidence": 0.92, "evidence": "3-Y16 annotation at left support with dimension 1400, shown in green layer at top of beam section"}, {"layer": "TOP", "role": "EXTRA", "spec": "5Y20", "support_scope": "BOTH_SUPPORTS", "confidence": 0.9, "evidence": "5-Y20 annotations visible at both left support (mid-span region) and right support, shown in green layer at top"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5Y20", "support_scope": "FULL_SPAN", "confidence": 0.88, "evidence": "5-Y20 annotation at bottom center of beam section, shown in green layer spanning full length"}]
- Claude stirrups: [{"spec": "3L-Y8@100C/C", "confidence": 0.93}]
- P2.6.9 expected count: 5
- deterministic/R1 count: 5
- manual notes: ['Phase sketch: TOP MAIN 3-Y25, TOP EXTRA 2-Y16, BOTTOM MAIN 3-Y20, BOTTOM EXTRA 2-Y16, STIRRUP 3L-Y10@100/125/100 C/C.', 'DXF R.1: TOP MAIN 3-Y20, TOP EXTRA 2-Y16, BOTTOM MAIN 3-Y25, BOTTOM EXTRA 3-Y25, STIRRUP 3L-Y10@100/125/100C/C.', 'Repository DXF wins. The same-layer multi-group control is BOTTOM MAIN 3-Y25 vs BOTTOM EXTRA 3-Y25, not two 2-Y16 groups.']
- taxonomy: VISION_DISAGREEMENT
- vs P269: {"expected_count": 5, "predicted_count": 3, "matched": [], "missing": [{"layer": "BOTTOM", "role": "EXTRA", "spec": "3Y25"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "3Y25"}, {"layer": "STIRRUP", "role": "STIRRUP", "spec": "3LY10"}, {"layer": "TOP", "role": "EXTRA", "spec": "2Y16"}, {"layer": "TOP", "role": "MAIN", "spec": "3Y20"}], "spurious": [{"layer": "BOTTOM", "role": "MAIN", "spec": "5Y20"}, {"layer": "TOP", "role": "EXTRA", "spec": "5Y20"}, {"layer": "TOP", "role": "MAIN", "spec": "3Y16"}], "correctly_matched_count": 0, "missing_count": 5, "spurious_count": 3, "merged_distinct_groups": 0, "identity_rule": "layer+role+specification"}

## Fifth / B65

- selected context source: B.1
- selected detail source: B.1
- completeness gate: VISION_READY_WITH_LIMITATIONS
- gate reasons: ['CONTEXT_CLIP', 'CONTEXT_HORIZONTAL_TRUNCATION', 'CONTEXT_VERTICAL_TRUNCATION', 'DETAIL_CLIP', 'DETAIL_HORIZONTAL_TRUNCATION', 'MINOR_CLIP_OR_SLIVER']
- Claude called: True reason=SIX_BEAM_CONTROL skip=None
- target identified: True assoc_conf=0.95
- neighbor evidence detected: True
- usable: True unusable=None
- Claude groups: [{"layer": "TOP", "role": "MAIN", "spec": "2Y16", "support_scope": "LEFT_SUPPORT", "confidence": 0.92, "evidence": "Two red bars visible at top left support, annotation '2-Y16' with 850mm and 1800mm dimensions indicating left support zone"}, {"layer": "TOP", "role": "EXTRA", "spec": "5Y16", "support_scope": "RIGHT_SUPPORT", "confidence": 0.9, "evidence": "Annotation '5-Y16' visible at top right region with single red bar shown at right support"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "5Y20", "support_scope": "FULL_SPAN", "confidence": 0.93, "evidence": "Two green bars visible running full span at bottom layer, annotation '5-Y20' centered below beam"}]
- Claude stirrups: [{"spec": "4L-Y8@100/175/100C/C", "confidence": 0.95}]
- P2.6.9 expected count: 6
- deterministic/R1 count: 7
- manual notes: ['Two BOTTOM EXTRA groups share diameter 16 but different counts (4-Y16 vs 2-Y16) and must remain distinct.']
- taxonomy: VISION_DISAGREEMENT
- vs P269: {"expected_count": 6, "predicted_count": 3, "matched": [], "missing": [{"layer": "BOTTOM", "role": "EXTRA", "spec": "2Y16"}, {"layer": "BOTTOM", "role": "EXTRA", "spec": "4Y16"}, {"layer": "BOTTOM", "role": "MAIN", "spec": "4Y20"}, {"layer": "STIRRUP", "role": "STIRRUP", "spec": "3LY10"}, {"layer": "TOP", "role": "EXTRA", "spec": "2Y16"}, {"layer": "TOP", "role": "MAIN", "spec": "3Y20"}], "spurious": [{"layer": "BOTTOM", "role": "MAIN", "spec": "5Y20"}, {"layer": "TOP", "role": "EXTRA", "spec": "5Y16"}, {"layer": "TOP", "role": "MAIN", "spec": "2Y16"}], "correctly_matched_count": 0, "missing_count": 6, "spurious_count": 3, "merged_distinct_groups": 1, "identity_rule": "layer+role+specification"}
