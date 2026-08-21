# P2.6.10-C.4 — Shadow Truth Reconciliation & Vision Benchmark Calibration

MODEL_VERSION: 10.11.17
Shadow / benchmark calibration only. Predecessor artefacts are evidence, not automatic ground truth.

## Population

- discovered control beams: 6
- source: existing C.3 six-beam artefact

## Evidence availability

- LIVE_CLAUDE_CALL = False
- PRODUCTION_WRITE = False
- ENGINEERING_CHANGES = NONE

## Beam-level reconciliation

- beams_reconciled: 1
- VISION_CONFIRMED: 1
- DETERMINISTIC_CONFIRMED: 0
- BOTH_EQUIVALENT: 0
- AMBIGUOUS_EVIDENCE: 5
- INSUFFICIENT_EVIDENCE: 0

| beam_id | status | strength | vision_result | deterministic_result | truth_source |
|---|---|---|---|---|---|
| B141 | VISION_CONFIRMED | STRONG | MATCHES_RECONCILED_TRUTH | DISAGREES_WITH_RECONCILED_TRUTH | MANUAL_VISUAL_VERIFICATION |
| B66 | AMBIGUOUS_EVIDENCE | LIMITED | UNRESOLVED | UNRESOLVED | UNRESOLVED_CONFLICT |
| B161 | AMBIGUOUS_EVIDENCE | LIMITED | UNRESOLVED | UNRESOLVED | UNRESOLVED_CONFLICT |
| B128 | AMBIGUOUS_EVIDENCE | LIMITED | UNRESOLVED | UNRESOLVED | UNRESOLVED_CONFLICT |
| B55 | AMBIGUOUS_EVIDENCE | LIMITED | UNRESOLVED | UNRESOLVED | UNRESOLVED_CONFLICT |
| B65 | AMBIGUOUS_EVIDENCE | LIMITED | UNRESOLVED | UNRESOLVED | UNRESOLVED_CONFLICT |

## Group-level comparison against reconciled truth

Unresolved groups are excluded from forced correctness claims.

- reconciled_expected_group_count: 3
- vision_correct / missing / spurious: 3 / 0 / 0
- deterministic_correct / missing / spurious: 0 / 3 / 1

## Explicit verification anchors

### B141

- reconciliation_status: VISION_CONFIRMED
- reconciled_groups: [{"layer": "BOTTOM", "role": "MAIN", "specification": "5Y16", "provenance": "MANUAL_VISUAL_VERIFICATION"}, {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4LY8@100C/C", "provenance": "MANUAL_VISUAL_VERIFICATION"}, {"layer": "TOP", "role": "MAIN", "specification": "5Y20", "provenance": "MANUAL_VISUAL_VERIFICATION"}]
- vision_interpretation: [{"layer": "TOP", "role": "MAIN", "specification": "5Y20", "raw_specification": "5-Y20", "support_scope": "FULL_SPAN", "family": null, "confidence": 0.95}, {"layer": "BOTTOM", "role": "MAIN", "specification": "5Y16", "raw_specification": "5-Y16", "support_scope": "FULL_SPAN", "family": null, "confidence": 0.95}, {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4LY8@100C/C", "raw_specification": "4L-Y8@100C/C", "support_scope": "", "family": null, "confidence": 0.95}]
- deterministic_interpretation: [{"layer": "TOP", "role": "MAIN", "specification": "5Y16", "raw_specification": "5Y16", "support_scope": "FULL_SPAN", "family": "LONGITUDINAL", "confidence": 0.8341}]
- outcome reached by generic engine from supplied evidence (no beam-ID branch).

## Unresolved cases

Beams without independent verification remain AMBIGUOUS_EVIDENCE or INSUFFICIENT_EVIDENCE.
A C.3 VISION_DISAGREEMENT is an observation, not a Vision error and not a deterministic error.

## Limitations

- Visual PNG pixels are not programmatically read as group truth.
- Phase-sketch free-text notes are not parsed into groups.
- Only explicitly supplied MANUAL_VERIFICATION can independently confirm one interpretation.
- This phase did not call Claude and did not rerender DXF.

## Decision and recommendation

- decision: VISION_SIGNAL_SUPPORTED
- recommendation: A_SAMPLED_EXPANDED_SHADOW
- Proceed to a stratified sampled Vision shadow benchmark. Do not send the full LIMITED population. Keep Vision diagnostic-only until the sample is reviewed.

If expansion is later approved, use a stratified sample covering, where available:
normal/high-quality renders; clipped/limited renders; neighbouring-beam interference;
same-spec distinct physical groups; MAIN/EXTRA separation; multi-group beams;
stirrup interpretation; blank/crushed reporting cohort; long-horizontal reporting cohort.
Do not automatically send the full LIMITED population.

## Safety

- LIVE_CLAUDE_CALL = False
- PRODUCTION_WRITE = False
- ENGINEERING_CHANGES = NONE
