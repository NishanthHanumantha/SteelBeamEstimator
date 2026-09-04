# Repository Forensics Report

**Phase:** 1 — Repository Forensics (read-only)  
**Date:** 2026-08-31  
**Scope:** Entire `SteelBeamEstimator` working tree  
**Deployed production (evidence):** Lightsail public app `http://13.127.104.99/` → Nginx → Gunicorn `wsgi:app` at `127.0.0.1:8001`, `APP_RELEASE=W.19.1`, `HYBRID_MODE=production`, 1 worker, Anthropic 0.125.0 overlay on `Version10/`. Server git checkout may be historical; runtime files are Version10 overlays.

**This phase did not delete, move, rename, or modify any production source.** Only this report file is new.

---

## 1. Executive Summary

The repository is a **multi-generation monorepo** (`Version1`–`Version10` plus an older packaging tree `Steel-Beam-Estimation/`). Live hybrid production is **Version10 only**, entered through `Version10/webapp` and executed as **14 subprocess stages** listed in `Version10/webapp/config.py` `PRODUCTION_STAGES`.

Current production architecture (from code, not from stale READMEs):

DXF upload → V.ROOT.1 discovery → deterministic CAD/geometry (R.1 … R.1.3, including piece generation and M.2 spacers) → T.1 stirrup evidence + W.8 context/detail crops → Claude Vision (C.5 contract / P.253 client) → D.2 semantic hybrid resolve → W.6 handoff onto R.1.3 → VB.1 steel / BBS / Excel.

**Main findings**

1. **Root `README.md` still says Version6 is active.** That is false. Production is Version10 + W.19.1 hybrid.
2. **`Version10/PIPELINE.md` omits T.1 and HYBRID (W.6)** and still cites MODEL_VERSION 8.9.5 / frozen V8 architecture docs.
3. **`Version10/webapp/wsgi.py` header still says “NOT YET DEPLOYED”** while it is the live Gunicorn target.
4. **~55k files** (excluding `.git` / `__pycache__`). Most are **generated artefacts** (`Version10/data` ~23k files) and **historical trees**. Version10 `src` is 129 packages / ~1743 `.py` files; only a minority are on the 14-stage path.
5. **Vision production reuses benchmark packages** (`PhaseP253_*`, `PhaseP2610C5_*`, `PhaseP2610E2_*/live_caller.py`, `PhaseP2610D1_*`, `PhaseP2610D2_*`, W.8 → P.26.10-A/B/B2/C1C2). Those folders also contain **non-production benchmark orchestrators**. Do not archive the folders.
6. **R.2A artefacts have been observed pointing at `Version8/data/Benchmark_Set_2/general_notes/`** even on uploaded runs. Version8 is historically archived **but is not SAFE_TO_ARCHIVE** until GN discovery no longer can load that path.
7. **Cursor/developer confusion risk is CRITICAL** because dozens of similarly named `run_phase_*.py` files, W.12–W.19 deployment scripts, and V8/V9 copies sit next to the real production runners.

**Repository health:** Production hybrid is coherent and deployable. The *tree* is not: it is an experimental lab plus nine frozen engines plus a large generated-data store. Cleanup is warranted **only** after a later controlled archive phase.

---

## 2. Current Production Architecture

**Actual flow discovered from `PRODUCTION_STAGES` + adapters + orchestrators:**

```
Browser  Version10/webapp/templates/index.html + static/js/app.js
    ↓ POST /api/estimate
estimation_service.start_estimation  (upload DXFs → data/web_runs/<run_id>/)
    ↓
version10_adapter.run_pipeline
    ↓ subprocess each stage (STEEL_ENGINE_ROOT, STEEL_RUN_ROOT, STEEL_OUTPUT_ROOT)
VROOT1  PhaseVROOT.1_*          drawing/beam discovery
R1      PhaseR.1_*              DXF reinforcement discovery
T1      PhaseT1_*               geometric stirrup evidence + envelopes
R2A     PhaseR.2A_*             GN cover / grade / Ld table
R21B    PhaseR2.1B_*            semantic interpreter
R21C    PhaseR2.1C_*            fact normalization
R21D    PhaseR2.1D_*            evidence / hypotheses
L22     PhaseL.2.2_*            geometry_registry
R3      PhaseR3_*               geometry context
R31     PhaseR3.1_*             drawing relationships
R12A    PhaseR1_2A_*            geometry accuracy
R13     PhaseR1.3_*             EngineeringBarModel
          ↳ PhaseR1_3_*         piece generation / cut lengths
          ↳ PhaseR1_2B_*        bar consolidation
          ↳ PhaseV9_spacer_rule M.2 spacers / cover
HYBRID  PhaseW6_*               evidence + Vision + D.2 resolve + R13 patch
          ↳ PhaseW8_*           context/detail PNG packages
          ↳ PhaseW5_*           per-beam Claude loop
          ↳ P.253 / C.5 / E.2 live_caller
          ↳ D.1 / D.2           semantic contract + hybrid object
VB1     PhaseVB.1_*             steel_weight + BBS + Excel
    ↓
GET /api/download/<run_id>  Production_Output/Estimation_Output.xlsx
```

**Responsibility split (matches deployed W.6 `handoff.py`):**

| Vision (semantic patch) | Deterministic (protected) |
|---|---|
| Target, layer, physical groups, count, diameter, spec, MAIN/EXTRA, support scope, visual stirrup spec | Geometry, spacers/cover, lengths, Ld engineering, hooks, cut length, stirrup *quantity*, pieces, kg, BBS, Excel |

`HYBRID_MODE=off` skips Claude and leaves R.1.3 unchanged. Failures do not fabricate Vision results.

---

## 3. Production Entry Points

### 3.1 HTTP / process (deployed)

| Entry | Path | How called | Confidence |
|---|---|---|---|
| Gunicorn WSGI | `Version10/webapp/wsgi.py` → `app:app` | `steel-beam-estimator-v10.service` + `gunicorn.w3.conf.py`, bind `127.0.0.1:8001` | High (unit file + live `/health`) |
| Flask factory | `Version10/webapp/app.py` `create_app()` | Imported by wsgi | High |
| Routes | `Version10/webapp/routes.py` | `/`, `/health`, `/api/estimate`, `/api/status/<run_id>`, `/api/download/<run_id>` | High |
| Job orchestration | `Version10/webapp/services/estimation_service.py` | Thread + single-flight `flight_guard` | High |
| Pipeline adapter | `Version10/webapp/services/version10_adapter.py` | `subprocess.run` of `Run_PY` scripts | High |
| Result download | `Version10/webapp/services/result_registry.py` | Reconstructs workbook from run tree | High |
| Hybrid health | `Version10/webapp/services/hybrid_shadow_service.py` | `/health` hybrid block; does **not** double-call Claude when W.6 is a stage | High |
| Dev server | `python app.py` port 5000 | Local only, not Lightsail | High |

**Chain (estimate):**

```
POST /api/estimate
 → estimation_service.start_estimation
 → version10_adapter (14 stages)
 → HYBRID run_production_hybrid
 → VB.1 EstimatorExcelGenerator
 → register_download_ready
 → GET /api/download/<run_id>
```

### 3.2 CLI (same engine, not the public UI)

Each production stage: `Version10/Run_PY/run_phase_*.py` with `config.run_context.resolve_run_context`.

**105** `Run_PY/run_phase_*.py` files exist (full list in the Version10 inventory). Only the 14 below are web-invoked.

The 14 **web-invoked** runners:

- `run_phase_vroot1_dynamic_pipeline_initialization.py`
- `run_phase_r1_generalized_reinforcement_discovery.py`
- `run_phase_t1_geometric_stirrup_evidence.py`
- `run_phase_r2a_engineering_context.py`
- `run_phase_r21b_semantic_interpreter.py`
- `run_phase_r21c_engineering_fact_normalization.py`
- `run_phase_r21d_evidence_hypothesis_engine.py`
- `run_phase_l2_2_geometry_recovery.py`
- `run_phase_r3_geometry_context_engine.py`
- `run_phase_r31_engineering_relationship_engine.py`
- `run_phase_r12a_geometry_accuracy.py`
- `run_phase_r13_pipeline_integration.py`
- `run_phase_w6_hybrid_production_authority.py`
- `run_phase_vb1_production_output_completion.py`

**91 additional `Run_PY/run_phase_*.py` files** (105 − 14) cover P.2 / QA / M.1 / VTEST / L.2 / piece-gen CLI / `vroot1_verify` / `track1_visual_chain`. They are **not** in `PRODUCTION_STAGES`. Treating them as production entry points is a Cursor confusion risk.

Notable non-web runners that look production-named:

- `run_phase_l2_engineering_reinforcement_interpretation.py` — `PhaseL.2 - engineering_reinforcement_interpretation/` exists; **not** a web stage (web uses L.2.2).
- `run_phase_r13_reinforcement_piece_generation.py` — piece generation is loaded **from R.1.3**, not as its own web stage.
- No `run_phase_w5_*` / `run_phase_w8_*`; W.5/W.8 run **inside** W.6.

### 3.3 External APIs

- **Anthropic Claude** via `Version10/src/llm/claude_client.py` wrapped by `PhaseP253_claude_vision_interpretation_pilot/claude_vision_client.py`. Key from process env / dotenv (`ANTHROPIC_API_KEY`). Never log the value.
- No other LLM providers identified on the production path.

### 3.4 Historical / not current public production

| Entry | Status |
|---|---|
| `Steel-Beam-Estimation/current_model/wsgi.py` | Frozen 8.9.5 packaging; systemd comment in v10 unit says old service on `:8000` |
| `Version8/webapp/` | Predecessor UI |
| Root `README.md` Version6 runners | Documentation only; not deployed |

---

## 4. Current Hybrid Pipeline

Traced from `PhaseW6_hybrid_production_authority/orchestrator.py` `run_production_hybrid`.

| Architecture box | Actual module | Call | Inputs | Outputs | Production? | Confidence |
|---|---|---|---|---|---|---|
| DXF | Upload folders under `STEEL_RUN_ROOT` `{general_notes,framing,reinforcement}` | `estimation_service` | Multipart DXF | Staged files | Yes | High |
| Deterministic CAD/geometry | VROOT1→R13 (table in §2) | Subprocess | Run tree | JSON artefacts under `data/output/Phase*` | Yes | High |
| Render / context | `PhaseW8_production_vision_evidence/package.py` `prepare_production_evidence` via `visuals.ensure_visuals` | In-process from W.6 | Beam ids, DXF, T.1 envelopes | `hybrid_evidence/<beam>/context\|detail/selected.png` + `evidence_manifest.json` | Yes | High |
| W.8 crop deps | `PhaseP2610A_*` `render_crop`; `PhaseP2610B_*` adaptive regions; `PhaseP2610B2_*` `validate_render`; `PhaseP2610C1C2_*` selector; `PhaseM.1_*/dxf_renderer.py` | Imports from `generator.py` | DXF session | PNGs | Yes (indirect) | High |
| Fallback crops | `visuals.py` W.6 envelope / T.1 OpenCV crop | If W.8 adapter fails | T.1 `geometry_envelopes.json` | Single crop | Yes | High |
| Vision | `PhaseW5_*/adapter.py` → `live_invoke.call_shadow_beam` → `PhaseP2610E2_*/live_caller.call_live_beam` → `PhaseP2610C5_*/claude_call.call_selected_beam` | Per beam, 2 images | Context+detail PNG, beam_id | JSON parse + audit | Yes | High |
| Prompt / schema | `PhaseP2610C5_*/vision_prompt.py`, `vision_contract.py` | Inside `call_selected_beam` | Beam id | Constrained JSON (no kg/BBS/Ld) | Yes | High |
| Image encode | `PhaseP2610C3_*/claude_client.encode_png` | C.5 | PNG path | API image parts | Yes | High |
| Semantic hybrid | `PhaseW5_*/semantic.py` `resolve_semantic` → `PhaseP2610E1_*/hybrid_runner_adapter` + `PhaseP2610D2_*/resolver.resolve_hybrid_beam` (D.1 field contract) | After successful Vision | Vision JSON + R13 model | `hybrid_semantic` | Yes | High |
| Hybrid resolution write-back | `PhaseW6_*/handoff.py` `apply_production_handoff` | If `HYBRID_MODE=production` | Shadow result | Patched `beam_reinforcement_models_production.json`; pre-hybrid snapshot | Yes | High |
| Deterministic engineering after hybrid | Unchanged cut/spacer/stirrup-qty keys (`PROTECTED_BAR_KEYS`) | VB.1 reads R13 | Patched model | Steel, BBS, Excel | Yes | High |
| Steel | `steel_weight_completion.py` | VB.1 | Models + optional loader | kg | Yes | High |
| BBS | `bbs_completion_engine.py` | VB.1 | Models | BBS rows | Yes | High |
| Excel | `estimator_excel_generator.py`; metadata from `loader_summary_from_r2a_artefacts` (W.19.1) | VB.1 | BBS + steel + R.2A JSON | Five-sheet xlsx | Yes | High |

**Not current Hybrid (do not treat as production Vision):** `PhaseP21`–`PhaseP269` trial gates, `PhaseP253` *pilot orchestrator* (the **client** is production), `PhaseP2610E3` multi-set benchmark, `PhaseM.1` dataset generator CLI, Version6 Claude integration scripts.

---

## 5. Production File Inventory

**Convention:** Rows are **packages or named files** on the deployed path. Individual helper `.py` files inside a listed package inherit the row unless noted. Criticality: **runtime** = required for a live estimate.

| File / package | Role | Category | Production criticality | Confidence |
|---|---|---|---|---|
| `Version10/webapp/wsgi.py` | Gunicorn target | PRODUCTION | runtime | High |
| `Version10/webapp/app.py` | Flask app | PRODUCTION | runtime | High |
| `Version10/webapp/routes.py` | HTTP API | PRODUCTION | runtime | High |
| `Version10/webapp/config.py` | Stages, paths, `APP_RELEASE` | PRODUCTION | runtime | High |
| `Version10/webapp/services/version10_adapter.py` | Subprocess pipeline | PRODUCTION | runtime | High |
| `Version10/webapp/services/estimation_service.py` | Jobs, uploads | PRODUCTION | runtime | High |
| `Version10/webapp/services/result_registry.py` | Download | PRODUCTION | runtime | High |
| `Version10/webapp/services/flight_guard.py` | Single flight | PRODUCTION | runtime | High |
| `Version10/webapp/services/hybrid_shadow_service.py` | Health + no double Claude | PRODUCTION | runtime | High |
| `Version10/webapp/templates/index.html` | UI | PRODUCTION | runtime | High |
| `Version10/webapp/static/js/app.js` | UI | PRODUCTION | runtime | High |
| `Version10/webapp/static/css/app.css` | UI | PRODUCTION | runtime | High |
| `Version10/src/config/run_context.py` | Run isolation | PRODUCTION | runtime | High |
| 14 `Run_PY/run_phase_{vroot1,r1,t1,r2a,r21b,r21c,r21d,l2_2,r3,r31,r12a,r13,w6,vb1}*.py` | Stage CLIs | PRODUCTION | runtime | High |
| `PhaseVROOT.1_dynamic_pipeline_initialization/` | Discovery | PRODUCTION | runtime | High |
| `PhaseR.1_generalized_reinforcement_discovery/` | DXF reinforcement | PRODUCTION | runtime | High |
| `PhaseT1_geometric_stirrup_evidence/` | Stirrup evidence / envelopes | PRODUCTION | runtime | High |
| `PhaseT16_entity_ownership/ownership_renderer.py` | Imported by T.1 | PRODUCTION | runtime (indirect) | Medium |
| `PhaseR.2A_engineering_context/` | Cover / Ld / grades | PRODUCTION | runtime | High |
| `PhaseR2.1B_engineering_semantic_interpreter/` | Semantic objects | PRODUCTION | runtime | High |
| `PhaseR2.1C_engineering_fact_normalization/` | Facts | PRODUCTION | runtime | High |
| `PhaseR2.1D_evidence_hypothesis_engine/` | Hypotheses | PRODUCTION | runtime | High |
| `PhaseL.2.2_geometry_recovery/` | Geometry registry | PRODUCTION | runtime | High |
| `PhaseR3_geometry_context_engine/` | Geometry context | PRODUCTION | runtime | High |
| `PhaseR3.1_engineering_relationship_engine/` | Relationships | PRODUCTION | runtime | High |
| `PhaseR1_2A_geometry_accuracy/` | Geometry catalog | PRODUCTION | runtime | High |
| `PhaseR1.3_pipeline_integration/` | Bar models + spacer/piece hook | PRODUCTION | runtime | High |
| `PhaseR1_2B_engineeringbar_consolidation/` | Loaded by R.1.3 | PRODUCTION | runtime | High |
| `PhaseR1_3_reinforcement_piece_generation/` | Loaded by R.1.3 | PRODUCTION | runtime | High |
| `PhaseV9_spacer_rule/spacer_engine.py` `r13_injector.py` `spacer_models.py` | M.2 spacers | PRODUCTION | runtime | High |
| `PhaseVB.1_production_output_completion/` | Steel, BBS, Excel | PRODUCTION | runtime | High |
| `PhaseW6_hybrid_production_authority/` | Hybrid stage | PRODUCTION | runtime | High |
| `PhaseW5_production_hybrid_shadow/` | Vision loop | PRODUCTION | runtime | High |
| `PhaseW8_production_vision_evidence/` | Evidence packages | PRODUCTION | runtime | High |
| `PhaseW11_hybrid_reliability/` | Timeouts / progress | PRODUCTION | runtime | High |
| `PhaseP2610A_beam_region_crop_audit/` (cropper, title_localizer) | W.8 crop | PRODUCTION | runtime (indirect) | High |
| `PhaseP2610B_adaptive_beam_detail_crop/` | W.8 adaptive | PRODUCTION | runtime (indirect) | High |
| `PhaseP2610B2_render_quality_directional_recovery/quality.py` | W.8 validate | PRODUCTION | runtime (indirect) | High |
| `PhaseP2610C1C2_evidence_inventory_candidate_selection/` | W.8 select | PRODUCTION | runtime (indirect) | High |
| `PhaseM.1_engineering_vision_dataset/dxf_renderer.py` | Render | PRODUCTION | runtime (indirect) | High |
| `PhaseP253_*/claude_vision_client.py` | Claude wrapper | PRODUCTION | runtime | High |
| `src/llm/claude_client.py` `claude_config.py` | Anthropic SDK | PRODUCTION | runtime | High |
| `PhaseP2610C5_*/claude_call.py` `vision_prompt.py` `vision_contract.py` `normalize.py` | Live Vision contract | PRODUCTION | runtime | High |
| `PhaseP2610C3_*/claude_client.py` (`encode_png`) | PNG encode | PRODUCTION | runtime | High |
| `PhaseP2610E2_*/live_caller.py` | Live retry / fail-closed | PRODUCTION | runtime | High |
| `PhaseP2610E1_*/hybrid_runner_adapter.py` | Vision vs det payload | PRODUCTION | runtime | High |
| `PhaseP2610D1_vision_semantic_contract_hybrid_foundation/` (resolver, validator, normalizer) | Field authority | PRODUCTION | runtime | High |
| `PhaseP2610D2_shadow_hybrid_semantic_resolver/resolver.py` `matching.py` `canonical.py` | Hybrid object | PRODUCTION | runtime | High |

**Mixed folders (same directory, not all files production):** C.5, C.3, E.1, E.2, P.253, M.1 also contain `phase_*_orchestrator.py`, `report.py`, PDF writers, anti-hardcoding harnesses. Those **orchestrators are not** `PRODUCTION_STAGES`. Classify those extra files as EXPERIMENTAL / PRODUCTION_TEST inside the same folder. **Do not archive the folder.**

---

## 6. Supporting Production Files

| File / package | Role | Category | Production criticality | Confidence |
|---|---|---|---|---|
| `Version10/webapp/deployment/steel-beam-estimator-v10.service` | systemd | SUPPORTING_PRODUCTION | deploy | High |
| `Version10/webapp/deployment/gunicorn.w3.conf.py` | Gunicorn | SUPPORTING_PRODUCTION | deploy | High |
| `Version10/webapp/deployment/nginx-v10.conf` | Nginx sample | SUPPORTING_PRODUCTION | deploy | Medium |
| `/etc/steel-beam-estimator-v10.env` (server, not in git) | `HYBRID_MODE`, API key | SUPPORTING_PRODUCTION | runtime | High |
| `Version10/webapp/requirements.txt` `Version10/requirements.txt` | Deps | SUPPORTING_PRODUCTION | deploy | High |
| `Version10/webapp/deployment/steel-beam-estimator-v10.env.example` | Env template (no secrets) | SUPPORTING_PRODUCTION | deploy | High |
| `Version10/webapp/deployment/pack_w191.py` `_w191_deploy.sh` | Last overlay pack | SUPPORTING_PRODUCTION | ops | High |
| Older `pack_w3.py`–`pack_w19.py`, `_w*_deploy.sh` | Historical overlay recipes | SUPPORTING_PRODUCTION / ARCHIVED mix | ops history | Medium |
| `Version10/config/*.yaml` | Engine YAML | SUPPORTING_PRODUCTION | some stages | Medium |
| Root `.env` | Local secrets | SUPPORTING_PRODUCTION | local/runtime | High — **never archive publicly** |
| `Version10/webapp/.gitignore` | VCS | SUPPORTING_PRODUCTION | — | High |

---

## 7. Production Tests / Validation

**Current (keep accessible):**

| File | Role | Category | Criticality | Confidence |
|---|---|---|---|---|
| `Version10/webapp/tests/test_w2_smoke.py` | Adapter/smoke | PRODUCTION_TEST | High | High |
| `test_w5_hybrid_shadow.py` | Hybrid shadow | PRODUCTION_TEST | High | High |
| `test_w6_hybrid_authority.py` | W.6 handoff | PRODUCTION_TEST | High | High |
| `test_w12_result_delivery.py` | Download | PRODUCTION_TEST | High | High |
| `test_w13_hybrid_download.py` | Hybrid download | PRODUCTION_TEST | High | High |
| `test_w14_hybrid_recovery.py` | Recovery | PRODUCTION_TEST | High | High |
| `test_w16_metadata_aggregation.py` | GN / B27 / frame | PRODUCTION_TEST | High | High |
| `test_w191_excel_metadata_binding.py` | Excel R.2A bind | PRODUCTION_TEST | High | High |
| `PhaseV9_spacer_rule/tests/test_spacer_engine.py` | Spacer math | PRODUCTION_TEST | High | High |
| `PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py` | W.18B | PRODUCTION_TEST | High | High |
| `PhaseW6_hybrid_production_authority/unit_tests.py` | W.6 units | PRODUCTION_TEST | High | High |
| `PhaseW5_production_hybrid_shadow/unit_tests.py` | W.5 units | PRODUCTION_TEST | High | High |
| `PhaseW8_production_vision_evidence/unit_tests.py` | W.8 units | PRODUCTION_TEST | Medium | High |

**Historical / experimental validation (not required to boot production):**

- `Version10/webapp/tests/run_w6_live_e2e.py`, `run_live_e2e.py`, `run_w8_live_verify.py`, `run_w21_scale_e2e.py`
- `Version10/webapp/deployment/smoke_w3.py` … `e2e_w14_*.py`, `_w13_live_18.py`, `_w19_galera_local.py`
- All `PhaseP2610E*` / `PhaseQA*` / `PhaseVA.2` / `PhaseVTEST*` runners and reports
- `PhaseP253` benchmark_evaluator, `PhaseP2610C5` strata sampler

These remain useful for regression **if** kept labeled as ops/benchmark, not as alternate entry points.

---

## 8. Experimental Files

Group (do not archive blindly; many **export functions later imported by production**):

| Group | Approx. `.py` | Notes |
|---|---|---|
| `PhaseP21`–`PhaseP24`, `PhaseP250*`–`PhaseP259` | Large | Vision candidate / crop / field-repair **trials**. W.8 only imports a **subset** of P.26.10-A/B/B2/C1C2. |
| `PhaseP261`–`PhaseP269` | Large | Longitudinal gates, live arbitration — **not** web stages. |
| `PhaseP2610B1/B3`, `C4`, `D3`, `D4`, `E3` | Large | Benchmarks / directional recovery not shown as W.8 imports in `generator.py`. |
| `PhaseQA*`, `PhaseVA.2`, `PhaseVTEST*`, `PhaseVRUN.1` | Medium | Accuracy / re-execution labs. |
| `PhaseR1_4`, `R1_5`, `R1_6*`, `R2.0*`, `R2.1A`, `R.2B`, `SI.0`, `SI.1` | Medium | Not in `PRODUCTION_STAGES`. May still be imported dynamically — **REVIEW_REQUIRED** before archive. |
| `PhaseM.1` except `dxf_renderer.py` | Dataset CLI | EXPERIMENTAL + one PRODUCTION renderer. |
| `Run_PY` except the 14 web runners | ~93 scripts | Experimental CLIs. |
| `src/ai/` | 16 | Not on traced hybrid path. |

---

## 9. Archived / Historical Implementations

| Old implementation | Current replacement | Evidence | Status | Safe to archive? |
|---|---|---|---|---|
| `Version1/`–`Version7/` | Version10 | Root README (stale) vs `webapp/config.py` ENGINE_LABEL Version10; no Lightsail cwd | Frozen engines | **LIKELY_SAFE** for V1–V7 source **after** confirming no `sys.path` into them. **UNCERTAIN** if any runner still hardcodes Version7 paths. |
| `Version8/` engine + `Version8/webapp` | Version10 web + engine | V10 runners comments still say “Version8/”; VB.1 comments mention Version8 defaults; **R.2A `gn_dxf` observed on Version8 Benchmark_Set_2** | Historical + **accidental runtime GN path** | **DO_NOT_ARCHIVE** whole Version8 until GN discovery is proven run-scoped only |
| `Version9/` | Version10 | R.1 runner docstring still says MODEL_VERSION 9.2.0 / Version9 | Fork leftover | **REVIEW_REQUIRED** (15k files, likely data+src) |
| `Steel-Beam-Estimation/` 8.9.5 web + docs | Version10 webapp + W.19.1 | Unit file comments; `Production_Architecture_8.9.5.md` | Frozen packaging | **LIKELY_SAFE** as *docs/history*; **UNCERTAIN** if ops still follow those deploy scripts |
| Version6 “active development” README | Version10 | `README.md` vs production | Doc-only | Docs conflict; tree LIKELY_SAFE as archive |

---

## 10. Duplicate / Superseded Files

| Item | Notes |
|---|---|
| Same phase names in Version7/8/9/10 `src/` | Copies evolved in place; **Version10 is authoritative for production** |
| `Steel-Beam-Estimation/current_model/webapp/*` vs `Version10/webapp/*` | Duplicate UI generation |
| `Version8/webapp` vs `Version10/webapp` | Duplicate |
| Multiple `gunicorn.*.conf.py` (`w3`, `w21`) | Live uses **w3**; w21 is alternate/historical |
| Multiple `pack_w*.py` | Each release overlay; latest production overlay recipe is **pack_w191** on top of W.19 files |
| `ARCHITECTURE_SUMMARY_RecentV10_21_8.md` vs `Version10/V10_Report_Docs/Architecture Summary.docx` vs root README | Three architecture stories |

Do **not** delete duplicates in Phase 1.

---

## 11. Generated / Temporary Artifacts

| Location | Category |
|---|---|
| `Version10/data/output/**` | GENERATED_ARTIFACT (phase JSON, crops, PDFs, fixtures) |
| `Version10/data/web_runs/**` | GENERATED_ARTIFACT (production run trees) |
| `Version10/Downloaded_Output/**` | GENERATED_ARTIFACT |
| `Version10/webapp/uploads`, `outputs`, `logs` | GENERATED_ARTIFACT |
| `out_local_crop*.txt` (repo root) | GENERATED_ARTIFACT |
| `Test_Input/**/~$*` Office locks | GENERATED_ARTIFACT (do not commit) |
| `.pytest_cache` | GENERATED_ARTIFACT |
| `Version10/webapp/.venv_w21` (and any `.venv`) | Environment, not source; inflates `webapp/` file counts |

`Version10/data` ≈ **23,355 files** — dominant bulk of Version10.

---

## 12. Unknown / Manual Review

Prefer UNKNOWN over forced classification.

| Item | Why unknown |
|---|---|
| `Version10/src/reinforcement/` (79 `.py`) | Not imported by R.1/W.5/VB.1 greps; may be used by other phases |
| `engineering_geometry/`, `engineering_specifications/`, `property_*`, `project/`, `parser/`, `extractor/`, `services/`, `utils/` | Shared libs; need import graph from all 14 orchestrators |
| `PhaseL.2 - engineering_reinforcement_interpretation/` | Has `run_phase_l2_engineering_reinforcement_interpretation.py`; R.1.3 still references its **output path**. **Not** in `PRODUCTION_STAGES` (web uses L.2.2). |
| `PhaseR2.1A_*`, `PhaseR.2B_*`, `PhaseR2.0*` | Adjacent to R.2.1B; not a web stage |
| `PhaseR1_2C_*`, `PhaseR1_2D_*` | Detailing / intent; may be nested from R.1 or R.1.3 |
| `PhaseT17*`, `PhaseT18*` | Ownership/render; T.1 only grepped T16 |
| `PhaseW10_hybrid_production_monitoring/` | Ops metrics; not in PRODUCTION_STAGES |
| `src/ai/` | Unused on traced path |
| `src/llm/` except Claude client | P.253 loads `llm.ClaudeClient`; other llm modules **may** load transitively |
| `BeamReinforcement_Bars_Identification/`, `Claude/`, `Prompt/`, `scripts/`, `Set1&2_Model_Output/` | Outside Version10; no production import found |
| `Version10/src/PhaseP2610B1_*` (imported? not in W.8 generator header) | Population generalization — **REVIEW** |
| Dynamic `importlib` in R.1.3 / VB.1 / runners | Easy to miss a package |

---

## 13. Cursor Confusion Risks

| File | Why confusing | Current override | Future action (Phase 2+) | Risk |
|---|---|---|---|---|
| `README.md` | States **Version6 is active** | Version10 webapp + W.19.1 | Rewrite README to Version10 hybrid; mark V1–V6 archive | **CRITICAL** |
| `Version10/PIPELINE.md` | Pipeline **without T.1 or HYBRID**; MODEL 8.9.5; points at V8 architecture doc | `webapp/config.py` PRODUCTION_STAGES | Update pipeline list | **CRITICAL** |
| `Version10/webapp/wsgi.py` docstring | “**NOT YET DEPLOYED**”, bind `:8000` | Live Gunicorn `:8001` `wsgi:app` | Fix comment only (later) | **CRITICAL** |
| `Steel-Beam-Estimation/docs/Production_Architecture_8.9.5.md` | Certified **deterministic 8.9.5**, no hybrid | Version10 W.6 production | Banner “historical” | **HIGH** |
| `ARCHITECTURE_SUMMARY_RecentV10_21_8.md` + docx in `V10_Report_Docs` | Correct hybrid *concept* but not wired to file names | This report + `config.py` | Cross-link | **MEDIUM** |
| ~105 `Run_PY/run_phase_*.py` | Looks like 105 production CLIs | Only 14 in PRODUCTION_STAGES | Index file / folder split later | **HIGH** |
| Version7/8/9/10 duplicate `Phase*` names | Cursor may edit wrong tree | `STEEL_ENGINE_ROOT=Version10` | Archive old versions | **HIGH** |
| `run_phase_r1_*.py` header “Usage from Version9/” | Wrong engine generation | Version10 src | Comment fix later | **HIGH** |
| `pack_w3.py` … `pack_w19.py` in `deployment/` | Many “current” pack scripts | Last live overlay: W.19 + W.19.1 files | Keep latest; label others historical | **MEDIUM** |
| `gunicorn.w21.conf.py` | Alternate workers/config | Production uses **w3** + 1 worker | Label | **MEDIUM** |
| PhaseP253 *pilot* vs production client | Name says pilot | `claude_vision_client.py` is live | Rename later (not now) | **MEDIUM** |
| E.2 package name “fifth_set_…_benchmark” | Looks like a one-off study | `live_caller.py` is production | Comment / split later | **HIGH** |
| `HYBRID_MODE=off` default in systemd unit file | Unit defaults off; **server env file** sets production | `/etc/steel-beam-estimator-v10.env` | Document env overlay | **MEDIUM** |

---

## 14. Documentation Conflicts

| Document | Current description | Actual implementation | Conflict | Severity | Recommended future update |
|---|---|---|---|---|---|
| Root `README.md` | Version6 active; V1–V5 frozen | Version10 hybrid production | Wrong active tree | **CRITICAL** | Point to Version10 webapp |
| `Version10/PIPELINE.md` | 12 stages, no T1/HYBRID; 8.9.5 | 14 stages including T1+W.6 | Incomplete pipeline | **CRITICAL** | Match PRODUCTION_STAGES |
| PIPELINE.md “Certified … V8” | Frozen V8 architecture | Hybrid W.16–W.19.1 on V10 | Old certification | **HIGH** | Historical pointer only |
| `wsgi.py` header | Not deployed | Deployed | False | **HIGH** | Align comment |
| `Steel-Beam-Estimation/docs/Architecture.md` / 8.9.5 | Pre-hybrid web | Version10 | Stale | **HIGH** | Archive banner |
| `V10_Report_Docs/Architecture Summary.docx` | Hybrid split (correct conceptually) | Matches W.6/W.8/VB.1 | Low conflict; missing file map | **LOW** | Add package names |
| Many `PHASE_W*_CHECKPOINT.md` | Sequential ops truth at that date | Later W.19.1 superseded some | Stale-as-of-date (OK if dated) | **LOW–MED** | Keep as history |

**Not rewritten in this phase.**

---

## 15. Archive Candidates

**Nothing moved.**

| File/folder | Category | Reason | Dependency check | Production impact | Archive confidence |
|---|---|---|---|---|---|
| `Version1/`–`Version5/` | ARCHIVED | Frozen per README | No production import found | None if unused | LIKELY_SAFE_TO_ARCHIVE |
| `Version6/` `Version7/` | ARCHIVED | Predecessor engines | Comments/paths may remain | Uncertain | REVIEW_REQUIRED |
| `Version8/` **source** | ARCHIVED | Fork origin | **GN fallback path used Version8 Benchmark_Set_2 DXF** | Could change Cover/Ld if discovery uses it | **DO_NOT_ARCHIVE** until R.2A run-scoped GN is exclusive |
| `Version8/data/Benchmark_Set_2/` | GENERATED/SUPPORT mix | Observed `gn_dxf` target | Runtime fallback | High if deleted | **DO_NOT_ARCHIVE** |
| `Version9/` | ARCHIVED + generated bulk | 15k files | Docstrings still say V9 | Unknown | REVIEW_REQUIRED |
| `Steel-Beam-Estimation/` | ARCHIVED packaging | 8.9.5 | Not v10 gunicorn | Ops docs only | LIKELY_SAFE_TO_ARCHIVE (docs first) |
| `Prompt/` `Claude/` `BeamReinforcement_*` | UNKNOWN | Pre-V10 notes | None found | None expected | REVIEW_REQUIRED |
| `out_local_crop*.txt` | GENERATED | Debug | None | None | SAFE_TO_ARCHIVE |
| `Version10/data/output/**` old phase dumps | GENERATED | Regenerable | Some tests may fixture | Tests may break | REVIEW_REQUIRED |
| `Version10/Downloaded_Output/**` except committed W.19/W.19.1 xlsx | GENERATED | Downloads | None for runtime | None | LIKELY_SAFE_TO_ARCHIVE |
| `Run_PY` experimental runners (91 of 105) | EXPERIMENTAL | Not in PRODUCTION_STAGES | Some used by humans | None for web | REVIEW_REQUIRED (keep 14) |
| Entire `PhaseP250*` except W.8 imports | EXPERIMENTAL | Trials | W.8 does **not** import most | If archive whole P250*, W.8 still needs A/B/B2/C1C2 | **DO_NOT_ARCHIVE** P2610A/B/B2/C1C2 |

---

## 16. DO NOT TOUCH — Production Critical Files

Do not move/delete/refactor in cleanup without a dedicated production gate:

**Web / deploy**

- `Version10/webapp/{wsgi.py,app.py,routes.py,config.py}`
- `Version10/webapp/services/{version10_adapter.py,estimation_service.py,result_registry.py,flight_guard.py,hybrid_shadow_service.py}`
- `Version10/webapp/{templates,static}`
- `Version10/webapp/deployment/{gunicorn.w3.conf.py,steel-beam-estimator-v10.service,nginx-v10.conf}`
- `Version10/webapp/requirements.txt`, `Version10/requirements.txt`
- Server: `/etc/steel-beam-estimator-v10.env`, Gunicorn 1 worker, `HYBRID_MODE`, Anthropic pin

**Fourteen runners + `src/config/run_context.py`**

**Deterministic packages listed in §5** including `PhaseV9_spacer_rule` (except adding tests), `PhaseR1_3_*`, `PhaseR1_2B_*`, `PhaseVB.1_*` (including W.19.1 `loader_summary_from_r2a_artefacts`).

**Hybrid / Vision**

- `PhaseW5_*`, `PhaseW6_*`, `PhaseW8_*`, `PhaseW11_*`
- `PhaseP253_*/claude_vision_client.py`
- `src/llm/claude_client.py`, `claude_config.py`
- `PhaseP2610C5_*/{claude_call,vision_prompt,vision_contract,normalize}.py`
- `PhaseP2610C3_*/claude_client.py` (encode)
- `PhaseP2610E2_*/live_caller.py`
- `PhaseP2610E1_*/hybrid_runner_adapter.py`
- `PhaseP2610D1_*` (contract modules)
- `PhaseP2610D2_*/{resolver,matching,canonical}.py`
- W.8 dependencies: `PhaseP2610A_*` cropper/title_localizer, `PhaseP2610B_*`, `PhaseP2610B2_*/quality.py`, `PhaseP2610C1C2_*`, `PhaseM.1_*/dxf_renderer.py`

**Production tests in §7 “Current”**

**Do not “fix” R.2A GN discovery, stirrup/longitudinal, or hybrid prompts as part of cleanup.**

---

## 17. Recommended Phase 2 Cleanup Plan

**Do not execute in this phase.**

1. Freeze a git tag of current `main` (includes W.19.1).
2. Add a root `PRODUCTION.md` pointing at Version10 14-stage list (docs-only).
3. Mark `README.md` / `PIPELINE.md` / `wsgi.py` header as stale (docs-only PR).
4. Inventory Version8 `Benchmark_Set_2` GN usage; **block Version8 delete** until that is closed.
5. Move **only** `SAFE_TO_ARCHIVE` generated debug files (`out_local_crop*.txt`) and Office lock files.
6. Optionally relocate `Version1`–`Version5` to `archive/` **after** a grep for `Version5/` `Version6/` path literals from Version10.
7. Do **not** split P.253/C.5/E.2 folders until imports are listed in a lockfile.
8. Do **not** delete `Run_PY` experimental runners until a manifest of “web 14 vs rest” exists.
9. Keep `data/web_runs` operator-retained (production policy).
10. Re-run W.16 + W.18B + W.19.1 unit tests and one Galera smoke after any move.

---

## 18. Final Repository Classification Summary

Counts are **approximate file counts** (excluding `.git` / `__pycache__`). Production/experimental `.py` counts are from `Version10/src` package grouping; mixed benchmark-in-production-folder files are counted with their package (conservative: over-counts PRODUCTION vs EXPERIMENTAL).

| Category | Count (approx.) | Basis |
|---|---|---|
| **PRODUCTION** | ~472 `.py` in traced packages + ~20 webapp core `.py` + 14 runners | §5 packages (includes some in-folder benchmark extras) |
| **SUPPORTING_PRODUCTION** | ~50–150 | systemd, gunicorn, requirements, config yaml, pack/deploy of W.19.1 |
| **PRODUCTION_TEST** | ~25–40 | Listed unit/web tests |
| **EXPERIMENTAL** | ~856 `.py` grouped P/QA leftover + **91** extra Run_PY (105 − 14) | §8 |
| **ARCHIVED** | Version1–7 ~5.3k files; Version8–9 large (V9 15k); Steel-Beam-Estimation 61 | Historical trees |
| **DUPLICATE_OR_SUPERSEDED** | Overlaps inside V7–V10 phase copies (not separately counted) | §10 |
| **GENERATED_ARTIFACT** | Version10/data ~23,355; plus downloads, crops, caches | §11 |
| **DOCUMENTATION** | `webapp/deployment/PHASE_*.md` (~100+), `V10_Report_Docs`, root md | — |
| **UNKNOWN_REVIEW_REQUIRED** | Remaining Version10 `src` (~1743 − 472 − 856 ≈ **415** `.py`) + `Prompt/` `Claude/` `scripts/` `reinforcement/` etc. | §12 |

**Whole-repo files ~55,951.** Majority GENERATED + ARCHIVED, not production source.

---

## Phase 1 validation checklist

- [x] No production source files modified
- [x] No deletions / moves / renames
- [x] No dependency or config changes
- [x] Hybrid entry points identified (`wsgi` → adapter → W.6 → VB.1)
- [x] Vision components identified (W.8, W.5, C.5, P.253, E.2 `live_caller`)
- [x] Deterministic engineering identified (R.* , T.1, V9 spacer, piece gen, VB.1)
- [x] Quantity / BBS / Excel traced to VB.1
- [x] Current production tests listed
- [x] Historical implementations separated
- [x] Cursor-confusion risks listed
- [x] Documentation conflicts listed
- [x] Unknown files reported
- [x] Archive candidates listed without moving
- [x] This file created
- [x] No existing files modified
