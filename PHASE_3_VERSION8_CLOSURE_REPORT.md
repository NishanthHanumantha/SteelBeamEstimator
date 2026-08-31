# Phase 3 — Version8 Runtime Dependency Closure

**Date:** 2026-08-31  
**Status:** COMPLETE  
**Decision:** GO — implemented

---

## 1. Phase Objective

Close the **live production runtime** dependency of web stages R.2A and R.2.1B on Version8 source.

This phase is **not** Version8 archival, deletion, or a Hybrid/Vision/R.1.3/VB.1 refactor.

---

## 2. Starting Git Baseline

```
f1febd2f
f1febd2fd1c72cd9e5c1800537af9075ff2eb24f
checkpoint: freeze Version10 Hybrid W.19.1 production baseline
```

That commit remains in history. It was not amended. It is the rollback baseline.

---

## 3. R2A Before

`Version10/Run_PY/run_phase_r2a_engineering_context.py` inserted `Version8/src` and `importlib`-loaded `PhaseR.2A_engineering_context` from Version8.

`resolve_run_context(..., engine_root=Version8)` → `PhaseR2AOrchestrator(v7_root=Version8)`.

GN discovery used Version8 `engineering_context_factory._discover_gn_path` (no `STEEL_RUN_ROOT`; fallback `Version8/data/Benchmark_Set_2/general_notes/`). The webapp GN pointer in Version10 `beam_registry.json` was ignored.

---

## 4. R2.1B Before

`Version10/Run_PY/run_phase_r21b_semantic_interpreter.py` inserted `Version8/src` + `Version8/` and loaded `PhaseR2.1B_engineering_semantic_interpreter` from Version8.

Annotations were already run-scoped (`STEEL_OUTPUT_ROOT`). The semantic dictionary was loaded from `engine_root` (Version8). Nested `_run_production()` bootstrapped R.1.3/VB.1 from Version8; exceptions were swallowed. Web stages later still ran Version10 R.1.3 and VB.1.

---

## 5. Version8 Dependencies Found

Live web (before Phase 3):

| Stage | Loaded package | `engine_root` |
|---|---|---|
| R2A | `Version8/src/PhaseR.2A_engineering_context` | Version8 |
| R21B | `Version8/src/PhaseR2.1B_engineering_semantic_interpreter` | Version8 |

Those subprocesses also imported `config.run_context` from Version8 because Version8 `src` was first on `sys.path`.

---

## 6. Version10 Equivalents

| Concern | Version10 candidate | Equivalence |
|---|---|---|
| R.2A package | `Version10/src/PhaseR.2A_engineering_context/` | Same 27 filenames; orchestrator/writer identical; factory + parsers include W.16 (`STEEL_RUN_ROOT`, table-title regions, provenance fields) |
| R.2.1B package | `Version10/src/PhaseR2.1B_*` | **Byte-identical** (15 files) |
| R.2.1A (dictionary, loaded by R.2.1B) | `Version10/src/PhaseR2.1A_*` | **Byte-identical** (13 files) |
| Dictionary YAML | `Version10/config/engineering_semantic_dictionary.yaml` | Same SHA as Version8 copy |

Full comparison: `PHASE_3_VERSION8_MIGRATION_ANALYSIS.md`.

---

## 7. GN Resolution Findings

Correct production contract (already implemented in the Version10 factory, previously unused by live R.2A):

1. Uploaded run GN: `STEEL_RUN_ROOT/general_notes/*.dxf` (**authoritative**)
2. Version10 `beam_registry.json` pointer
3. `Version10/data/Benchmark_Set_2/general_notes/`

The Version8 factory was **not** patched. The web runner now executes the Version10 factory.

The Benchmark_Set_2 GN DXF is byte-identical in Version8 and Version10. Explicit `create()` of that file produced the same Fe550 / cover 30 / M30 / Ld 50 / confidence 1.0 in both factories. Version10 adds provenance keys (`cover_source`, `dev_length_source`, `gn_dxf_path`) already consumed by W.19.1.

---

## 8. Behavioural Comparison

- R.2.1B: no source difference; ESO JSON contract for R.2.1C unchanged (`engineering_semantic_objects.json` under run-scoped output).
- R.2A: Version10 parsers locate TABLE 1/2 by title (W.16). Live Version8 previously could fall back to the Galera Benchmark GN instead of the uploaded project GN. Using Version10 + `STEEL_RUN_ROOT` is the **intended** production behaviour, already tested by W.16 (`test_gn_discovery_prefers_steel_run_root`, Galera/Inizio TABLE 2).
- Downstream R.2.1C/R.2.1D, L.2.2, R.3, R.3.1, R.1.2A, R.1.3, W.6, VB.1 were not modified.

---

## 9. Migration Decision

**GO**

Evidence: Version10 R.2A is the W.16 factory; R.2.1B is byte-identical; writers/contracts unchanged; Hybrid/R.1.3/VB.1 untouched; rollback remains `f1febd2f`.

---

## 10. Files Modified

Production code:

- `Version10/Run_PY/run_phase_r2a_engineering_context.py`
- `Version10/Run_PY/run_phase_r21b_semantic_interpreter.py`

Documentation:

- `PRODUCTION_TRUTH.md`
- `PRODUCTION_BOUNDARY_MANIFEST.md`
- `RUNNER_MANIFEST.md`
- `PHASE_3_VERSION8_MIGRATION_ANALYSIS.md`
- `PHASE_3_VERSION8_CLOSURE_REPORT.md`

---

## 11. Version8 Runtime Dependencies Removed

Live web path no longer:

- inserts `Version8/src` for R.2A or R.2.1B
- `importlib`-loads Version8 `PhaseR.2A_*` or `PhaseR2.1B_*`
- passes `engine_root=Version8` into those orchestrators

---

## 12. Validation

| Check | Result |
|---|---|
| `py_compile` both runners | PASS |
| Import R2A/R21B runners; module `__file__` under Version10; `config.run_context` from Version10 | PASS |
| GN discovery: `STEEL_RUN_ROOT` preferred; else Version10 Benchmark_Set_2 | PASS |
| `PRODUCTION_STAGES` count 14; T1 present; HYBRID = W.6; VB1 last | PASS |
| Live runners contain no `Version8/src` load | PASS |
| W.16 `test_w16_metadata_aggregation` | 16 OK |
| W.19.1 `test_w191_excel_metadata_binding` | 4 OK |
| W.2 smoke | 12 OK |
| W.6 Flask `test_w6_hybrid_authority` | 4 OK |
| W.6 `unit_tests.py` (no live Claude) | 17 OK |
| W.18B spacer pytest | 15 OK |
| Live Claude estimate | **not run** |

No dedicated in-tree R.2.1C/R.2.1D/R.1.3/VB.1 unit suites beyond the W.16 / W.19.1 / W.18B coverage above. R.2.1C still reads the same ESO path and fields; R.2.1B exporter is unchanged.

---

## 13. Remaining Version8 References

**Live R.2A / R.2.1B runtime:** none.

**Historical / non-web (left in place):**

- The `Version8/` tree itself
- Non-web `Version10/Run_PY` runners that still name Version8 (R.2.1A CLI, SI.0, QA, VROOT1 verify, etc.)
- VROOT1 CLI `_default_input()` Benchmark_Set folders (web always passes the upload folder)
- Deployment / rollback markdown for the old `:8000` 8.9.x app

---

## 14. Production Architecture After Migration

Unchanged 14-stage web pipeline:

VROOT1 → R1 → T1 → **R2A (Version10)** → **R21B (Version10)** → R21C → R21D → L.2.2 → R3 → R.3.1 → R.1.2A → R.1.3 → W.6 Hybrid → VB.1

Engineering authority unchanged: Vision determines WHAT exists; R.1.3/deterministic determines HOW; VB.1 remains steel / BBS / Excel.

GN for web runs now follows the Version10 factory (`STEEL_RUN_ROOT` first).

---

## 15. Rollback

```
git checkout f1febd2f -- Version10/Run_PY/run_phase_r2a_engineering_context.py Version10/Run_PY/run_phase_r21b_semantic_interpreter.py
```

Or reset the Phase 3 commit (not `f1febd2f`) if it is the tip and has not been depended on.

Do **not** amend or force-push `f1febd2f`.

---

## 16. Recommended Next Phase

Do **not** start automatically.

Candidate next work (separate explicit request):

- Inventory remaining **historical** Version8 references in non-web runners (not an archive of `Version8/`).
- Optional: retarget unused CLI runners that still load Version8 (R.2.1A, etc.) if they are ever needed from Version10.
- Version8 physical archive only after a dedicated archive phase with its own Go/No-Go.

---
