# B98A Root Cause Report — P2.5.0.2

- Actual top reinforcement: `OWN::B98A::1247FFE`
- Outcome: `OUTCOME_B_rejected_BAR_not_actual_top__actual_is_OWN_LWPOLYLINE`
- ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY: **True**

## Rejected BAR classifications

- `BAR::E6591903` → **FALSE_CANDIDATE** (HIGH): {"y_offset_mm": 69170.672, "depth_mm": 600.0, "y_offset_to_depth_ratio": 115.28, "dxf_handle": "11CD1B5", "layer": "-STR-REINF", "t18_reason": "bar_y_outside_reinforcement_elevation", "actual_top_is": "OWN::B98A::1247FFE", "note": "Real -STR-REINF LINE exists at a different drawing elevation. R.3.1 assigned beam_id by X-overlap heuristics, but geometry is not this beam's top reinforcement. Actual top bar is OWN::* LWPOLYLINE on -STR-BEAM inside the envelope."}
- `BAR::4D469A4E` → **FALSE_CANDIDATE** (HIGH): {"y_offset_mm": 68170.672, "depth_mm": 600.0, "y_offset_to_depth_ratio": 113.62, "dxf_handle": "11CD1B7", "layer": "-STR-REINF", "t18_reason": "bar_y_outside_reinforcement_elevation", "actual_top_is": "OWN::B98A::1247FFE", "note": "Real -STR-REINF LINE exists at a different drawing elevation. R.3.1 assigned beam_id by X-overlap heuristics, but geometry is not this beam's top reinforcement. Actual top bar is OWN::* LWPOLYLINE on -STR-BEAM inside the envelope."}

## Annotation chain

```json
{
  "beam_id": "B98A",
  "annotation_id": "ANN-2a9913fa",
  "raw_text": "4-Y25",
  "annotation_position": {
    "x": 31653409.98419774,
    "y": -21208789.1063728
  },
  "leader_id": "LDR::1812F192",
  "leader_tip": {
    "x": 31653309.90820159,
    "y": -21208319.09241375
  },
  "leader_tail": {
    "x": 31653413.33937468,
    "y": -21208721.80721938
  },
  "leader_tip_to_tail_mm": 415.785,
  "leader_tail_to_annotation_mm": 67.383,
  "accepted_annotation_record": {
    "id": "ANN-2a9913fa",
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
      "annotation_id": "ANN-2a9913fa",
      "text": "4-Y25",
      "leaders": [
        "LDR::1812F192"
      ],
      "describes": [
        "LDR::1812F192",
        "OWN::B98A::1247FFE"
      ],
      "semantic_id": "SEM::ANN-2a9913fa",
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
    "LDR::1812F192",
    "OWN::B98A::1247FFE"
  ],
  "own_entity": {
    "id": "OWN::B98A::1247FFE",
    "attributes": {
      "handle": "1247FFE",
      "entity_type": "LWPOLYLINE",
      "ownership": "HIGH",
      "role": "TOP_BAR",
      "layer": "-STR-BEAM",
      "reasons": [
        "inside_envelope",
        "distance_to_axis=407.3mm",
        "parallel_to_axis",
        "inside_top_bar_band",
        "inside_stirrup_band"
      ],
      "confidence_score": 0.97
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
    "describes \u2192 OWN::B98A::1247FFE",
    "P2.5.0 evidence package (annotations+leaders only; reinforcement=[])"
  ]
}
```
