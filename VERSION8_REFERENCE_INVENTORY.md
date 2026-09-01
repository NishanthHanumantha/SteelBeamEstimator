# Version8 Reference Inventory

**Phase:** 4 — audit only  
**Date:** 2026-09-01  
**Baseline:** `6afdc444`  
**Scope:** Meaningful references **outside** `Version8/` (the Version8 tree is the subject of archival, not a “reference”). Self-references inside Version8 are omitted.

Classification key (Step 4):

| Code | Meaning |
|---|---|
| A | LIVE_PRODUCTION |
| B | PRODUCTION_SUPPORT |
| C | CURRENT_VALIDATION |
| D | CURRENT_OPERATIONAL_TOOL |
| E | HISTORICAL_DOCUMENTATION |
| F | HISTORICAL_CODE |
| G | EXPERIMENTAL |
| H | GENERATED_OR_DATA_ARTIFACT |
| I | UNKNOWN_REVIEW_REQUIRED |

**Current?** = used by today’s Version10 Hybrid web path or current W.16–W.19.1 test gate.  
**Production?** = required for live estimate / Excel.  
**Blocker?** = blocks moving the entire Version8 directory **without** a prior path fix or an explicit “CLI may break” policy.

---

## 1. Live 14-stage web path

| Reference | File | Type | Classification | Current? | Production? | Blocker? | Confidence |
|---|---|---|---|---|---|---|---|
| `STEEL_ENGINE_ROOT` = Version10; asserts not mis-rooted | `Version10/webapp/services/version10_adapter.py` | py | A (negative: **no** Version8) | Yes | Yes | No | High |
| `V8_ROOT = ENGINE_ROOT` (alias **is Version10**) | `Version10/webapp/config.py` | py | F | Yes | Yes | No | High |
| 14 `PRODUCTION_STAGES` scripts under Version10 | `Version10/webapp/config.py` | py | A | Yes | Yes | No | High |
| Docstring “cd Version8”; engine = Version10 | `Version10/Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py` | py | E + live V10 load | Yes | Yes | No | High |
| `_V7 = repo/Version8`; `_default_input()` | `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/phase_vroot1_orchestrator.py` | py | A (CLI default) / unused on web | Web: no argv fallback | Web: no | **Yes** for CLI-after-move | High |
| `_write_v7_copy` → `Version8/data/output/PhaseVROOT.1_*` | `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/engineering_object_initializer.py` | py | **A write side-effect** | Yes | Write only | **Yes** | High |
| Comment “cwd Version8”; `_SRC` = Version10 `src` | `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/initialization_export.py` | py | E | No | No | No | High |
| “not Version8” (Phase 3) | `Version10/Run_PY/run_phase_r2a_engineering_context.py` | py | A (V10 load) | Yes | Yes | No | High |
| “not Version8” (Phase 3) | `Version10/Run_PY/run_phase_r21b_semantic_interpreter.py` | py | A (V10 load) | Yes | Yes | No | High |
| Comment `python Version8/Run_PY/...`; `parent.parent` = Version10 | `run_phase_r21c_*`, `r21d_*`, `l2_2_*`, `r3_*`, `r31_*`, `r12a_*`, `r13_*`, `vb1_*` | py | E | Yes (V10) | Yes | No | High |
| Comment “loads Version9 src (not Version8)” | `Version10/Run_PY/run_phase_r1_generalized_reinforcement_discovery.py` | py | E | Yes (V10) | Yes | No | High |
| Comment engine_root Version8 | `Version10/src/PhaseR1.3_pipeline_integration/pipeline_integration_manager.py` | py | E | No | No | No | High |
| Comment “Version8 root for YAML” | `Version10/src/PhaseR.1_generalized_reinforcement_discovery/phase_r1_orchestrator.py` | py | E | No | No | No | High |
| Header “Version8 / D.5.3” | `Version10/src/PhaseL.2.2_geometry_recovery/geometry_registry_engine.py` | py | E | No | No | No | High |
| Comment VROOT1 wiring | `Version10/src/PhaseL.2.2_geometry_recovery/geometry_registry.py` | py | E | No | No | No | High |
| Comments “Version8/” for `parents[2]` = Version10 | `Version10/src/config/run_context.py` | py | E | Yes (V10 paths) | Yes | No | High |
| Offline defaults comment Version8; `_V6` = Version10 | `Version10/src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py` | py | E | Yes | Yes | No | High |
| Inspect `Version8/data/output/phase_i` if present | `Version10/src/PhaseVB.1_production_output_completion/integration_engine_validator.py` | py | F (optional read) | Soft | No required | No | High |
| Docstring Version8 snapshot; loads `cwd/data/output` | `Version10/src/llm/context/context_collector.py` | py | F | No (not W.6) | No | No | High |
| Docstring Version8; `parents[1]` = Version10 | `Version10/Run_PY/_bootstrap.py` | py | F | No (not imported by 14 stages) | No | No | High |

**T1 / W.6 runners and Hybrid/Vision packages:** no Version8 string in `run_phase_t1_*`, `run_phase_w6_*`, `PhaseW5_*`, `PhaseW6_*`, `PhaseW8_*`.

---

## 2. Non-web CLI that still load Version8 source or data

| Reference | File | Type | Classification | Current? | Production? | Blocker? | Confidence |
|---|---|---|---|---|---|---|---|
| `Version8_SRC = PROJECT_ROOT/Version8/src` | `Version10/Run_PY/run_phase_r21a_semantic_dictionary.py` | py | F | No | No | Conditional (if CLI kept) | High |
| Same pattern | `run_phase_r20_mtext_recovery.py` | py | F | No | No | Conditional | High |
| Same pattern | `run_phase_r201_notation_inventory.py` | py | F | No | No | Conditional | High |
| `VERSION7_ROOT = Version8` | `run_phase_r2b_engineering_context_consumption.py` | py | F | No | No | Conditional | High |
| Same | `run_phase_r14_integrity_validation.py` | py | F | No | No | Conditional | High |
| `Version8/src/PhaseSI.*` | `run_phase_si0_stirrup_recovery.py` | py | F | No | No | Conditional | High |
| Same | `run_phase_si1_stirrup_improvement.py` | py | F | No | No | Conditional | High |
| `Version8/data/output` + Benchmark_Set_2 | `run_phase_vroot1_verify.py` | py | F | No | No | Conditional | High |
| `cd Version8` / `_V7 = Version8` | `run_phase_va2_benchmark_set2_validation.py` | py | G | No | No | Conditional | High |
| `cd Version8` | `run_phase_vtest3_benchmark_set3_validation.py` | py | G | No | No | Conditional | High |
| `_ROOT` comment Version8 | `run_phase_vrun1_pipeline_reexecution.py` | py | G | No | No | Conditional | High |
| `cd Version8` | `run_phase_l2_engineering_reinforcement_interpretation.py` | py | F | No | No | Conditional | High |
| Docstring Version8 path | `run_phase_r11a_*`, `r11b_*`, `r12b_*`, `r12c_*` | py | E | No | No | No | Medium |
| Version8 template path | `run_phase_qa2b2_accuracy_report.py` | py | G | No | No | Conditional | High |
| Version8 path | `run_phase_qa30_overall_accuracy_report.py` | py | G | No | No | Conditional | High |
| `_V6 = .../Version8` data/output | `Version10/src/PhaseSI.0_stirrup_recovery/phase_si0_orchestrator.py` | py | F | No | No | Conditional | High |
| `_V6 = .../Version8` | `Version10/src/PhaseSI.1_stirrup_improvement/phase_si1_orchestrator.py` | py | F | No | No | Conditional | High |
| `_V7 = repo/Version8` | `PhaseR1_1A_annotation_coverage/phase_r11a_orchestrator.py` | py | F | No | No | Conditional | High |
| Same | `PhaseR1_1B_production_integration/production_integration_orchestrator.py` | py | F | No | No | Conditional | High |
| Report string Version8 output | `PhaseR1_1B_production_integration/report_exporter.py` | py | E | No | No | No | High |
| Resolve paths starting `Version8/` | `PhaseR1.4_integrity_validation/pipeline_data_loader.py` | py | F | No | No | Conditional | High |
| Look under Version8/data | `PhaseR1_4_production_accuracy_benchmark/regression_engine.py` | py | G | No | No | Conditional | High |

---

## 3. Experimental / QA packages (Version10/src)

All **G EXPERIMENTAL** unless noted. Current? No. Production? No. Blocker? Conditional if those CLIs must keep working.

| File | Notes |
|---|---|
| `PhaseVA.2_benchmark_set2_validation/*.py` (orchestrator, loader, runner, export, comparator, reporter, statistics, workbook + engineering validators) | Hardcoded `_ROOT / "Version8"` |
| `PhaseVTEST3_benchmark_set3_validation/*.py` | Same |
| `PhaseVTEST3_2_estimator_comparison_engine/*.py` | Same |
| `PhaseVRUN.1_pipeline_reexecution/*.py` | `WORKSPACE / "Version8"`; `execution_export.py` has an absolute Version8 output path |
| `PhaseQA.2_multi_drawing_benchmark/pipeline_runner.py` | Docstring “Version8 production pipeline” |
| `PhaseQA2B0_pipeline_integration/pipeline_paths.py` | **Avoids** Version8 (`"Version8/"` listed as legacy to skip) — F/G, not a load |
| `PhaseQA2B0_pipeline_integration/pipeline_validator.py` | Mentions `Version8/src` as old crop path |
| `PhaseQA2B0_pipeline_integration/PipelineArchitecture.md` | Docs |
| `PhaseVTEST3_benchmark_set3_validation/__init__.py` | “complete Version8 production” |

---

## 4. Production YAML (historical paths)

| Reference | File | Type | Classification | Current? | Production? | Blocker? | Confidence |
|---|---|---|---|---|---|---|---|
| Comment “relative to Version8 root” | `Version10/config/dynamic_pipeline_initialization.yaml` | yaml | E | No (VROOT1 uses folder arg) | No | No | High |
| `Version8/data/output/...` | `pipeline_traceability.yaml` | yaml | G | No | No | No | High |
| Same | `production_output_completion.yaml` | yaml | F | No (VB.1 uses RunContext) | No | No | High |
| Same | `reinforcement_integrity_validation.yaml` | yaml | F | No | No | No | High |
| Same | `engineering_accuracy_validation.yaml` | yaml | G | No | No | No | High |
| Same | `end_to_end_validation.yaml` | yaml | G | No | No | No | High |
| Same | `engineering_error_diagnostics.yaml` | yaml | G | No | No | No | High |

---

## 5. Deployment / rollback

| Reference | File | Type | Classification | Current? | Production? | Blocker? | Confidence |
|---|---|---|---|---|---|---|---|
| Old engine `/opt/.../Version8` | `Version10/webapp/deployment/ROLLBACK_W3.txt` | txt | B | Recipe | No (public is V10 `:8001`) | Server policy | High |
| Upstream comment Version8 `:8000` | `nginx-v8-rollback.conf` | conf | B | Recipe | No | Server policy | High |
| Do not point STEEL_ENGINE_ROOT at Version8 | `LAUNCH_W21.txt` | txt | B | Advisory | No | No | High |
| Isolation check `"Version8" not in run_root` | `smoke_w3.py` | py | C (historical W.3 smoke) | No | No | No | High |
| W.3/W.7 go-live narratives | `PHASE_W3_*.md`, `PHASE_W7_*.md` | md | E | No | No | No | High |
| Pre-Phase-3 GN note | `PHASE_W19_1_EXCEL_PROJECT_METADATA_BINDING_HOTFIX.md` | md | E (stale vs Phase 3) | No | No | No | High |

Live systemd / nginx-v10 / env.example: **no** Version8 path.

---

## 6. Current production-truth documents (root)

| Reference | File | Type | Classification | Current? | Production? | Blocker? | Confidence |
|---|---|---|---|---|---|---|---|
| Gate CLOSED; do not move Version8 until asked | `PRODUCTION_TRUTH.md` | md | E / policy | Yes | No | No | High |
| Live R2A/R21B Version10; remaining historical V8 | `PRODUCTION_BOUNDARY_MANIFEST.md` | md | E | Yes | No | No | High |
| Runner rows (R2A/R21B = Version10) | `RUNNER_MANIFEST.md` | md | E | Yes | No | No | High |
| **Stale:** live R2A still executes Version8 | `PHASE_2_CLEANUP_REPORT.md` | md | E **conflict** | No | No | No (docs only) | High |
| Phase 3 analysis / closure | `PHASE_3_VERSION8_*.md` | md | E | Yes | No | No | High |
| Phase 1 leftover (untracked) | `REPOSITORY_FORENSICS_REPORT.md` | md | E | No | No | No | High |

---

## 7. Other trees / packaging docs

| Reference | File | Type | Classification | Current? | Production? | Blocker? | Confidence |
|---|---|---|---|---|---|---|---|
| 8.9.x architecture | `Steel-Beam-Estimation/docs/*`, `README.md` | md | E | No | No | No | High |
| Version9 freeze / pipeline mentions | `Version9/README.md`, `PIPELINE.md`, engineering README | md | E | No | No | No | High |
| Version7 freeze | `Version7/VERSION_FREEZE.md`, `README.md` | md | E | No | No | No | High |
| Cursor knowledge | `Claude/SteelBeamEstimator_V9_Context_Knowledge.md` | md | E | No | No | No | Medium |
| Engineering specs README | `Version10/src/engineering_specifications/README.md` | md | E | No | No | No | High |

Generated QA markdown **inside Version8/data/web_runs** is H; not listed.

---

## 8. Counts

| Bucket | Files (approx.) |
|---|---|
| Live execute of Version8 Python | **0** |
| Live required Version8 read | **0** |
| Live Version8 **write** mechanisms | **1** (`_write_v7_copy`) |
| Live CLI default to Version8 data | **1** (`_default_input`) |
| Non-web CLI / src packages that still path to Version8 | **~45** files |
| YAML historical | **7** |
| Deployment / rollback | **9** |
| Root + packaging docs | **~25** |
| **UNKNOWN_REVIEW_REQUIRED (I)** | **0** blocking |

**TOTAL MEANINGFUL VERSION8 REFERENCES (unique files outside Version8/ with a Version8 token, from this audit):** **~90**

Do not treat comment-only `parent.parent  # Version8/` live runners as production Version8 loads.

---

## 9. Interpretation notes

1. Text occurrence ≠ production dependency.  
2. `PHASE_2_CLEANUP_REPORT.md` is **wrong** after Phase 3; `PRODUCTION_TRUTH.md` is authoritative.  
3. Lightsail `:8000` was not probed; rollback files are classified B without asserting the process is still running.  
4. No CI config found that would fail if Version8 moved.
