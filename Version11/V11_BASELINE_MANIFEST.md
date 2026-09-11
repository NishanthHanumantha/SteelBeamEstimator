# Version11 Baseline Manifest

**Creation date:** 2026-09-11  
**Source baseline:** Version10 W.19.1 Hybrid (`APP_RELEASE = "W.19.1"`)  
**Source git HEAD at fork:** `59330bda4fc62919ef8e3b1371a5afc377b20161`  
**This document is the authoritative V11 dependency map for phase V11.0.**

No accuracy / model / prompt / engineering-formula changes were introduced. Intentional differences are packaging and identity only (see below).

---

## Copied production boundary

Layout follows Version10 so `ENGINE_ROOT = webapp.parent` still works:

```
Version11/
├── README.md
├── V11_DEVELOPMENT_RULES.md
├── V11_BASELINE_MANIFEST.md
├── V11_DEPENDENCY_CLASSIFICATION.md
├── V11_VS_V10_BASELINE_REPORT.md
├── PHASE_V11_0_COMPLETION_REPORT.md
├── requirements.txt
├── webapp/          # Flask entry, routes, services, templates, static, tests
├── Run_PY/          # 14 production runners
├── src/             # production + traced hybrid packages
├── config/          # YAML engineering configuration
├── tests/           # index only; tests remain next to packages
├── data/
│   ├── Benchmark_Set_2/          # factory GN/benchmark path
│   ├── benchmarks/Benchmark_Set_2/
│   ├── baseline/                 # KPI extracts + E.1/E.2 JSON fixtures
│   ├── output/.gitkeep
│   └── web_runs/.gitkeep
├── docs/            # V11.0 inventories, V10 deployment reference copies
└── tools/           # fork/verify helpers (not production runtime)
```

There is no nested duplicate of Version1–Version10 inside Version11. Prompts, Vision contracts, and JSON schemas remain inside the packages that own them (`src/llm/`, C.5, P.253). Empty parallel `prompts/` / `schemas/` trees were not created.

---

## Copied runners (14)

Exactly the Version10 `PRODUCTION_STAGES` scripts:

1. `run_phase_vroot1_dynamic_pipeline_initialization.py`
2. `run_phase_r1_generalized_reinforcement_discovery.py`
3. `run_phase_t1_geometric_stirrup_evidence.py`
4. `run_phase_r2a_engineering_context.py`
5. `run_phase_r21b_semantic_interpreter.py`
6. `run_phase_r21c_engineering_fact_normalization.py`
7. `run_phase_r21d_evidence_hypothesis_engine.py`
8. `run_phase_l2_2_geometry_recovery.py`
9. `run_phase_r3_geometry_context_engine.py`
10. `run_phase_r31_engineering_relationship_engine.py`
11. `run_phase_r12a_geometry_accuracy.py`
12. `run_phase_r13_pipeline_integration.py`
13. `run_phase_w6_hybrid_production_authority.py`
14. `run_phase_vb1_production_output_completion.py`

---

## Copied source packages

### Deterministic engineering (MUST_COPY)

- `PhaseVROOT.1_dynamic_pipeline_initialization`
- `PhaseR.1_generalized_reinforcement_discovery`
- `PhaseT1_geometric_stirrup_evidence`
- `PhaseT16_entity_ownership`
- `PhaseR.2A_engineering_context`
- `PhaseR2.1B_engineering_semantic_interpreter`
- `PhaseR2.1C_engineering_fact_normalization`
- `PhaseR2.1D_evidence_hypothesis_engine`
- `PhaseL.2.2_geometry_recovery`
- `PhaseR3_geometry_context_engine`
- `PhaseR3.1_engineering_relationship_engine`
- `PhaseR1_2A_geometry_accuracy`
- `PhaseR1.3_pipeline_integration`
- `PhaseR1_2B_engineeringbar_consolidation`
- `PhaseR1_2C_engineering_intent_resolution`
- `PhaseR1_2D_reinforcement_detailing`
- `PhaseR1_3_reinforcement_piece_generation`
- `PhaseV9_spacer_rule` (M.2 spacer)
- `PhaseSI.1_stirrup_improvement`
- `PhaseVB.1_production_output_completion`
- `src/config`
- `src/llm`

### Hybrid / Vision (MUST_COPY — traced production path)

- `PhaseW5_production_hybrid_shadow`
- `PhaseW6_hybrid_production_authority`
- `PhaseW8_production_vision_evidence`
- `PhaseW10_hybrid_production_monitoring` (W.6 fail-safe `write_run_monitor`)
- `PhaseW11_hybrid_reliability`
- `PhaseP253_claude_vision_interpretation_pilot`
- `PhaseP2610C5_stratified_vision_semantic_benchmark` (C.5)
- `PhaseP2610C3_visual_completeness_claude_shadow` (C.3 `encode_png`)
- `PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark` (E.1 adapter)
- `PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark` (E.2 live_caller)
- `PhaseP2610D1_vision_semantic_contract_hybrid_foundation`
- `PhaseP2610D2_shadow_hybrid_semantic_resolver`
- `PhaseP2610D3_hybrid_engineering_binding_compatibility`
- `PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark`
- `PhaseP269_reinforcement_group_interpretation` (handoff extractor)
- `PhaseP26_vision_candidate_recovery` (**subset only**: `__init__.py`, `config.py`, `deterministic_comparator.py` for `role_family`)
- `PhaseP2610A_beam_region_crop_audit`
- `PhaseP2610B_adaptive_beam_detail_crop`
- `PhaseP2610B2_render_quality_directional_recovery`
- `PhaseP2610C1C2_evidence_inventory_candidate_selection`
- `PhaseM.1_engineering_vision_dataset`

Mixed packages were copied as packages because production modules live inside them. Experimental orchestrators inside those packages were **not** made import-time dependencies: ten `__init__.py` files were neutralized so `import package` does not load P.254 / B.1 research graphs.

---

## Copied configuration / resources

- `Version11/config/*.yaml` (25 files)
- `Version11/requirements.txt` plus `webapp/requirements.txt`
- `webapp/templates/index.html`, `webapp/static/css/app.css`, `webapp/static/js/app.js`
- W.19.1 hotfix note + env example copied to `docs/v10_deployment_reference/` as **reference only** (not live overlay)

---

## Copied tests

- `webapp/tests/test_w2_smoke.py` (identity assertions retargeted to Version11)
- `webapp/tests/test_w16_metadata_aggregation.py`
- `webapp/tests/test_w191_excel_metadata_binding.py`
- `webapp/tests/test_w6_hybrid_authority.py`
- related web tests: W.5, W.12, W.13, W.14
- `src/PhaseW6_hybrid_production_authority/unit_tests.py`
- `src/PhaseV9_spacer_rule/tests/` (W.18B)

Tests were not weakened.

---

## Copied benchmark / baseline data

Copied (fixtures, not generated bulk):

- `data/Benchmark_Set_2/` framing + reinforcement + general notes DXFs (also mirrored under `data/benchmarks/`)
- E.1/E.2 small JSON fixtures under `data/baseline/` (KPI values of `1` are stubs — do not use as accuracy)
- Extracted E.3 pooled KPIs: `data/baseline/P2610E3_pooled_kpis.json`

Estimator ground-truth Excel workbooks were **not** copied and were **not** modified. They remain in the existing repository locations used by P2.6.10-E.3.

---

## Excluded generated data

Not copied:

- `Version10/data/output/` bulk (including E.3 review trees, crops, logs)
- `Version10/data/web_runs/` contents
- webapp `uploads/`, `outputs/`, production `logs/*.log`
- Downloaded_Output, Office lock files, `.pytest_cache`, virtualenvs
- historical `pack_w*.py`, nginx/systemd live overlays

---

## Excluded experimental / historical code

Not copied:

- Version1–Version9 trees
- `Steel-Beam-Estimation/` packaging tree
- 86 Version10 `src/` packages with no proven production import (QA/VA/VTEST/VRUN, unused P.21–P.268 research, unused engineering_geometry/extractor stacks, L.2 non-web, etc.)
- unused `Run_PY` runners (91 non-web scripts)
- `PhaseP254_*`, `PhaseP2610B1_*`, `PhaseP2610E3_*` packages (E.3 **metrics JSON extract** is recorded; the experimental orchestrator package is not a V11 runtime dependency)
- remainder of `PhaseP26_vision_candidate_recovery` beyond the three proven files

Version8 was not copied, archived, moved, or referenced as a V11 runtime dependency.

---

## Known intentional differences from Version10

These are **not** accuracy changes:

1. `webapp/config.py`: `ENGINE_LABEL = "Version11"`, `ENGINE_DISPLAY = "Version11 development pipeline"`. `APP_RELEASE` remains `"W.19.1"`. `PRODUCTION_STAGES` unchanged.
2. `webapp/services/version10_adapter.py`: ENGINE_ROOT warning accepts `version10` **or** `version11` (filename kept).
3. `webapp/tests/test_w2_smoke.py`: assertions expect Version11 identity.
4. Ten mixed-package `__init__.py` files skip import-time research orchestrators.
5. P.26 copied as a **subset** (production `role_family` only).
6. W.10 monitoring package included (traced from W.6 orchestrator).
7. No live deployment files; empty output/log placeholders.

SHA256 of all other compared production files matches Version10 (634 files matched; 13 documented identity diffs; 0 true pipeline diffs).
