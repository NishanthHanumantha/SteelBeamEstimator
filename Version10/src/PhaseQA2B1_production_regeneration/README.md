# Phase QA.2B.1 — Production Output Regeneration & Ground Truth Re-Benchmark

**MODEL_VERSION:** 9.6.1

Regenerates `Estimation_Output.xlsx` for all three benchmark drawing sets using the
integrated Version 9.6.0 production pipeline, then runs QA.2A against those new
workbooks only.

## Run

```powershell
cd Version9
python Run_PY/run_phase_qa2b1_production_regeneration.py
```

Hard rules:

- Does **not** pass `--reuse-existing-model`
- Does **not** load prior `Estimation_Output.xlsx`
- Does **not** modify engineering / ownership / render / QA.2A metric code

## Outputs

`data/output/PhaseQA2B1_production_regeneration/`

- `ProductionRegenerationQA.json`
- `RegenerationComparison.json`
- `ProductionRegenerationSummary.md`
- `BenchmarkSummary.md`
- `GroundTruth_Benchmark_Report.xlsx`
- `GroundTruth_Benchmark_Report.json`
