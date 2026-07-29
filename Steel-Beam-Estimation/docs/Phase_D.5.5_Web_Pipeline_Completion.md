> **Historical Migration Record (D.5.x)** — retained for migration history.
> Production baseline is **MODEL_VERSION 8.9.5**. See
> [Production_Architecture_8.9.5.md](Production_Architecture_8.9.5.md) and
> [Phase_D.5.6_Production_Validation_Cleanup.md](Phase_D.5.6_Production_Validation_Cleanup.md).
# Phase D.5.5 â€” Downstream Production Pipeline Completion

**MODEL_VERSION:** 8.9.4  
**Date:** 2026-07-29  
**Scope:** Web-enable R.3.1 â†’ R.1.2A â†’ R.1.3 â†’ VB.1 (Excel) on RunContext

---

## 1. Architecture summary

D.5.4 stopped the production pipeline after R.3. D.5.5 completes the
engineering migration so a clean upload executes through Excel generation
using **only** the current `RunContext`.

Contract (every stage):

```text
INPUT â†’ Current RunContext â†’ Previous phase outputs only
      â†’ Current phase processing â†’ Current phase output folder only
```

No stage may search Version7, Benchmark folders, shared
`Version8/data/output`, or historical artefacts for production execution.

Engineering algorithms (relationships, geometry catalog, bar models, steel
weight, BBS, Excel layout) are unchanged â€” only I/O, path resolution, and
pipeline wiring were migrated.

---

## 2. Final production pipeline diagram

```text
Upload DXFs
  â†’ VROOT1
  â†’ R1
  â†’ R2A
  â†’ R.2.1B
  â†’ R.2.1C
  â†’ R.2.1D
  â†’ L.2.2
  â†’ R.3
  â†’ R.3.1
  â†’ R.1.2A   (catalog-only)
  â†’ R.1.3    (build-only; nested VB.1 skipped)
  â†’ VB.1     (Excel + workbook mapping inside VB.1)
  â†’ SUCCESS + download Estimation_Output.xlsx
```

**Workbook Mapping** is not a separate runner. Column/worksheet mapping lives
inside VB.1 (`EstimatorExcelGenerator` / workbook builders). Treating it as
its own `PRODUCTION_STAGES` entry would duplicate Excel generation.

---

## 3. RunContext integration summary

| Constant | Folder under `output_root` |
|----------|----------------------------|
| `PHASE_R31` | `PhaseR3.1_engineering_relationship_engine` |
| `PHASE_R12A` | `PhaseR1_2A_geometry_accuracy` |
| `PHASE_R13` | `PhaseR1.3_pipeline_integration` |
| `PHASE_VB1` | `Production_Output` |

Env (unchanged from D.5.1+):

- `STEEL_ENGINE_ROOT` â†’ Version8 (src packages)
- `STEEL_RUN_ROOT` â†’ `web_runs/<run_id>/`
- `STEEL_OUTPUT_ROOT` â†’ `web_runs/<run_id>/data/output`

Dual-root rule for R.1.3 / VB.1:

- **engine_root** loads `src/` packages and R.2A GN pointer
- **run_root** hosts all `data/output/...` artefacts

---

## 4. Downstream phase migration summary

| Stage | Runner | Primary success artefact | Notes |
|-------|--------|--------------------------|-------|
| R.3.1 | `run_phase_r31_engineering_relationship_engine.py` | `EngineeringDrawingRelationships.json` | Explicit paths; no `_find_output` |
| R.1.2A | `run_phase_r12a_geometry_accuracy.py` | `validated_beam_geometry.json` | **catalog_only** on web; `--full` forensic offline only |
| R.1.3 | `run_phase_r13_pipeline_integration.py` | `beam_reinforcement_models_production.json` | `skip_production=True` (VB.1 owns Excel) |
| VB.1 | `run_phase_vb1_production_output_completion.py` | `Estimation_Output.xlsx` | Explicit R13 models path; `use_r14_validation=False` on web |

Soft-success: non-zero exit is accepted when the stageâ€™s primary artefact exists
(same pattern as R.3 / L.2.2).

---

## 5. Files modified

### RunContext / runners

- `Version8/src/config/run_context.py`
- `Version8/Run_PY/run_phase_r31_engineering_relationship_engine.py`
- `Version8/Run_PY/run_phase_r12a_geometry_accuracy.py`
- `Version8/Run_PY/run_phase_r13_pipeline_integration.py`
- `Version8/Run_PY/run_phase_vb1_production_output_completion.py`

### Engineering packages (I/O only)

- `Version8/src/PhaseR3.1_engineering_relationship_engine/*`
- `Version8/src/PhaseR1_2A_geometry_accuracy/*`
- `Version8/src/PhaseR1.3_pipeline_integration/*`
- `Version8/src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py`

### Web applications

- `Version8/webapp/config.py`
- `Version8/webapp/services/estimation_service.py`
- `Steel-Beam-Estimation/current_model/config/settings.py`
- `Steel-Beam-Estimation/current_model/webapp/config.py`
- `Steel-Beam-Estimation/current_model/webapp/services.py`
- `Steel-Beam-Estimation/current_model/config/model_info.yaml`

### Docs

- `Version8/PIPELINE.md`
- `Steel-Beam-Estimation/docs/Phase_D.5.5_Web_Pipeline_Completion.md` (this file)
- `Steel-Beam-Estimation/docs/ReleaseNotes.md`
- `Steel-Beam-Estimation/README.md`

---

## 6. Removed legacy dependencies (production hot path)

- R.3.1: `_find_output`, shared production workbook search
- R.1.2A web path: nested R13/VB1 subprocess rebuild
- R.1.3 web path: nested VB.1 (separate stage owns Excel)
- VB.1 web path: shared `Version8/data/output/Production_Output` default;
  L.2 fallback when R13 path is explicit; R.1.4 gate disabled for web runner
- Web success no longer stops at R.3 with `workbook_*=None`

---

## 7. Removed Version7 references (production)

Production runners for R31 / R12A / R13 / VB1 no longer take `version7_root`
or resolve Version7 trees. Parameter name `v7_root` remains in some APIs as a
**legacy alias for engine_root / run_root** (Version8), not a Version7 path.

`settings.V7_ROOT` still exists for historical tooling but is unused by
`PRODUCTION_STAGES`.

---

## 8. Removed Benchmark references (production)

Downstream production stages do not read `Benchmark_Set_*` folders.

Remaining (documented debt â€” not on D.5.5 hot path):

- R.2A `EngineeringContextFactory` offline GN fallback under
  `data/Benchmark_Set_2/general_notes` (web uses GN pointer file)
- Cosmetic Excel header strings mentioning â€œBenchmark Setâ€ in
  `excel_structure_builder.py` (labels only)

---

## 9. Validation results

| Check | Result |
|-------|--------|
| `py_compile` on all D.5.5 changed modules / runners / webapps | PASS |
| Production stages list includes R31 â†’ R12A â†’ R13 â†’ VB1 | PASS |
| Success requires run-scoped `Estimation_Output.xlsx` | PASS |
| Download copies workbook from same run into webapp outputs | PASS |
| Full end-to-end upload on clean Lightsail | Deferred to **D.5.6** |

---

## 10. Excel generation verification

- VB.1 writes `web_runs/<run_id>/data/output/Production_Output/Estimation_Output.xlsx`
- Webapps copy that file to `outputs/Estimation_Output_<run_id>.xlsx`
- Job `workbook_path` / `workbook_name` point at the copy for the download endpoint
- No Version7 / Benchmark / shared workbook discovery on the web path

---

## 11. Production readiness assessment

| Area | Status |
|------|--------|
| Full pipeline wiring | Ready |
| RunContext isolation | Ready |
| Excel download contract | Ready |
| Clean-repo / Lightsail E2E certification | **D.5.6** |
| Removal of residual offline Benchmark GN fallback | **D.5.6** |

---

## 12. Remaining technical debt

1. R.2A factory Benchmark GN fallback (offline only; web uses pointer).
2. VB.1 offline defaults still allow shared `Version8/data/output` when invoked
   without RunContext args.
3. R.1.2A `--full` forensic mode still rebuilds R13/VB1 via subprocess (not used
   in production stages).
4. Some internal APIs retain `v7_root` naming (Version8 alias).
5. Cosmetic â€œBenchmark Setâ€ strings in Excel headers.

---

## 13. MODEL_VERSION

`8.9.4`

---

## 14. Suggested git commit message

```text
feat(D.5.5): complete downstream web pipeline through Excel (MODEL_VERSION 8.9.4)

Run-scoped R.3.1 â†’ R.1.2A â†’ R.1.3 â†’ VB.1; restore workbook download
from the current upload via RunContext.
```

---

## Next phase (do not implement here)

**D.5.6 â€” Production Validation & Cleanup**

- Clean Lightsail E2E on multiple drawing sets
- Remove temporary migration compatibility leftovers
- Performance profiling
- Final production readiness certification

