# Phase 5a — VROOT1 Version8 Path Retarget

**Date:** 2026-09-02  
**Status:** COMPLETE  
**Archive decision:** still **CONDITIONAL_GO** (Phase 5b not started)

---

## 1. Starting Git Baseline

```
cf4aeae0
docs: add Phase 4 Version8 archive CONDITIONAL_GO audit
```

`HEAD` == `origin/main` before this phase.

---

## 2. Problem Addressed

Phase 4 blockers #1 and #2 only:

1. Live VROOT1 `_write_v7_copy()` wrote four JSON files under `Version8/data/output/PhaseVROOT.1_dynamic_pipeline_initialization/`.
2. VROOT1 `_default_input()` listed `Version8/data/Benchmark_Set_*` when no folder was passed.

Web already passes the upload folder, so (2) was CLI-only. (1) ran on every web VROOT1.

---

## 3. `_write_v7_copy()` Before

Always called from `EngineeringObjectInitializer.initialize()`, independent of `write_adapters`.

Wrote:

- `dynamic_beam_schedule.json`
- `dynamic_reinforcement_objects.json`
- `dynamic_engineering_objects.json`
- `dynamic_beam_geometry.json`

to **`repo/Version8/data/output/PhaseVROOT.1_dynamic_pipeline_initialization/`**.

Canonical VROOT1 export (8 artefacts including `beam_registry.json`) already goes to `STEEL_OUTPUT_ROOT` via `InitializationExport`.

L.2.2 optionally reads `dynamic_beam_geometry.json` from **run-scoped** `STEEL_OUTPUT_ROOT/PhaseVROOT.1_*`, not from Version8, and continues if missing. Excel / W.6 / R.1.3 do not read the Version8 copies.

---

## 4. `_write_v7_copy()` After

**Removed** (call + method + `_V7_DATA`). No retarget copy was added — the files were unused trace duplicates.

---

## 5. `_default_input()` Before

```
repo/Version8/data/Benchmark_Set_2
repo/Version8/data/Benchmark_Set_1
repo/Version8/data/input
else repo/Version8/data
```

---

## 6. `_default_input()` After

```
Version10/data/Benchmark_Set_2
Version10/data/Benchmark_Set_1   # not present; skipped
Version10/data/input             # not present; skipped
else Version10/data
```

Verified: Version10 `Benchmark_Set_2` exists with framing + reinforcement DXFs (and GN). Smoke `_default_input()` returned that folder.

Web behaviour unchanged: adapter still passes the staging/upload folder as argv.

---

## 7. Files Modified

- `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/engineering_object_initializer.py`
- `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/phase_vroot1_orchestrator.py`
- `Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/initialization_export.py` (comment only: Version8 → Version10 `src`)
- `Version10/Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py` (usage docstring)
- `PRODUCTION_TRUTH.md`
- `PHASE_5A_VROOT1_VERSION8_PATH_RETARGET_REPORT.md`

Version8 tree: **not** modified.

---

## 8. Production Behaviour Preserved

- 14 stages unchanged  
- Canonical 8 VROOT1 JSON artefacts unchanged  
- R2A / R21B still Version10  
- W.6 Hybrid / R.1.3 / VB.1 untouched  
- Discovery, beam IDs, schemas, quantity/Excel: untouched  

---

## 9. Validation

| Check | Result |
|---|---|
| `py_compile` modified VROOT1 files | PASS |
| Live VROOT1 package: no `Version8` / `_V7` / `_write_v7_copy` strings | PASS |
| `_default_input()` → Version10 `Benchmark_Set_2` | PASS |
| VROOT1 smoke on that fixture | PASS — 65 beams, 9/9 rules, 8/8 canonical exports |
| Version8 `PhaseVROOT.1_*` file snapshot before/after smoke | **unchanged** (12 files) |
| `PRODUCTION_STAGES` == 14, HYBRID=W.6, VB1 last | PASS |
| W.2 smoke + W.19.1 | 16 OK |
| Claude | not called |

Smoke used `write_adapters=False` so Version5 adapter paths were not touched. Version8 write was independent of that flag; its absence is what the snapshot proves.

---

## 10. Version8 References Remaining

Historical / non-web (expected):

- `Version10/Run_PY/run_phase_vroot1_verify.py` still points at Version8 Benchmark_Set_2 / output (not a web stage)
- YAML `pipeline_traceability.yaml`, `reinforcement_integrity_validation.yaml`
- Phase 4 audit docs
- Non-web SI/QA/VA CLIs (Phase 4 items #3/#4)

Live VROOT1 implementation: **none**.

---

## 11. Archive Impact

Live web VROOT1 no longer reads or writes Version8.

Archive decision remains **CONDITIONAL_GO**. Version8 must stay in the tree until Phase 5b.

---

## 12. Remaining Phase 5b Prerequisites

1. Non-web CLI policy: runners that still hardcode `Version8/src` (R.2.1A, SI.0/SI.1, VA.2, VTEST3, VRUN.1, QA reports, `vroot1_verify`) — accept breakage or retarget separately.  
2. Lightsail `:8000` Version8 rollback is a **server** decision; do not delete the server tree in the same git-archive action unless operators retire it.  
3. Do not change W.6 / Vision / R.1.3 / VB.1 for archival.

---

## 13. Go / No-Go for Phase 5b

**CONDITIONAL GO for Phase 5b** after an explicit archive request.

Phase 5a closed the live VROOT1 filesystem coupling. Phase 5b may **move** (not delete) Version8 only if operators accept leftover CLI breakage and the Lightsail rollback policy.

Do not start Phase 5b from this phase.
