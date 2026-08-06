# Phase QA.3.0 — Unseen Drawing Benchmark

MODEL_VERSION: 10.0.0

First large-scale generalization validation of the Version10 production model
on completely unseen drawing sets (Fourth / Fifth / Sixth).

## Policy

- Version9 is frozen; all work is under Version10.
- No engineering heuristics, ownership, OpenCV, rendering, parsers, or
  benchmark formulas were modified for this phase.
- Production runs from DXF only.
- Estimator Output Excel is ground truth for **benchmark only**.

## Outputs

- `DrawingSetDiscovery.json`
- `QA30Validation.json`
- `Generalization_Benchmark_Report.xlsx` / `.json`
- `GeneralizationSummary.md`
- `EngineeringErrorSummary.json`
- `ExecutionSummary.md`
- Per-set folders: `Fourth_Set_Drawings/`, `Fifth_Set_Drawings/`, `Sixth_Set_Drawings/`

## Run

```
python Run_PY/run_phase_qa30_unseen_benchmark.py
```
