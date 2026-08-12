# B97A Root Cause Report — P2.5.0.2

- Actual top reinforcement: `OWN::B97A::1247FFF`
- Outcome: `OUTCOME_B_rejected_BAR_not_actual_top__actual_is_OWN_LWPOLYLINE`
- ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY: **True**

## Rejected BAR classifications

- `BAR::2B7B3233` → **FALSE_CANDIDATE** (HIGH): {"y_offset_mm": 24880.902, "depth_mm": 600.0, "y_offset_to_depth_ratio": 41.47, "dxf_handle": "1221B7C", "layer": "-STR-REINF", "t18_reason": "bar_y_outside_reinforcement_elevation", "actual_top_is": "OWN::B97A::1247FFF", "note": "Real -STR-REINF LINE exists at a different drawing elevation. R.3.1 assigned beam_id by X-overlap heuristics, but geometry is not this beam's top reinforcement. Actual top bar is OWN::* LWPOLYLINE on -STR-BEAM inside the envelope."}
- `BAR::5B1BFCC2` → **FALSE_CANDIDATE** (HIGH): {"y_offset_mm": 44357.592, "depth_mm": 600.0, "y_offset_to_depth_ratio": 73.93, "dxf_handle": "12469C4", "layer": "-STR-REINF", "t18_reason": "bar_y_outside_reinforcement_elevation", "actual_top_is": "OWN::B97A::1247FFF", "note": "Real -STR-REINF LINE exists at a different drawing elevation. R.3.1 assigned beam_id by X-overlap heuristics, but geometry is not this beam's top reinforcement. Actual top bar is OWN::* LWPOLYLINE on -STR-BEAM inside the envelope."}

## Annotation chain

```json
{
  "beam_id": "B97A",
  "annotation_id": "ANN-d7128f62",
  "raw_text": "4-Y25",
  "annotation_position": {
    "x": 31650705.70627044,
    "y": -21208789.1063728
  },
  "leader_id": "LDR::E83C245B",
  "leader_tip": {
    "x": 31650605.63027429,
    "y": -21208319.09241375
  },
  "leader_tail": {
    "x": 31650709.06144738,
    "y": -21208721.80721938
  },
  "leader_tip_to_tail_mm": 415.785,
  "leader_tail_to_annotation_mm": 67.383,
  "accepted_annotation_record": {
    "id": "ANN-d7128f62",
    "text": "4-Y25",
    "accepted": true,
    "accepted_rules": [
      "R3_ANNOTATION_VIA_CHAIN",
      "R5_NEIGHBOUR_REJECT"
    ],
    "rejected_rule": null,
    "ownership_reason": "leader_bar_chain_owned",
    "ownership_score": 0.65
  },
  "accepted_chains": [
    {
      "annotation_id": "ANN-d7128f62",
      "text": "4-Y25",
      "leaders": [
        "LDR::E83C245B"
      ],
      "describes": [
        "LDR::E83C245B",
        "OWN::B97A::1247FFF"
      ],
      "semantic_id": "SEM::ANN-d7128f62",
      "semantic_type": "BarCallout",
      "accepted": true,
      "accepted_rules": [
        "R3_ANNOTATION_VIA_CHAIN",
        "R5_NEIGHBOUR_REJECT"
      ],
      "rejected_rule": null,
      "ownership_reason": "leader_bar_chain_owned",
      "ownership_score": 0.65
    }
  ],
  "describes": [
    "LDR::E83C245B",
    "OWN::B97A::1247FFF"
  ],
  "own_entity": {
    "id": "OWN::B97A::1247FFF",
    "attributes": {
      "handle": "1247FFF",
      "entity_type": "LWPOLYLINE",
      "ownership": "HIGH",
      "role": "TOP_BAR",
      "layer": "-STR-BEAM",
      "reasons": [
        "overlap_pct=0.78",
        "distance_to_axis=407.3mm",
        "parallel_to_axis",
        "inside_top_bar_band",
        "inside_stirrup_band"
      ],
      "confidence_score": 0.82
    },
    "type": "OwnedEntity"
  },
  "evidence_package_reinforcement_count": 0,
  "why_accepted_chain_with_empty_reinforcement": "Accepted chain describes OWN::* (T16 OwnedEntity TOP_BAR / LWPOLYLINE on -STR-BEAM), not BAR::* (R.3.1 PhysicalBar). P2.5.0 evidence_pack only includes AnnotationGraph PhysicalBar nodes from accepted bar_results; OwnedEntity geometry is not mapped into reinforcement[].",
  "pipeline": [
    "DXF TEXT/MTEXT",
    "annotation extraction / normalization",
    "leader detection",
    "AnnotationGraph",
    "T18 accepted annotation + accepted_chains",
    "describes \u2192 OWN::B97A::1247FFF",
    "P2.5.0 evidence package (annotations+leaders only; reinforcement=[])"
  ]
}
```
