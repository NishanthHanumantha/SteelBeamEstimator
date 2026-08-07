# Phase QA.3.2 Execution Summary

- MODEL_VERSION: `10.0.2`
- Elapsed: `136.74s`
- Beams analysed: `11`
- VALID / PARTIAL / INVALID: `0` / `4` / `7`
- Category A/B/C: `{'A': 0, 'B': 4, 'C': 7}`
- Average IoU: `0.3466`
- Average completeness %: `38.8036`
- Regenerated manual crops: `11`
- QA.3.1 trustworthy beams: `0`
- Dominant finding: `manual_crops_are_regenerated_tight_envelopes_not_true_autocad_gt`
- Validation overall_pass: `True`

## Priorities
### Priority 1: Correct Manual Comparison Crop generation before Ownership work

Manual crops for unseen sets are regenerated from T1 geometry envelopes (tight beam bbox), not true AutoCAD ground-truth crops. Ownership investigation should be postponed until crop generation is corrected or a verified GT crop source is established.

### Priority 2: Coordinate / extent mismatch between Manual and Owned Render

Documented divergence: Manual uses geometry_envelopes.extent; Owned Render uses T182 computed_render_bbox. Align comparison baseline extent with the reinforcement context under evaluation.

### Priority 3: Resume Ownership Engine investigation after GT baseline fix

Once Manual crops are trustworthy (Category A), re-run QA.3.1-style ownership diagnostics. Until then, QA.3.1 Ownership FAIL counts may mix true ownership defects with baseline crop defects.

