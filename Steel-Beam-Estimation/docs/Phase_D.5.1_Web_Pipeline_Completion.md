> **Historical Migration Record (D.5.x)** — retained for migration history.
> Production baseline is **MODEL_VERSION 8.9.5**. See
> [Production_Architecture_8.9.5.md](Production_Architecture_8.9.5.md) and
> [Phase_D.5.6_Production_Validation_Cleanup.md](Phase_D.5.6_Production_Validation_Cleanup.md).
# Phase D.5.1 â€” Web Pipeline Completion Foundation

**MODEL_VERSION:** 8.9.0  
**Date:** 2026-07-28  
**Scope:** Engineering Semantic Engine (R.2.1B + R.2.1C) + per-run I/O architecture

---

## 1. Architecture summary

Web estimations no longer write to shared `Version8/data/output/`. Each upload runs in an isolated tree:

```text
Version8/data/web_runs/<run_id>/
  general_notes/ | framing/ | reinforcement/
  data/output/
    PhaseVROOT.1_dynamic_pipeline_initialization/
    PhaseR.1_generalized_reinforcement_discovery/
    PhaseR.2A_engineering_context/
    PhaseR2.1B_engineering_semantic_interpreter/
    PhaseR2.1C_engineering_fact_normalization/
```

`RunContext` (`Version8/src/config/run_context.py`) provides `engine_root`, `run_root`, `input_root`, `output_root` for every stage.

Production pipeline stops after R.2.1C (Excel / R.3 deferred).

---

## 2. Data flow diagram

```text
Browser upload (3Ã— DXF)
        â”‚
        â–¼
web_runs/<run_id>/  (DXF staging)
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   beam_registry, drawing_manifest
   â”‚ VROOT1  â”‚ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                   â”‚
        â”‚                                        â”‚
        â–¼                                        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   reinforcement_annotations.json  â”‚
   â”‚   R1    â”‚ â—„â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   engineering_context.json
   â”‚  R2A    â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   engineering_semantic_objects.json
   â”‚ R.2.1B  â”‚ â—„â”€â”€ reads R1 + VROOT1 under same run output_root
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”   EngineeringFacts.json (+ stats/reports)
   â”‚ R.2.1C  â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
        â”‚
        â–¼
   SUCCESS (D.5.1) â€” workbook later
```

---

## 3. Files modified

| Area | Files |
|------|--------|
| Run context | `Version8/src/config/run_context.py` (new) |
| VROOT1 | `initialization_export.py`, `phase_vroot1_orchestrator.py`, `Run_PY/run_phase_vroot1_...py` |
| R1 | `phase_r1_orchestrator.py`, `Run_PY/run_phase_r1_...py` |
| R2A | `Run_PY/run_phase_r2a_...py` |
| R.2.1B | `phase_r21b_orchestrator.py`, `Run_PY/run_phase_r21b_...py` |
| R.2.1C | `phase_r21c_orchestrator.py`, `__init__.py`, `Run_PY/run_phase_r21c_...py` |
| Local web | `Version8/webapp/config.py`, `app.py`, `services/estimation_service.py` |
| Deploy web | `current_model/config/settings.py`, `model_info.yaml`, `webapp/config.py`, `webapp/services.py` |
| Docs | `Version8/PIPELINE.md`, this file, `docs/ReleaseNotes.md` |

---

## 4. Pipeline diagram

```text
BEFORE:  Upload â†’ VROOT1 â†’ R1 â†’ R2A â†’ R3 â†’ â€¦ â†’ VB1
AFTER:   Upload â†’ VROOT1 â†’ R1 â†’ R2A â†’ R.2.1B â†’ R.2.1C   [STOP]
```

---

## 5. Run context design

| Field | Web | Offline CLI |
|-------|-----|-------------|
| `engine_root` | Version8 | Version8 |
| `run_root` | `web_runs/<run_id>` | = engine_root |
| `input_root` | = run_root | = run_root |
| `output_root` | `run_root/data/output` | `engine_root/data/output` |

Env: `STEEL_ENGINE_ROOT`, `STEEL_RUN_ROOT`, `STEEL_OUTPUT_ROOT`.

---

## 6. Input / output redesign

| Stage | Input | Output (under `output_root`) |
|-------|-------|------------------------------|
| VROOT1 | DXFs in run_root | `PhaseVROOT.1_.../*` |
| R1 | VROOT1 artefacts | `PhaseR.1_.../*` |
| R2A | GN pointer + engine parsers | `PhaseR.2A_.../*` |
| R.2.1B | R1 annotations/models + registry | `PhaseR2.1B_.../engineering_semantic_objects.json` |
| R.2.1C | R.2.1B ESO | `PhaseR2.1C_.../EngineeringFacts.json` |

Engineering calculations unchanged â€” path injection only.

---

## 7. Removed legacy dependencies (R.2.1B / R.2.1C)

- No `Benchmark_Set_*` path usage in R.2.1B/C
- No Version7 seed / copy in web hot path
- No shared `Version8/data/output` as primary web output root
- Version7 seeding helper removed from D.5.1 pipeline services

---

## 8. Validation checklist

- [ ] Fresh `web_runs/<id>/` with 3 DXFs
- [ ] Set `STEEL_RUN_ROOT` / run stages VROOT1â†’R21C
- [ ] Artefacts appear only under that run's `data/output/`
- [ ] `EngineeringFacts.json` present after R.2.1C
- [ ] Web UI reports success without Excel
- [ ] Grep R.2.1B/C: no Benchmark_Set / Version7 path deps

---

## 9. MODEL_VERSION

**8.9.0** â€” R.2.1B/C packages, webapp, `model_info.yaml`, PIPELINE.md

---

## 10. Suggested git commit message

```text
feat(D.5.1): per-run web pipeline for R.2.1B/C (MODEL_VERSION 8.9.0)

Introduce RunContext and web_runs/<run_id>/data/output tree; web-enable
R.2.1B+R.2.1C I/O; truncate PRODUCTION_STAGES after the semantic engine.
```

---

## 11. Production readiness assessment

| Item | Status |
|------|--------|
| Per-run isolation | Ready (D.5.1) |
| Semantic engine on upload | Ready (R.2.1Bâ†’R.2.1C) |
| Fresh clone without leftover artefacts | Ready for semantic stages |
| R.3 / Excel workbook | **Not ready** â€” requires D.5.2+ (R.2.1D, L.2.2, R.3, VB.1) |
| Lightsail full estimate download | **Blocked** until later milestones |

D.5.1 is production-ready for the **Engineering Semantic Engine** only.

