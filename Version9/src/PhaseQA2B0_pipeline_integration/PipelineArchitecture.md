# QA.2B.0 — Pipeline Architecture

**MODEL_VERSION:** 9.6.0  
**Phase:** End-to-End Benchmark Pipeline Integration

## Required flow

```
Input DXF
      ↓
Beam Discovery                          (R1 / VROOT1)
      ↓
Engineering Interpretation              (R2A → R21D → L22 → R3 → R31 → R12A → R13 → VB1)
      ↓
Stirrup Recovery                        (T1 geometric stirrup evidence)
      ↓
Shared Engineering Ownership            (T16 → T17 → T18 → T183 → T1831)
      ↓
Render Generation                       (T181 ownership render)
      ↓
OpenCV Enhancement / Adaptive Extent    (T1 opencv_renders + T182 adaptive extent)
      ↓
Beam Crop Generation                    (latest crop preference order below)
      ↓
Ground Truth Comparator                 (QA.2A workbook compare + crop manifest gate)
      ↓
Accuracy Engine                         (QA.2A metrics — unchanged)
      ↓
QA Report Generator                     (QA.2A Excel/JSON + QA.2B.0 validation)
```

## Crop / render preference (latest first)

1. `PhaseT183_shared_engineering_ownership/RenderedBeams/{beam}_render.png`
2. `PhaseT182_adaptive_render_extent/RenderedBeams/{beam}_render.png`
3. `PhaseT181_render_validation/RenderedBeams/{beam}_render.png`
4. `PhaseT16_entity_ownership/{beam}/filtered_render.png`
5. `PhaseT1_geometric_stirrup_evidence/opencv_renders/{beam}_crop.png`

Legacy / forbidden sources (never preferred):

- Version8 / Version7 paths
- `_9_3_2_before_backup`
- obsolete Track1 before-caches

## Integration package

| Module | Role |
|--------|------|
| `PipelineIntegrator` | Resolve latest `qa2_*` web_run per set; ensure T1 envelopes; run Track1 visual chain; build crop manifests; invoke QA.2A with reuse |
| `PipelineValidator` | Emit `PipelineValidation.json` connection / integrity checks |
| `IntegrationQA` | Emit `PipelineIntegrationQA.json` + `ExecutionSummary.md` |
| `track1_chain_runner` | Calls existing T16–T1831 orchestrators (no forks) |
| `pipeline_paths` | Latest artefact registry + crop resolver |

## Production stage wiring

`PhaseQA.2_multi_drawing_benchmark/pipeline_runner.py` appends stage **T16CHAIN** after VB1:

- script: `Run_PY/run_phase_track1_visual_chain.py`
- soft artefact: `PhaseT182_adaptive_render_extent/RenderedBeams` (PNG present)

This keeps the multi-drawing benchmark as the single entry for future full QA runs.

## Null-extent beam filter (integration only)

Beams whose `geometry_envelopes.json` entry has null `extent` / xmin–ymax
(e.g. `no_beam_mark`) are excluded from the Track1 visual chain so they cannot
abort T1.8+. They are recorded as `skipped_null_extent` in crop manifests.
This does not change T1 / T1.8 algorithms — only which beams are invoked.

## Non-goals (explicit)

- No engineering rule changes
- No render / OpenCV / crop algorithm changes
- No QA.2A metric formula changes
- Accuracy evaluation deferred to a later QA phase
