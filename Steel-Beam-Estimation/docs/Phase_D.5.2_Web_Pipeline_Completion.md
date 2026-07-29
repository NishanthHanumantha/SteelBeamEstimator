> **Historical Migration Record (D.5.x)** — retained for migration history.
> Production baseline is **MODEL_VERSION 8.9.5**. See
> [Production_Architecture_8.9.5.md](Production_Architecture_8.9.5.md) and
> [Phase_D.5.6_Production_Validation_Cleanup.md](Phase_D.5.6_Production_Validation_Cleanup.md).
# Phase D.5.2 â€” Web Pipeline Completion (R.2.1D)

**MODEL_VERSION:** 8.9.1  
**Date:** 2026-07-28  
**Scope:** Web-enable Phase R.2.1D (Evidence & Hypothesis Engine) on RunContext

---

## 1. Architecture summary

D.5.1 delivered per-run execution through R.2.1C. D.5.2 extends the same
`RunContext` contract so R.2.1D consumes R.2.1C `EngineeringFacts.json` from the
**current run** and writes the hypothesis-enriched `EngineeringFacts.json` under:

```text
Version8/data/web_runs/<run_id>/
  data/output/
    PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json   (input)
    PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json       (output)
```

Engineering logic (evidence scoring, hypothesis ranking, validation) is unchanged.
Only I/O, path resolution, and pipeline integration were refactored.

Production pipeline now stops after R.2.1D (L.2.2 / R.3 / Excel deferred).

---

## 2. Updated pipeline diagram

```text
Browser upload (3Ã— DXF)
        â”‚
        â–¼
web_runs/<run_id>/  (DXF staging)
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ VROOT1  â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚   R1    â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚  R2A    â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ R.2.1B  â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   EngineeringFacts.json (normalized)
   â”‚ R.2.1C  â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   EngineeringFacts.json (evidence + hypotheses)
   â”‚ R.2.1D  â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   SUCCESS (D.5.2) â€” geometry / Excel later
```

---

## 3. RunContext integration summary

| Item | Detail |
|------|--------|
| Constant | `PHASE_R21D = "PhaseR2.1D_evidence_hypothesis_engine"` |
| Env | `STEEL_ENGINE_ROOT`, `STEEL_RUN_ROOT`, `STEEL_OUTPUT_ROOT` (unchanged from D.5.1) |
| Runner argv | `run_phase_r21d_...py [<run_root>]` |
| Offline default | `run_root = engine_root` â†’ `Version8/data/output/...` |

---

## 4. R.2.1D input/output redesign

| Direction | Path (relative to run `output_root`) |
|-----------|--------------------------------------|
| **Input** | `PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json` |
| **Output** | `PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json` (+ existing reports/stats) |

Removed:

- Hardcoded `_V7/.../PhaseR2.1C_.../EngineeringFacts.json`
- Shared `Version8/data/output` as the only production target for web
- Version7 runner error messaging in the missing-input path

---

## 5. Files modified

| Area | Files |
|------|--------|
| Run context | `Version8/src/config/run_context.py` (`PHASE_R21D`, 8.9.1) |
| R.2.1D | `phase_r21d_orchestrator.py`, `__init__.py`, `Run_PY/run_phase_r21d_...py` |
| Local web | `Version8/webapp/config.py`, `app.py`, `services/estimation_service.py` |
| Deploy web | `current_model/config/settings.py`, `model_info.yaml`, `webapp/config.py`, `webapp/services.py` |
| Docs | `PIPELINE.md`, this file, `ReleaseNotes.md`, package README |

---

## 6. Removed legacy dependencies

- No `Benchmark_Set_*` path usage in R.2.1D
- No Version7 path hardcoded for R.2.1D input
- No seed / copy of `EngineeringFacts.json` in the D.5.2 hot path
- No offline prerequisite outside the current runâ€™s R.2.1C output

---

## 7. Validation results

Checklist for a fresh clone / clean deploy:

- [x] `PRODUCTION_STAGES` includes R21D after R21C (both webapps)
- [x] Success criterion = `PhaseR2.1D_.../EngineeringFacts.json` under run tree
- [x] R.2.1D orchestrator accepts `output_root` / explicit paths (no `_V7`)
- [x] Grep R.2.1D package + runner: no Benchmark_Set / Version7 path deps
- [x] Synthetic run-scoped smoke: R.2.1C facts under `web_runs/_d52_smoke` â†’ R.2.1D wrote `EngineeringFacts.json` (exit 0 soft-success)
- [ ] End-to-end upload smoke (operator): Upload â†’ â€¦ â†’ R.2.1D artefact present

CLI smoke (when a run with R.2.1C facts exists):

```powershell
python Version8/Run_PY/run_phase_r21d_evidence_hypothesis_engine.py <web_runs/<run_id>>
```

---

## 8. Remaining blockers before L.2.2 (D.5.3)

| Blocker | Notes |
|---------|--------|
| `geometry_registry.json` | Still not generated in web pipeline (L.2.2 offline / Version7 assumptions) |
| R.3 | Still resolves artefacts via `version7_root/data/output/...` (`_find_output`) â€” **not** RunContext |
| R.3.1 | Same shared-output assumption as R.3 |
| Excel / VB.1 | Intentionally out of scope |

---

## 9. Backward compatibility â€” `EngineeringFacts.json` callers

| Consumer | Current assumption | D.5.4 / later action |
|----------|--------------------|----------------------|
| **R.3** | `self._root / "data/output/PhaseR2.1D_.../EngineeringFacts.json"` where `_root` is Version7/engine shared root | Switch to `RunContext.artefact(PHASE_R21D, "EngineeringFacts.json")` |
| **R.3.1** | Same relative phase folder under shared `data/output` | Same RunContext wiring |
| Web success check | Was R.2.1C path (D.5.1) | Now R.2.1D path (this phase) |
| R.2.1C output | Still written; R.2.1D reads it | Keep both artefacts in run tree |

Do **not** modify R.3 in D.5.2.

---

## 10. MODEL_VERSION

`8.9.0` â†’ `8.9.1`

---

## 11. Suggested git commit message

```text
feat(D.5.2): web-enable R.2.1D Evidence & Hypothesis Engine (MODEL_VERSION 8.9.1)

Run-scoped EngineeringFacts.json from current upload via RunContext;
extend production pipeline through R.2.1D; leave L.2.2/R.3 for later.
```

---

## 12. Production readiness assessment

| Capability | Ready? |
|------------|--------|
| Upload â†’ VROOT1 â†’ R1 â†’ R2A â†’ R.2.1B â†’ R.2.1C â†’ R.2.1D | **Yes** (architecture) |
| Dynamic `EngineeringFacts.json` (hypothesis-enriched) per run | **Yes** |
| No Benchmark / Version7 / seed for R.2.1D | **Yes** |
| R.3 / Excel workbook | **Not ready** â€” needs D.5.3 (L.2.2) then R.3 RunContext (D.5.4+) |

