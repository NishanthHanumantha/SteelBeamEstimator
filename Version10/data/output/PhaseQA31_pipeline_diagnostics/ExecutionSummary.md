# Execution Summary — QA.3.1

- MODEL_VERSION: 10.0.1
- Elapsed (s): 3.37
- Beams analysed: 11
- Missing-artefact beams: 0
- QA overall_pass: True

## Failure frequency

- Beam Discovery: 0
- Beam Extents: 0
- Crop Window: 0
- Ownership: 7
- Annotation Association: 0
- Rendering: 0
- Mixed: 0
- None (no stage FAIL): 4

## Top primary root cause: Ownership

## Hypothesis
- ownership_or_scoping_before_render_is_dominant: True
- renderer_mostly_faithful_to_owned_set: True

## Priority 1: Ownership — Priority confirmed by diagnostics: ownership/scoping fails before render on multiple beams. Investigate Ownership failures first (n=7).

No engineering modules were modified.
