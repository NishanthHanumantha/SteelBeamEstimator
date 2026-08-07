# Phase QA.3.1 — Ownership & Render Pipeline Diagnostics

**MODEL_VERSION:** 10.0.1  
**Type:** Diagnostic only (no engineering changes)

Reads existing QA.3.0 / Track1 artefacts and identifies the first failing
pipeline stage for priority beams on unseen drawings.

## Run

From `Version10/`:

```bash
python Run_PY/run_phase_qa31_pipeline_diagnostics.py
python Run_PY/run_phase_qa31_pipeline_diagnostics.py --beams B14,B22,B45
```

Outputs: `data/output/PhaseQA31_pipeline_diagnostics/`
