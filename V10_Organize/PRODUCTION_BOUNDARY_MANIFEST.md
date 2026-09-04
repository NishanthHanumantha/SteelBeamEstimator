# Production Boundary Manifest

**Phase:** 2 — Production Boundary & Safe Cleanup  
**Date:** 2026-08-31  
**Baseline:** `REPOSITORY_FORENSICS_REPORT.md` (Phase 1)  
**Companion docs:** `PRODUCTION_TRUTH.md`, `PRODUCTION_MODULE_INDEX.md`, `RUNNER_MANIFEST.md`

This file identifies the **current Version10 Hybrid production boundary**.  
It does **not** restructure packages. Mixed folders stay mixed.

---

## 1. Production Entry Points

| Component | Path | Role |
|---|---|---|
| WSGI | `Version10/webapp/wsgi.py` | Gunicorn target `wsgi:app` |
| Flask app | `Version10/webapp/app.py` | `create_app()` / `app` |
| Routes | `Version10/webapp/routes.py` | `/`, `/health`, `/api/estimate`, `/api/status/<run_id>`, `/api/download/<run_id>` |
| Config | `Version10/webapp/config.py` | `PRODUCTION_STAGES` (14), `APP_RELEASE=W.19.1`, paths |
| Estimation jobs | `Version10/webapp/services/estimation_service.py` | Upload DXFs, thread, single-flight |
| Pipeline adapter | `Version10/webapp/services/version10_adapter.py` | Subprocess each stage; sets `STEEL_*` env |
| Result registry | `Version10/webapp/services/result_registry.py` | Workbook reconstruction / download |
| Flight guard | `Version10/webapp/services/flight_guard.py` | One live estimate at a time |
| Hybrid health | `Version10/webapp/services/hybrid_shadow_service.py` | `/health` hybrid block; no double Claude when W.6 is a stage |
| UI | `Version10/webapp/templates/index.html`, `static/js/app.js`, `static/css/app.css` | Browser |
| Run context | `Version10/src/config/run_context.py` | `STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT` |
| Claude SDK | `Version10/src/llm/claude_client.py`, `claude_config.py` | Used by P.253 client |

**Estimate chain:**

```
POST /api/estimate
  → estimation_service.start_estimation
  → version10_adapter.run_pipeline (14 subprocess stages)
  → W.6 run_production_hybrid
  → VB.1 EstimatorExcelGenerator
  → result_registry / GET /api/download/<run_id>
```

Adapter env (every stage):

- `STEEL_ENGINE_ROOT` = Version10  
- `STEEL_RUN_ROOT` = `data/web_runs/<run_id>`  
- `STEEL_OUTPUT_ROOT` = `<run>/data/output`  
- `cwd` = Version10  

**Phase 3 (2026-08-31):** R.2A and R.2.1B runners load **Version10** `src` with `engine_root=Version10`. See § Version8 gate (CLOSED).

---

## 2. Production Stage Manifest

Source of truth: `Version10/webapp/config.py` `PRODUCTION_STAGES` (exactly **14**).

### Stage 1 — VROOT1

| Field | Value |
|---|---|
| STAGE | VROOT1 |
| RUNNER | `Version10/Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/` |
| DIRECT DEPENDENCIES | Drawing classifier, beam discovery, registry builders in the same package |
| IMPORTANT INDIRECT | CLI default input can fall back to `Version8/data/Benchmark_Set_*` if no folder is passed. **Web always passes the upload folder.** |
| OUTPUTS | `beam_registry.json`, drawing/project manifests under `PhaseVROOT.1_*` |
| NEXT STAGE | R1 |

### Stage 2 — R1

| Field | Value |
|---|---|
| STAGE | R1 |
| RUNNER | `run_phase_r1_generalized_reinforcement_discovery.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR.1_generalized_reinforcement_discovery/` |
| DIRECT DEPENDENCIES | DXF annotation / grouping modules in the same package; `config.run_context` |
| IMPORTANT INDIRECT | YAML `Version10/config/generalized_reinforcement_discovery.yaml` |
| OUTPUTS | Reinforcement annotations / discovery artefacts under `PhaseR.1_*` |
| NEXT STAGE | T1 |

### Stage 3 — T1

| Field | Value |
|---|---|
| STAGE | T1 |
| RUNNER | `run_phase_t1_geometric_stirrup_evidence.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseT1_geometric_stirrup_evidence/` |
| DIRECT DEPENDENCIES | Same-package geometry evidence |
| IMPORTANT INDIRECT | `PhaseT16_entity_ownership/ownership_renderer.py` (imported by T.1); W.8 later uses T.1 envelopes |
| OUTPUTS | `stirrup_geometry_evidence.json`, `geometry_envelopes.json` |
| NEXT STAGE | R2A |

### Stage 4 — R2A

| Field | Value |
|---|---|
| STAGE | R2A |
| RUNNER | `run_phase_r2a_engineering_context.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR.2A_engineering_context/` |
| DIRECT DEPENDENCIES | Version10 parsers + `engineering_context_factory` (W.16 table-title + `STEEL_RUN_ROOT`) |
| IMPORTANT INDIRECT | GN order: run `STEEL_RUN_ROOT/general_notes/` → Version10 `beam_registry.json` pointer → `Version10/data/Benchmark_Set_2/general_notes/`. |
| OUTPUTS | Engineering context JSON under run `PhaseR.2A_engineering_context/` |
| NEXT STAGE | R21B |

### Stage 5 — R21B

| Field | Value |
|---|---|
| STAGE | R21B |
| RUNNER | `run_phase_r21b_semantic_interpreter.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR2.1B_engineering_semantic_interpreter/` |
| DIRECT DEPENDENCIES | Version10 semantic interpreter modules (byte-identical to Version8 package) |
| IMPORTANT INDIRECT | Dictionary YAML from `engine_root` (Version10); R.2.1C reads run-scoped `engineering_semantic_objects.json` |
| OUTPUTS | `engineering_semantic_objects.json` |
| NEXT STAGE | R21C |

### Stage 6 — R21C

| Field | Value |
|---|---|
| STAGE | R21C |
| RUNNER | `run_phase_r21c_engineering_fact_normalization.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR2.1C_engineering_fact_normalization/` (`__file__.parent.parent` = Version10) |
| DIRECT DEPENDENCIES | Same-package fact engine |
| IMPORTANT INDIRECT | R21B artefacts |
| OUTPUTS | `EngineeringFacts.json` |
| NEXT STAGE | R21D |

### Stage 7 — R21D

| Field | Value |
|---|---|
| STAGE | R21D |
| RUNNER | `run_phase_r21d_evidence_hypothesis_engine.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR2.1D_evidence_hypothesis_engine/` |
| DIRECT DEPENDENCIES | Same package |
| IMPORTANT INDIRECT | R21C facts |
| OUTPUTS | `EngineeringFacts.json` (evidence/hypotheses) |
| NEXT STAGE | L22 |

### Stage 8 — L.2.2

| Field | Value |
|---|---|
| STAGE | L22 |
| RUNNER | `run_phase_l2_2_geometry_recovery.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseL.2.2_geometry_recovery/` |
| DIRECT DEPENDENCIES | VROOT1 `beam_registry.json` |
| IMPORTANT INDIRECT | **Not** `PhaseL.2 - engineering_reinforcement_interpretation` (that CLI is not a web stage) |
| OUTPUTS | `geometry_registry.json` |
| NEXT STAGE | R3 |

### Stage 9 — R3

| Field | Value |
|---|---|
| STAGE | R3 |
| RUNNER | `run_phase_r3_geometry_context_engine.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR3_geometry_context_engine/` |
| DIRECT DEPENDENCIES | L.2.2 registry |
| IMPORTANT INDIRECT | — |
| OUTPUTS | `GeometryContexts.json` |
| NEXT STAGE | R31 |

### Stage 10 — R.3.1

| Field | Value |
|---|---|
| STAGE | R31 |
| RUNNER | `run_phase_r31_engineering_relationship_engine.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR3.1_engineering_relationship_engine/` |
| DIRECT DEPENDENCIES | R3 contexts |
| IMPORTANT INDIRECT | — |
| OUTPUTS | `EngineeringDrawingRelationships.json` |
| NEXT STAGE | R12A |

### Stage 11 — R.1.2A

| Field | Value |
|---|---|
| STAGE | R12A |
| RUNNER | `run_phase_r12a_geometry_accuracy.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR1_2A_geometry_accuracy/` |
| DIRECT DEPENDENCIES | Prior geometry artefacts |
| IMPORTANT INDIRECT | — |
| OUTPUTS | `validated_beam_geometry.json` |
| NEXT STAGE | R13 |

### Stage 12 — R.1.3

| Field | Value |
|---|---|
| STAGE | R13 |
| RUNNER | `run_phase_r13_pipeline_integration.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseR1.3_pipeline_integration/` |
| DIRECT DEPENDENCIES | `engineering_bar_builder.py`, `pipeline_integration_manager.py` |
| IMPORTANT INDIRECT | **Dynamic `importlib`:** `PhaseR1_3_reinforcement_piece_generation`, `PhaseR1_2B_engineeringbar_consolidation`, `PhaseV9_spacer_rule` (M.2). **Do not treat missing CLI as unused.** |
| OUTPUTS | `beam_reinforcement_models_production.json` |
| NEXT STAGE | HYBRID (W.6) |

### Stage 13 — HYBRID (W.6)

| Field | Value |
|---|---|
| STAGE | HYBRID |
| RUNNER | `run_phase_w6_hybrid_production_authority.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseW6_hybrid_production_authority/` |
| DIRECT DEPENDENCIES | `orchestrator.py` `run_production_hybrid`; `handoff.py`; `visuals.py`; W.5 adapter; W.8 package |
| IMPORTANT INDIRECT | See §3 Hybrid Boundary (P.253, C.5, E.2, D.1, D.2, P.2610A/B/B2/C1C2, C.3 `encode_png`, M.1 `dxf_renderer`, E.1 adapter + **module-level D.3/D.4/P.269 imports**) |
| OUTPUTS | `hybrid_observability.json`, `hybrid_resolution.json`, patched R13 production model + pre-hybrid snapshot |
| NEXT STAGE | VB1 |

### Stage 14 — VB.1

| Field | Value |
|---|---|
| STAGE | VB1 |
| RUNNER | `run_phase_vb1_production_output_completion.py` |
| PRIMARY PACKAGE | `Version10/src/PhaseVB.1_production_output_completion/` |
| DIRECT DEPENDENCIES | `steel_weight_completion.py`, `bbs_completion_engine.py`, `estimator_excel_generator.py`, `phase_vb1_orchestrator.py` |
| IMPORTANT INDIRECT | W.19.1 `loader_summary_from_r2a_artefacts()` reads **run-scoped R.2A JSON** (does not load Version8 parsers). Comments in the runner still say “Version8/” but `Path(__file__).parent.parent` is Version10. |
| OUTPUTS | `Production_Output/Estimation_Output.xlsx`, steel/BBS JSON |
| NEXT STAGE | *(end — download)* |

---

## 3. Hybrid Boundary

Classify **files**, not whole folders. See `PRODUCTION_MODULE_INDEX.md`.

| Alias | Package | Production files (traced) | Remainder |
|---|---|---|---|
| W.5 | `PhaseW5_production_hybrid_shadow` | adapter, live_invoke, semantic, settings, catalog, comparison, paths, visual_sources, config, cost | `__main__.py` CLI; unit tests |
| W.6 | `PhaseW6_hybrid_production_authority` | orchestrator, handoff, visuals, coverage, config, observability, resolution_trace | `__main__.py`; unit tests |
| W.8 | `PhaseW8_production_vision_evidence` | generator, package, config | unit tests |
| P.253 | `PhaseP253_claude_vision_interpretation_pilot` | `claude_vision_client.py`, `response_schema.py` | pilot orchestrator, benchmark_evaluator, report_builder — EXPERIMENTAL |
| C.5 | `PhaseP2610C5_stratified_vision_semantic_benchmark` | `claude_call.py`, `vision_prompt.py`, `vision_contract.py`, `normalize.py`, `config.py` | sampler, strata, phase orchestrator — EXPERIMENTAL |
| C.3 | `PhaseP2610C3_visual_completeness_claude_shadow` | `claude_client.py` (`encode_png`) | completeness gates, C.3 vision_prompt — EXPERIMENTAL |
| E.2 | `PhaseP2610E2_...live...benchmark` | `live_caller.py` | population benchmark orchestrator — EXPERIMENTAL |
| E.1 | `PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark` | `hybrid_runner_adapter.py` | PDF/KPI/orchestrator — EXPERIMENTAL |
| D.1 | `PhaseP2610D1_vision_semantic_contract_hybrid_foundation` | normalize, vision_normalizer, resolver, vision_validator, config | orchestrator / report — EXPERIMENTAL |
| D.2 | `PhaseP2610D2_shadow_hybrid_semantic_resolver` | resolver, matching, canonical, config | orchestrator — EXPERIMENTAL |
| P.2610A | `PhaseP2610A_beam_region_crop_audit` | cropper, title_localizer | audit orchestrator — EXPERIMENTAL |
| P.2610B | `PhaseP2610B_adaptive_beam_detail_crop` | envelope, completeness | orchestrator — EXPERIMENTAL |
| P.2610B2 | `PhaseP2610B2_render_quality_directional_recovery` | quality.py | recovery pipeline — EXPERIMENTAL |
| P.2610C1C2 | `PhaseP2610C1C2_evidence_inventory_candidate_selection` | config, inventory, selector | orchestrator — EXPERIMENTAL |
| P.2610C3 | (same as C.3) | encode_png only on production path | remainder EXPERIMENTAL |
| P.2610E1 / E.2 | (see E.1 / E.2) | adapter / live_caller | benchmark remainder |
| M.1 | `PhaseM.1_engineering_vision_dataset` | `dxf_renderer.py` | dataset CLI — EXPERIMENTAL |

**Transitive (do not archive):** E.1 `hybrid_runner_adapter.py` imports **D.3**, **D.4**, and **P.269** at module load even though W.5 only *calls* payload builders + D.2.

**Not current Hybrid:** `PhaseP21`–`PhaseP269` trial gates (except P.269 extractor via E.1 import), `PhaseP2610E3`, M.1 dataset generator CLI, Version6 Claude scripts.

---

## 4. Deterministic Engineering Boundary

| Concern | Production modules | Notes |
|---|---|---|
| R.1 | `PhaseR.1_generalized_reinforcement_discovery/` | Version10 src |
| T.1 | `PhaseT1_geometric_stirrup_evidence/` | Web stage 3 |
| R.2A | Version10 `PhaseR.2A_engineering_context/` | Phase 3 closed Version8 runtime load |
| R.2.1B | Version10 `PhaseR2.1B_*` | Phase 3 closed Version8 runtime load |
| R.2.1C / D | Version10 `PhaseR2.1C_*`, `PhaseR2.1D_*` | |
| L.2.2 | Version10 `PhaseL.2.2_geometry_recovery/` | Not L.2 |
| R.3 / R.3.1 | Version10 `PhaseR3_*`, `PhaseR3.1_*` | |
| R.1.2A | Version10 `PhaseR1_2A_geometry_accuracy/` | |
| R.1.3 | Version10 `PhaseR1.3_pipeline_integration/` | Integration + dynamic loads |
| R.1.2B | `PhaseR1_2B_engineeringbar_consolidation/` | Loaded by R.1.3, not a web stage |
| Piece generation | `PhaseR1_3_reinforcement_piece_generation/` | Loaded by R.1.3 |
| M.2 spacers | `PhaseV9_spacer_rule/` (`spacer_engine.py`, `r13_injector.py`, `spacer_models.py`) | Loaded by R.1.3 |
| VB.1 | `PhaseVB.1_production_output_completion/` | Steel, BBS, Excel |
| Steel | `steel_weight_completion.py` | VB.1 |
| BBS | `bbs_completion_engine.py` | VB.1 |
| Excel | `estimator_excel_generator.py` + W.19.1 `loader_summary_from_r2a_artefacts` | VB.1 |

---

## 5. Runtime Resources

| Kind | Location | Notes |
|---|---|---|
| Prompts | C.5 `vision_prompt.py` (production Vision) | Do not treat C.3 `vision_prompt.py` as current production prompt |
| Schemas / contract | C.5 `vision_contract.py`; P.253 `response_schema.py`; D.1 field contract | |
| YAML | `Version10/config/*.yaml` | Stage-specific; `end_to_end_validation.yaml` still cites Version8 workbook paths (validation, not web estimate) |
| Env templates | `Version10/webapp/deployment/steel-beam-estimator-v10.env.example` | Secrets live on server `/etc/steel-beam-estimator-v10.env` |
| systemd | `Version10/webapp/deployment/steel-beam-estimator-v10.service` | Unit default `HYBRID_MODE=off`; live overlay `production` |
| Gunicorn | `gunicorn.w3.conf.py` bind `127.0.0.1:8001`, workers=1 | Live |
| Nginx sample | `nginx-v10.conf` | |
| Static UI | `webapp/static/` | |
| Render | M.1 `dxf_renderer.py`; W.8 evidence PNGs under run tree | |
| Templates | Excel generator internals in VB.1 | |
| Dynamically loaded | R.1.3 `importlib` of pieces / R.1.2B / M.2; R.2A/R21B `importlib` of Version10 packages | |
| Overlay pack | `pack_w191.py` | Latest production overlay recipe |

---

## 6. Production Tests

Keep available for regression (no live Claude unless explicitly requested):

| Test | Path |
|---|---|
| Adapter / 14 stages | `Version10/webapp/tests/test_w2_smoke.py` |
| Hybrid shadow | `test_w5_hybrid_shadow.py` |
| W.6 handoff | `test_w6_hybrid_authority.py` |
| Download | `test_w12_result_delivery.py` |
| Hybrid download | `test_w13_hybrid_download.py` |
| Recovery | `test_w14_hybrid_recovery.py` |
| Metadata | `test_w16_metadata_aggregation.py` |
| Excel R.2A bind | `test_w191_excel_metadata_binding.py` |
| Spacer | `PhaseV9_spacer_rule/tests/test_spacer_engine.py`, `test_w18b_spacer_rule.py` |
| Package units | W.5 / W.6 / W.8 `unit_tests.py` |

Live e2e scripts (`run_w6_live_e2e.py`, `run_live_e2e.py`, `run_w8_live_verify.py`) **consume API credits** — not Phase 2 validation.

---

## Version8 dependency gate

**VERSION8 LIVE R.2A / R.2.1B RUNTIME = CLOSED** (Phase 3, 2026-08-31)

Live web runners now `importlib`-load Version10 packages with `engine_root=Version10`. Version10 factory prefers `STEEL_RUN_ROOT/general_notes`.

**VERSION8 TREE = STILL PRESENT.** Do not delete or move it in this phase.

Remaining **historical** Version8 references (not live R.2A/R.2.1B):

- Non-web `Run_PY` runners that still name Version8 (R.2.1A CLI, SI.0, QA, etc.)
- VROOT1 `_default_input()` Benchmark_Set folders (CLI default only; web passes the upload folder)
- Deployment / rollback docs describing the old `:8000` 8.9.x app

---

## Version1–Version7 archive classification

Searched `Version10/webapp/`, `Version10/webapp/tests/`, `Version10/webapp/deployment/` for `Version1/` … `Version7/` **runtime paths**.

- **No** production Python path into Version1–Version7.  
- Deployment markdown mentions a dirty `Version1/docs/*.docx` as unrelated working-tree only.

Classification: **LIKELY_SAFE_TO_ARCHIVE** for V1–V7 **source trees**.  
**Not moved in Phase 2** (evidence is strong for *webapp*, but historical YAML/comments and duplicate phase trees remain; policy is no broad archival).

**Version8 / Version9:** do not archive. Live R.2A/R.2.1B Version8 runtime is CLOSED; the Version8 tree remains in place. Version9 remains REVIEW_REQUIRED (R.1 docstring still says Version9; large tree).

---

## Git safety note

Working tree was **dirty with unrelated user files** at Phase 2 start. **No checkpoint commit** was created. Manual checkpoint recommended before any later archive work.
