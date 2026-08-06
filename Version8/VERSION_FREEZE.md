# Version 8 — FROZEN

**Status:** FROZEN as of 2026-07-29  
**Final MODEL_VERSION:** 8.9.5  
**Git tag:** `v8.9.5` — *Stable Production Baseline - Web-native RunContext Pipeline*  
**Successor:** `Version9/`

## Do not continue feature work here

All new development — including reinforcement identification & interpretation
accuracy improvements — continues in **Version9**.

Version 8 remains the certified production baseline (upload → Excel on
RunContext / Lightsail). Do not change engineering behaviour in this tree.

## What shipped into Version 9

Lean copy for accuracy work:

- `src/`, `Run_PY/`, `config/`, `schemas/`, `prompts/`
- `webapp/` (code only)
- `data/` input drawing sets + Excel template
- `requirements.txt`, `PIPELINE.md`, `.gitignore`

**Not carried forward:** `data/output/**`, `data/web_runs/**`, `Demo1/`,
local webapp `logs/` / `uploads/` / `outputs/`, Version8-only docs recaps,
`_bootstrap_from_v7.py`.

## Production reference

- `Steel-Beam-Estimation/docs/Production_Architecture_8.9.5.md`
- `Steel-Beam-Estimation/docs/Phase_D.5.6_Production_Validation_Cleanup.md`

## Later successor

Accuracy work moved from Version9 to **Version10** (2026-08-06). Version8 remains the certified production baseline; Version9 remains the completed 9.x accuracy branch.
