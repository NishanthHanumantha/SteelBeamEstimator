# Fourth Set Failure Analysis (P2.4)

## Top 3 root causes

- `QUANTITY_RESOLUTION`: count=185 (23.99% of failures)
- `ROLE_RESOLUTION`: count=144 (18.68% of failures)
- `DIAMETER_RESOLUTION`: count=111 (14.4% of failures)

## Beam summary (priority + meaningful failures)

| Beam | GT | Det | Match | Miss | Extra | Det% | Match% | FirstFail | Reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| B10 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | ABSENT_FROM_FOURTH_SET_GT | beam_not_in_fourth_set_estimator |
| B12 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | ABSENT_FROM_FOURTH_SET_GT | beam_not_in_fourth_set_estimator |
| B13 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | ABSENT_FROM_FOURTH_SET_GT | beam_not_in_fourth_set_estimator |
| B14 | 10 | 10 | 3 | 3 | 1 | 100.0 | 30.0 | LEADER_CHAIN | leader_broken_chain |
| B15 | 9 | 9 | 2 | 3 | 4 | 100.0 | 22.22 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B16 | 7 | 7 | 2 | 0 | 5 | 100.0 | 28.57 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B18 | 10 | 10 | 1 | 3 | 0 | 100.0 | 10.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B19 | 9 | 9 | 0 | 3 | 2 | 100.0 | 0.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B22 | 10 | 10 | 1 | 7 | 0 | 100.0 | 10.0 | LEADER_CHAIN | leader_broken_chain |
| B23 | 8 | 8 | 1 | 6 | 0 | 100.0 | 12.5 | LEADER_CHAIN | leader_broken_chain |
| B29 | 7 | 7 | 1 | 0 | 0 | 100.0 | 14.29 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B42A | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | QUANTITY_RESOLUTION | role_missing_role |
| B45 | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | ROLE_RESOLUTION | role_missing_role |
| B46 | 6 | 6 | 2 | 4 | 0 | 100.0 | 33.33 | ROLE_RESOLUTION | role_missing_role |
| B8 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | ABSENT_FROM_FOURTH_SET_GT | beam_not_in_fourth_set_estimator |
| B9 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | ABSENT_FROM_FOURTH_SET_GT | beam_not_in_fourth_set_estimator |
| B100 | 7 | 7 | 2 | 2 | 0 | 100.0 | 28.57 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B100A | 6 | 6 | 1 | 4 | 0 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B101 | 7 | 7 | 3 | 2 | 0 | 100.0 | 42.86 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B101A | 14 | 14 | 1 | 12 | 0 | 100.0 | 7.14 | LEADER_CHAIN | leader_broken_chain |
| B102 | 7 | 7 | 3 | 2 | 0 | 100.0 | 42.86 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B103 | 6 | 6 | 2 | 1 | 1 | 100.0 | 33.33 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B104 | 7 | 0 | 0 | 7 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B117 | 9 | 0 | 0 | 9 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B118 | 15 | 0 | 0 | 15 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B119 | 6 | 6 | 1 | 3 | 0 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B120 | 6 | 6 | 1 | 3 | 2 | 100.0 | 16.67 | LEADER_CHAIN | leader_broken_chain |
| B121 | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | ROLE_RESOLUTION | role_missing_role |
| B122 | 7 | 7 | 1 | 2 | 0 | 100.0 | 14.29 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B123 | 10 | 10 | 1 | 3 | 2 | 100.0 | 10.0 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B128 | 8 | 8 | 1 | 3 | 0 | 100.0 | 12.5 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B129 | 7 | 7 | 2 | 3 | 0 | 100.0 | 28.57 | ROLE_RESOLUTION | role_missing_role |
| B130 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B133 | 8 | 8 | 1 | 3 | 1 | 100.0 | 12.5 | QUANTITY_RESOLUTION | quantity_overcount |
| B133A | 7 | 7 | 1 | 3 | 1 | 100.0 | 14.29 | LEADER_CHAIN | leader_broken_chain |
| B134 | 6 | 6 | 1 | 3 | 2 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B134A | 3 | 3 | 1 | 0 | 2 | 100.0 | 33.33 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B135 | 22 | 22 | 0 | 20 | 0 | 100.0 | 0.0 | QUANTITY_RESOLUTION | quantity_overcount |
| B136 | 9 | 9 | 1 | 7 | 0 | 100.0 | 11.11 | LEADER_CHAIN | leader_broken_chain |
| B140 | 4 | 4 | 2 | 1 | 0 | 100.0 | 50.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B141 | 4 | 4 | 0 | 3 | 0 | 100.0 | 0.0 | ROLE_RESOLUTION | role_missing_role |
| B142 | 3 | 3 | 1 | 1 | 0 | 100.0 | 33.33 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B144 | 4 | 4 | 1 | 1 | 0 | 100.0 | 25.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B145 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B147 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B148 | 10 | 10 | 1 | 6 | 0 | 100.0 | 10.0 | QUANTITY_RESOLUTION | role_missing_role |
| B149 | 9 | 9 | 0 | 9 | 0 | 100.0 | 0.0 | LEADER_CHAIN | leader_wrong_target |
| B150 | 3 | 3 | 1 | 0 | 0 | 100.0 | 33.33 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B152 | 8 | 8 | 1 | 5 | 0 | 100.0 | 12.5 | LEADER_CHAIN | leader_broken_chain |
| B154 | 5 | 5 | 1 | 3 | 0 | 100.0 | 20.0 | QUANTITY_RESOLUTION | role_missing_role |
| B156 | 6 | 6 | 1 | 3 | 2 | 100.0 | 16.67 | DIAMETER_RESOLUTION | diameter_wrong_diameter |
| B158165 | 10 | 0 | 0 | 10 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B159 | 14 | 14 | 0 | 12 | 2 | 100.0 | 0.0 | VB1_INTEGRATION | not_consumed_by_vb1 |
| B161 | 6 | 6 | 1 | 1 | 3 | 100.0 | 16.67 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B164 | 9 | 9 | 1 | 7 | 0 | 100.0 | 11.11 | LEADER_CHAIN | leader_broken_chain |
| B165 | 7 | 7 | 1 | 3 | 0 | 100.0 | 14.29 | VB1_INTEGRATION | not_consumed_by_vb1 |
| B166 | 7 | 7 | 3 | 1 | 1 | 100.0 | 42.86 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B168 | 15 | 15 | 0 | 15 | 0 | 100.0 | 0.0 | ROLE_RESOLUTION | role_missing_role |
| B169 | 8 | 8 | 1 | 0 | 0 | 100.0 | 12.5 | ROLE_RESOLUTION | partial_role |
| B17 | 6 | 6 | 3 | 1 | 0 | 100.0 | 50.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B170 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | QUANTITY_RESOLUTION | role_missing_role |
| B173 | 3 | 3 | 2 | 1 | 0 | 100.0 | 66.67 | LEADER_CHAIN | leader_wrong_target |
| B174 | 3 | 3 | 1 | 1 | 0 | 100.0 | 33.33 | LEADER_CHAIN | leader_wrong_target |
| B175 | 4 | 2 | 1 | 2 | 0 | 50.0 | 25.0 | DIAMETER_RESOLUTION | dxf_geometry_present_but_not_detected_as_physical_bar |
| B176 | 14 | 14 | 0 | 14 | 0 | 100.0 | 0.0 | LEADER_CHAIN | leader_broken_chain |
| B177 | 3 | 3 | 1 | 2 | 0 | 100.0 | 33.33 | ANNOTATION_ASSOCIATION | annotation_wrong_annotation |
| B178 | 3 | 3 | 1 | 1 | 0 | 100.0 | 33.33 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B180 | 4 | 4 | 2 | 1 | 1 | 100.0 | 50.0 | ROLE_RESOLUTION | excel_wrong_role |
| B182 | 4 | 4 | 2 | 1 | 0 | 100.0 | 50.0 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B185 | 4 | 4 | 1 | 1 | 0 | 100.0 | 25.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B186 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B191 | 6 | 6 | 1 | 3 | 0 | 100.0 | 16.67 | LEADER_CHAIN | leader_broken_chain |
| B19A | 6 | 0 | 0 | 6 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B24 | 9 | 0 | 0 | 9 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B24A | 8 | 0 | 0 | 8 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B25 | 10 | 0 | 0 | 10 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B26 | 10 | 0 | 0 | 10 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B27 | 10 | 0 | 0 | 10 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | dxf_geometry_present_but_not_detected_as_physical_bar |
| B28 | 9 | 0 | 0 | 9 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | dxf_geometry_present_but_not_detected_as_physical_bar |
| B30 | 7 | 0 | 0 | 7 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B31 | 10 | 0 | 0 | 10 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B32 | 10 | 0 | 0 | 10 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B33 | 9 | 0 | 0 | 9 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B34 | 6 | 0 | 0 | 6 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B35 | 8 | 0 | 0 | 8 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B36 | 6 | 0 | 0 | 6 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B37 | 9 | 0 | 0 | 9 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B38 | 9 | 0 | 0 | 9 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B39 | 8 | 0 | 0 | 8 | 0 | 0.0 | 0.0 | PHYSICAL_BAR_DETECTION | no_physical_bar_or_text_primary_evidence |
| B42 | 8 | 8 | 3 | 3 | 1 | 100.0 | 37.5 | QUANTITY_RESOLUTION | quantity_overcount |
| B47 | 6 | 6 | 1 | 4 | 0 | 100.0 | 16.67 | ROLE_RESOLUTION | role_missing_role |
| B48 | 4 | 4 | 2 | 1 | 2 | 100.0 | 50.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B51 | 3 | 3 | 1 | 1 | 0 | 100.0 | 33.33 | ROLE_RESOLUTION | role_missing_role |
| B52 | 3 | 3 | 1 | 1 | 0 | 100.0 | 33.33 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B55 | 6 | 6 | 2 | 2 | 2 | 100.0 | 33.33 | ROLE_RESOLUTION | partial_role |
| B56 | 6 | 6 | 1 | 3 | 2 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B57 | 6 | 6 | 1 | 3 | 0 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B58 | 4 | 4 | 1 | 3 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B59 | 6 | 6 | 1 | 5 | 0 | 100.0 | 16.67 | ROLE_RESOLUTION | role_missing_role |
| B60 | 7 | 7 | 1 | 1 | 0 | 100.0 | 14.29 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B61 | 7 | 7 | 2 | 1 | 0 | 100.0 | 28.57 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B61A | 7 | 0 | 0 | 7 | 0 | 0.0 | 0.0 | DXF_GEOMETRY | no_dxf_geometry_for_beam_role |
| B63 | 8 | 8 | 0 | 4 | 1 | 100.0 | 0.0 | ROLE_RESOLUTION | role_missing_role |
| B64 | 6 | 6 | 1 | 3 | 0 | 100.0 | 16.67 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B65 | 8 | 8 | 0 | 5 | 0 | 100.0 | 0.0 | QUANTITY_RESOLUTION | quantity_overcount |
| B66 | 6 | 6 | 0 | 3 | 0 | 100.0 | 0.0 | QUANTITY_RESOLUTION | quantity_overcount |
| B68 | 8 | 8 | 0 | 4 | 1 | 100.0 | 0.0 | QUANTITY_RESOLUTION | quantity_overcount |
| B68A | 9 | 9 | 0 | 2 | 2 | 100.0 | 0.0 | QUANTITY_RESOLUTION | excel_wrong_diameter |
| B69 | 8 | 8 | 1 | 3 | 1 | 100.0 | 12.5 | QUANTITY_RESOLUTION | quantity_overcount |
| B70 | 8 | 8 | 0 | 3 | 1 | 100.0 | 0.0 | QUANTITY_RESOLUTION | excel_wrong_diameter |
| B70A | 9 | 9 | 0 | 3 | 0 | 100.0 | 0.0 | QUANTITY_RESOLUTION | excel_wrong_diameter |
| B71 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B72 | 4 | 4 | 1 | 1 | 2 | 100.0 | 25.0 | QUANTITY_RESOLUTION | excel_wrong_diameter |
| B73 | 4 | 4 | 2 | 1 | 0 | 100.0 | 50.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B74 | 9 | 9 | 2 | 4 | 0 | 100.0 | 22.22 | ROLE_RESOLUTION | role_missing_role |
| B75 | 9 | 9 | 1 | 6 | 0 | 100.0 | 11.11 | LEADER_CHAIN | leader_broken_chain |
| B76 | 9 | 9 | 2 | 4 | 0 | 100.0 | 22.22 | ROLE_RESOLUTION | role_missing_role |
| B77 | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | ROLE_RESOLUTION | role_missing_role |
| B78 | 6 | 6 | 1 | 4 | 0 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B79 | 4 | 4 | 2 | 1 | 0 | 100.0 | 50.0 | LEADER_CHAIN | leader_wrong_target |
| B80 | 8 | 8 | 0 | 8 | 0 | 100.0 | 0.0 | LEADER_CHAIN | leader_wrong_target |
| B82 | 4 | 4 | 1 | 3 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B83 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | QUANTITY_RESOLUTION | role_missing_role |
| B85 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | QUANTITY_RESOLUTION | role_missing_role |
| B86 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B88 | 4 | 4 | 1 | 1 | 0 | 100.0 | 25.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B89 | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | ROLE_RESOLUTION | role_missing_role |
| B91 | 4 | 4 | 1 | 1 | 0 | 100.0 | 25.0 | QUANTITY_RESOLUTION | excel_wrong_diameter |
| B92 | 4 | 4 | 1 | 2 | 0 | 100.0 | 25.0 | QUANTITY_RESOLUTION | role_missing_role |
| B93 | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | LEADER_CHAIN | leader_wrong_target |
| B94 | 4 | 4 | 2 | 1 | 0 | 100.0 | 50.0 | DIAMETER_RESOLUTION | excel_wrong_diameter |
| B96 | 10 | 10 | 3 | 4 | 0 | 100.0 | 30.0 | QUANTITY_RESOLUTION | excel_wrong_quantity |
| B96A | 4 | 4 | 1 | 2 | 2 | 100.0 | 25.0 | ROLE_RESOLUTION | role_missing_role |
| B97 | 9 | 9 | 0 | 3 | 2 | 100.0 | 0.0 | QUANTITY_RESOLUTION | quantity_overcount |
| B97A | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | LEADER_CHAIN | leader_wrong_target |
| B98 | 6 | 6 | 1 | 3 | 0 | 100.0 | 16.67 | QUANTITY_RESOLUTION | quantity_overcount |
| B98A | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | LEADER_CHAIN | leader_wrong_target |
| B99 | 7 | 7 | 1 | 5 | 0 | 100.0 | 14.29 | ROLE_RESOLUTION | role_missing_role |
| B99A | 4 | 4 | 2 | 2 | 0 | 100.0 | 50.0 | LEADER_CHAIN | leader_broken_chain |

## Top reinforcement

- GT top bars: 248
- Matched: 99
- Unmatched: 96
- Dominant failure: `DXF_GEOMETRY`
- Missing/failing top bars are dominated by DXF_GEOMETRY (49/149 = 32.9%).

## Problem beams B10/B12/B13

- **B10**: present=False — NOT_A_FOURTH_SET_BEAM — cannot attribute Fourth Set render failure to this ID.
- **B12**: present=False — NOT_A_FOURTH_SET_BEAM — cannot attribute Fourth Set render failure to this ID.
- **B13**: present=False — NOT_A_FOURTH_SET_BEAM — cannot attribute Fourth Set render failure to this ID.

## Shared beams B8/B9/B10

Fourth Set shared-beam case is SIDE_FACE_REINFORCEMENT scope on ['B100A', 'B101A', 'B96A', 'B97A', 'B98A', 'B99A'], not B8/B9/B10.
