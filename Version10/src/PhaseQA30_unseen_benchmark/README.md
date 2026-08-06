# Phase QA.3.0 — Unseen Drawing Benchmark

**MODEL_VERSION:** 10.0.0  
**Type:** Benchmark validation (no engineering changes)

Validates generalization of the Version10 production spine on completely
unseen drawing sets under `Test_Input` (Fourth / Fifth / Sixth).

## Modules

| Module | Role |
|--------|------|
| `drawing_set_discovery.py` | Auto-discover DXFs + estimator Excel |
| `production_executor.py` | Fresh DXF-only production via `ProductionPipelineRunner` |
| `benchmark_executor.py` | Post-production QA.2A comparison (estimator Excel here only) |
| `generalization_report.py` | Generalization report artefacts |
| `qa_validator.py` | `QA30Validation.json` gates |
| `report_builder.py` | Execution summary + console completion |
| `phase_qa30_orchestrator.py` | End-to-end orchestration |

## Strict policy

- Estimator Output Excel is **never** opened during production.
- No modifications to Beam Discovery, Ownership, OpenCV, Track1, QA.2A formulas.
- `reuse_detected` must be `false` for every set.

## Run

From `Version10/`:

```bash
python Run_PY/run_phase_qa30_unseen_benchmark.py
```

Outputs land in `data/output/PhaseQA30_unseen_benchmark/`.
