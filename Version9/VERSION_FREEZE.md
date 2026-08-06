# Version 9 — FROZEN

**Status:** FROZEN as of 2026-08-06  
**Final MODEL_VERSION range:** 9.0.x → **9.6.2** (QA.2B.2 accuracy report)  
**Successor:** `Version10/`

## Do not continue feature work here

All new development — including further accuracy, ownership, rendering, and
benchmark improvements — continues in **Version10**.

Version 9 remains the completed accuracy branch that delivered:

- Track 1 geometric stirrup evidence (T1) + OpenCV crops
- Entity / annotation / beam ownership (T1.6–T1.8)
- Adaptive render extent (T1.8.2)
- Shared engineering ownership + scope dedup (T1.8.3 / T1.8.3.1)
- QA.2B.0 pipeline integration
- QA.2B.1 production regeneration + ground-truth re-benchmark
- QA.2B.2 Overall Accuracy Report (V9.6.1)

Do not change engineering behaviour in this tree.

## What shipped into Version 10

Lean copy for continued accuracy work:

- `src/`, `Run_PY/`, `config/`, `schemas/`, `prompts/`
- `webapp/` (code only)
- `data/` input drawing sets + Excel template
- `requirements.txt`, `PIPELINE.md`, `.gitignore`

**Not carried forward:** `data/output/**`, `data/web_runs/**`,
`Cursor_Explanation/`, local webapp `logs/` / `uploads/` / `outputs/`.

## Reference artefacts (historical, under Version9)

- `data/output/PhaseQA2B1_production_regeneration/` — regenerated GT benchmark
- `data/output/PhaseQA2B2_accuracy_report/Overall_Accuracy_Report_V9.6.1.docx`
