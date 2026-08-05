# Phase QA.2B.0 — End-to-End Benchmark Pipeline Integration

**MODEL_VERSION:** 9.6.0

Strictly a pipeline wiring phase. No engineering, render, crop, or accuracy-math changes.

## Run

```powershell
cd Version9
python Run_PY/run_phase_qa2b0_pipeline_integration.py
```

Options:

- `--skip-benchmark` — integrate + validate only
- `--force-track1` — re-run T16–T1831 even if artefacts exist

## Outputs

Under `data/output/PhaseQA2B0_pipeline_integration/`:

- `PipelineValidation.json`
- `PipelineIntegrationQA.json`
- `ExecutionSummary.md`
- `PipelineArchitecture.md`
- `CropManifest_{First,Second,Third}.json`
- `IntegrationResult.json`

## See also

`PipelineArchitecture.md` — required flow and crop preference order.
