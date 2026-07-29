# Phase D.5.6 — Production Validation & Cleanup

**MODEL_VERSION:** 8.9.5  
**Date:** 2026-07-29  
**Status:** Complete — Stable Production Baseline  
**Type:** Cleanup & Stabilization (no engineering behaviour change)

> **Historical Migration Record:** Phases D.5.1–D.5.5 delivered the RunContext
> migration. This document certifies cleanup and freezes **8.9.5** as the
> production baseline. Engineering algorithms are unchanged from 8.9.4.

---

## 1. Production cleanup summary

| Action | Result |
|--------|--------|
| Remove dead `_ensure_r3_prerequisites` stubs | Done (both webapps) |
| Stop re-exporting unused `V7_ROOT` / `ARTEFACT_SEED_ROOT` from Flask config | Done |
| Health `phase` D.4.2 → Production Ready | Done |
| Migration-flavoured log / comment language | Cleaned |
| Webapp README Version7 seed language | Removed |
| MODEL_VERSION bump 8.9.4 → 8.9.5 | Done |
| Architecture + audit + debt register docs | Done |
| Excel / estimation logic | **Unchanged** |
| RunContext contract | **Unchanged** |

Lightsail upload→Excel validation for 8.9.4 remains the functional proof.
D.5.6 does not re-run engineering tests unless cleanup required it (it did not).

---

## 2. Legacy dependency audit table

| Reference | Location | Classification | Action |
|-----------|----------|----------------|--------|
| `V7_ROOT` in settings | `current_model/config/settings.py` | Offline / historical path constant | **Retain** + document unused by PRODUCTION_STAGES |
| `ARTEFACT_SEED_ROOT` | settings (env optional) | Offline seed (pre-D.5) | **Retain** + document unused by web pipeline |
| `PRODUCTION_EXCEL` shared path | settings / Version8 webapp config | Offline default workbook path | **Retain** — web uses run-scoped `VB1_EXCEL_REL` |
| R.2A GN pointer under `engine/src/...` | settings `R2A_GN_POINTER` | Production (web pointer file) | **Retain** |
| `v7_root` param names in R13/VB1 APIs | Version8 engineering packages | Dev alias = engine/run root (Version8) | **Retain** — offline runners; not Version7 path |
| `Benchmark_Set_2` GN fallback | `PhaseR.2A/.../engineering_context_factory.py` | Offline discovery only | **Retain** — web uses pointer; debt register |
| Excel “Benchmark Set” drawing labels | `excel_structure_builder.py` | Engineering Excel content | **Retain** — changing would alter workbook output |
| Version7 seed text in webapp README | `Version8/webapp/README.md` | Misleading production docs | **Removed** |
| Empty `_ensure_r3_prerequisites` | both estimation services | Dead migration stub | **Removed** |
| Health `phase: D.4.2` | `current_model/webapp/routes.py` | Obsolete migration label | **Updated** |

---

## 3. Version7 reference audit

| Area | Verdict |
|------|---------|
| PRODUCTION_STAGES runners | No Version7 path resolution |
| Web estimation services | No Version7 seed / copy |
| Download endpoint | Same-run Excel only |
| `settings.V7_ROOT` | Exists; **not** referenced by production stages |
| Historical D.4.2.1 / D.5.x docs | Keep as Historical Migration Record |
| Offline CLI under `Version8/Run_PY` | May use `run_root=engine_root` (Version8), not Version7 |

---

## 4. Benchmark terminology audit

| Surface | Status |
|---------|--------|
| Production UI templates / JS | No Benchmark labels |
| Health endpoint | No Benchmark / Version7 |
| Production logs (web services) | Cleaned of migration phase tags |
| README / PIPELINE / ReleaseNotes (current) | Production drawing-set language |
| D.5.x migration docs | Historical — Benchmark mentioned in context of migration |
| Excel Drawing Reference cells | Unchanged (engineering output parity) |
| Offline R.2A factory fallback folder name | Retained (`Benchmark_Set_2`) — offline only |

---

## 5. Health endpoint updates

**Before:** `"phase": "D.4.2"`  
**After:**

```json
{
  "status": "ok",
  "phase": "Production Ready",
  "production_status": "stable_baseline",
  "model_version": "8.9.5",
  "engine_ready": true,
  "ezdxf_available": true,
  "engine_root": "...",
  "web_runs_root": "...",
  "upload_folder": "...",
  "run_context": {
    "STEEL_ENGINE_ROOT": "...",
    "STEEL_RUN_ROOT": "<web_runs>/<run_id>",
    "STEEL_OUTPUT_ROOT": "<web_runs>/<run_id>/data/output"
  },
  "timestamp": "..."
}
```

Version8/webapp now exposes `/health` with the same production descriptors.

---

## 6. Logging cleanup summary

| Removed / reworded | Replacement |
|--------------------|-------------|
| `D.5.5 pipeline complete ...` | `Pipeline complete ...` |
| `Keeping run tree ... (D.5.1 per-run artefacts)` | `Run artefacts retained staging=...` |
| Dead `_ensure_r3_prerequisites` docstring noise | Function removed |

Retained: runner start/finish, exit codes, soft-success artefact checks, errors, timings, run_id, artefact paths.

---

## 7. Documentation updates

| Document | Change |
|----------|--------|
| `Phase_D.5.6_Production_Validation_Cleanup.md` | This file |
| `Production_Architecture_8.9.5.md` | Permanent architecture reference |
| `Technical_Debt_Register_8.9.5.md` | Future work only |
| `Production_Pipeline_Complete_8.9.4.md` | Marked historical; points to 8.9.5 |
| Phase_D.5.1–D.5.5 docs | Banner: Historical Migration Record |
| README / ReleaseNotes / PIPELINE / model_info | 8.9.5 baseline |
| `Version8/webapp/README.md` | Production pipeline; no Version7 seed |

---

## 8. Repository cleanup recommendations

| Item | Recommendation | Auto-deleted? |
|------|----------------|---------------|
| `_commit_msg*.txt` (repo root, untracked) | Delete local temp drafts | Optional local only |
| `Version8/Demo1/` (untracked) | Review; keep if demo assets needed | No |
| Historical `Phase_D.5.*` docs | Keep as Historical Migration Record | No |
| `Version7/` tree (if present on disk) | Not required for production; do not delete from monorepo without separate review | No |
| Shared `Version8/data/output/` historical artefacts | Offline only; safe to ignore for web | No |
| `PRODUCTION_EXCEL` / `V7_ROOT` settings constants | Keep documented; remove in a future major cleanup if offline tools drop them | No |

---

## 9. Final production architecture

See [Production_Architecture_8.9.5.md](Production_Architecture_8.9.5.md).

---

## 10. Technical debt register

See [Technical_Debt_Register_8.9.5.md](Technical_Debt_Register_8.9.5.md).

---

## 11. Files modified

- `Steel-Beam-Estimation/current_model/webapp/routes.py`
- `Steel-Beam-Estimation/current_model/webapp/services.py`
- `Steel-Beam-Estimation/current_model/webapp/config.py`
- `Steel-Beam-Estimation/current_model/config/settings.py`
- `Steel-Beam-Estimation/current_model/config/model_info.yaml`
- `Version8/webapp/routes.py`
- `Version8/webapp/app.py`
- `Version8/webapp/config.py`
- `Version8/webapp/services/estimation_service.py`
- `Version8/webapp/README.md`
- `Version8/src/config/run_context.py`
- `Version8/PIPELINE.md`
- `Steel-Beam-Estimation/README.md`
- `Steel-Beam-Estimation/docs/*` (D.5.6 + architecture + debt + banners)

---

## 12. MODEL_VERSION

`8.9.5` — **Stable Production Baseline**

---

## 13. Suggested git commit message

```text
chore(D.5.6): stabilize production baseline MODEL_VERSION 8.9.5

Cleanup migration stubs/labels, refresh health endpoint and docs;
no engineering behaviour change from 8.9.4.
```

---

## 14. Production readiness certification

| Criterion | Status |
|-----------|--------|
| Upload → Excel validated on Lightsail (8.9.4) | Certified |
| RunContext per-run isolation | Certified |
| No Version7 dependency on production path | Certified |
| No Benchmark execution implied in production UI/health | Certified |
| Health reflects Production Ready / 8.9.5 | Certified |
| Docs match implemented PRODUCTION_STAGES | Certified |
| Engineering behaviour frozen vs 8.9.4 | Certified |
| Remaining debt documented (not implemented) | Certified |

**Certification:** MODEL_VERSION **8.9.5** is the official stable production
baseline for future development.
