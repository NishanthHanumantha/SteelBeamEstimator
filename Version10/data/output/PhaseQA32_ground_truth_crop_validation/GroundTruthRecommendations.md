# QA.3.2 Engineering Recommendations

Based ONLY on collected evidence. No engineering modules modified.

Summary: A=0 B=4 C=7; regenerated_manual=11/11; avg_iou=0.3466; avg_completeness=38.8036

## Priority 1: Correct Manual Comparison Crop generation before Ownership work

Manual crops for unseen sets are regenerated from T1 geometry envelopes (tight beam bbox), not true AutoCAD ground-truth crops. Ownership investigation should be postponed until crop generation is corrected or a verified GT crop source is established.

Evidence: `{'category_C': 7, 'category_B': 4, 'regenerated': 11, 'average_iou': 0.3466, 'average_completeness_pct': 38.8036}`

## Priority 2: Coordinate / extent mismatch between Manual and Owned Render

Documented divergence: Manual uses geometry_envelopes.extent; Owned Render uses T182 computed_render_bbox. Align comparison baseline extent with the reinforcement context under evaluation.

Evidence: `{'average_centroid_error': 2885.6845, 'average_padding_error': 4667.8498}`

## Priority 3: Resume Ownership Engine investigation after GT baseline fix

Once Manual crops are trustworthy (Category A), re-run QA.3.1-style ownership diagnostics. Until then, QA.3.1 Ownership FAIL counts may mix true ownership defects with baseline crop defects.

Evidence: `{'qa31_trustworthy_beam_count': 0}`
