# P2.5.0.1 Executive Summary — Evidence Spatial Sanity

- MODEL_VERSION: `10.6.1`
- MODE: `DIAGNOSTIC_ONLY`
- ENGINEERING_CHANGES: `NONE`
- Determinism: **PASS**
- Regression unchanged: **True**
- Fix applied: **True**

## Required answers

1. Why is B97A's crop ~47 m tall?  
   Crop height ≈ 47206.53000000119 mm because P2.5.0 included T18-rejected bars (esp. BAR::5B1BFCC2 at y-gap ≈ 43947.30999999866 mm) and expanded the evidence window to contain them.

2. Why is B98A's crop ~76 m tall?  
   Crop height ≈ 76101.44508749992 mm for the same reason — rejected far-elevation bars (dominant BAR::E6591903, y-gap ≈ 68690.66999999806 mm); rejected leader LDR::53A6EF71 also contributed downward expansion.

3. Which exact evidence object caused each expansion?  
   B97A: BAR::5B1BFCC2 (reinforcement). B98A: BAR::E6591903 (reinforcement).

4. Are BAR::2B7B3233 / BAR::5B1BFCC2 genuinely spatially associated with B97A?  
   NO. T18 rejected both with ownership_reason=bar_y_outside_reinforcement_elevation / R5_NEIGHBOUR_REJECT. They share AnnotationGraph beam_id=B97A and overlapping X, but Y is tens of metres outside the beam elevation band.

5. Are BAR::E6591903 / BAR::4D469A4E genuinely spatially associated with B98A?  
   NO. Same T18 rejection (bar_y_outside_reinforcement_elevation). Not genuinely spatially associated with B98A's reinforcement elevation.

6. Coordinate-space / unit / transform problem?  
   NO. All stages use DXF modelspace millimetres (beam bbox, R.3.1, AnnotationGraph, leaders, evidence window, M.1 renderer). No unit/transform mismatch detected.

7. Ownership problem?  
   NO ownership-engine error for this symptom. T18 correctly rejected the far bars. P2.4 wrong-beam ownership=0 is not invalidated. R.3.1/AnnotationGraph still tags beam_id on those far bars (upstream association worth later review) but T18 already filtered them.

8. Evidence-expansion problem?  
   YES. P2.5.0 treated all bar_results / leader_results keys as includable evidence, ignoring accepted=false, then expand_window_to_evidence unioned them into the crop.

9. Upstream of P2.5.0 or inside P2.5.0?  
   Inside P2.5.0 evidence inclusion / expansion. Upstream provides candidate bars with far Y; ownership correctly rejects; P2.5.0 incorrectly re-included them.

10. Does P2.5.0 need a code correction?  
   YES — minimal proven fix: include only T18-accepted bars/leaders (plus accepted_chains BAR::/leaders) in the evidence package / window. MODEL_VERSION → 10.6.1.

11. Are current crops suitable for Claude Vision?  
   BEFORE fix: B97A/B98A = VISION_CROP_EXTREME (not suitable). AFTER fix: B97A=VISION_CROP_HEALTHY, B98A=VISION_CROP_HEALTHY. Known-good B14/B60 remain healthy. Full-set re-render recommended before Claude.

12. Exact recommendation before P2.5.1?  
   Do NOT start P2.5.1 yet until Fourth Set P2.5.0 packages are regenerated with the accepted-only fix and Crop Sanity is reviewed for remaining EXTREME cases. Then proceed to P2.5.1 Quantity Intent Schema.

## After-fix crop metrics (B97A / B98A)

{
  "B97A": {
    "ratios": {
      "beam_width_mm": 3585.39,
      "beam_height_mm": 2979.22,
      "crop_width_mm": 4999.893,
      "crop_height_mm": 3219.22,
      "crop_width_to_beam_width_ratio": 1.3945,
      "crop_height_to_beam_height_ratio": 1.0806,
      "crop_area_to_beam_area_ratio": 1.5069,
      "crop_aspect_wh": 1.5531
    },
    "max_y_gap_mm": 0.0,
    "reinforcement_count": 0,
    "excluded_rejected": {
      "bars": [
        "BAR::2B7B3233",
        "BAR::5B1BFCC2"
      ],
      "leaders": [],
      "basis": "T18 bar_results/leader_results with accepted=false are diagnostic candidates only and must not expand the P2.5.0 evidence window (P2.5.0.1 fix)."
    },
    "crop_bbox": [
      31646955.30694844,
      -21211038.03,
      31651955.2,
      -21207818.81
    ],
    "render_success": true,
    "vision_crop_status": "VISION_CROP_HEALTHY"
  },
  "B98A": {
    "ratios": {
      "beam_width_mm": 3585.4,
      "beam_height_mm": 3048.94,
      "crop_width_mm": 3585.4,
      "crop_height_mm": 3048.94,
      "crop_width_to_beam_width_ratio": 1.0,
      "crop_height_to_beam_height_ratio": 1.0,
      "crop_area_to_beam_area_ratio": 1.0,
      "crop_aspect_wh": 1.1759
    },
    "max_y_gap_mm": 0.0,
    "reinforcement_count": 0,
    "excluded_rejected": {
      "bars": [
        "BAR::4D469A4E",
        "BAR::E6591903"
      ],
      "leaders": [
        "LDR::53A6EF71"
      ],
      "basis": "T18 bar_results/leader_results with accepted=false are diagnostic candidates only and must not expand the P2.5.0 evidence window (P2.5.0.1 fix)."
    },
    "crop_bbox": [
      31651335.2,
      -21210918.03,
      31654920.6,
      -21207869.09
    ],
    "render_success": true,
    "vision_crop_status": "VISION_CROP_HEALTHY"
  }
}
