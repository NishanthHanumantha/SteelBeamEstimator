# Phase 2 — Production Boundary & Safe Cleanup Report

**Date:** 2026-08-31  
**Phase 1 baseline:** `REPOSITORY_FORENSICS_REPORT.md`  
**Git HEAD at start:** `8b17a2a5` (W.19.1 docs)  
**Checkpoint commit:** **not created** — working tree was dirty with unrelated user files. Manual checkpoint is required before later archive work.

---

## 1. Baseline

Current production: **Version10 Hybrid**, release **W.19.1**, Lightsail Gunicorn `wsgi:app` at `127.0.0.1:8001`, 1 worker.

Entry: `Version10/webapp/wsgi.py` → Flask → `/api/estimate` → `estimation_service` → `version10_adapter` → 14 subprocess stages → W.6 Hybrid → VB.1 steel / BBS / Excel.

Authority: Vision determines **what** reinforcement exists; deterministic engine (R.1.3 → VB.1) determines **how** it is engineered and quantified.

---

## 2. Production Boundary

Protected and documented in:

- `PRODUCTION_TRUTH.md` — Cursor first-read
- `PRODUCTION_BOUNDARY_MANIFEST.md` — entry points, 14 stages, hybrid, engineering, resources, tests
- `PRODUCTION_MODULE_INDEX.md` — per-file mixed-package classification
- `RUNNER_MANIFEST.md` — 105 runners

No mixed Vision/benchmark package was split or moved.

---

## 3. Production Stage Manifest

Exact `PRODUCTION_STAGES` order (14):

VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → **HYBRID (W.6)** → **VB1**

Details (runners, packages, outputs, next stage): `PRODUCTION_BOUNDARY_MANIFEST.md` §2.

Runtime caveat: web R.2A and R.2.1B **execute Version8 `src`**, not the Version10 copies of those packages.

---

## 4. Hybrid Production Boundary

W.6 orchestrator → W.8 evidence (P.2610A cropper/title_localizer, P.2610B envelope/completeness, P.2610B2 `quality.py`, P.2610C1C2 selector/inventory, M.1 `dxf_renderer.py`) → W.5 adapter → E.2 `live_caller` → C.5 `claude_call` / `vision_prompt` / `vision_contract` → P.253 `claude_vision_client` → D.2 `resolve_hybrid_beam` → W.6 `handoff.py`.

E.1 `hybrid_runner_adapter.py` is production-imported and **also imports D.3 / D.4 / P.269 at module load**. Those packages must not be archived until that import surface is narrowed.

---

## 5. Deterministic Engineering Boundary

R.1, T.1, R.2.1C/D, L.2.2, R.3, R.3.1, R.1.2A, R.1.3 (dynamic load of piece generation, R.1.2B, M.2 `PhaseV9_spacer_rule`) → VB.1 steel / BBS / Excel.

R.2A / R.2.1B **runtime source is Version8**. Version10 `PhaseR.2A_*` exists (and W.16 tests it) but is **not** what the web R.2A runner loads.

---

## 6. Version8 Dependency Result

**BLOCKED**

Evidence:

1. `Version10/Run_PY/run_phase_r2a_engineering_context.py` inserts `Version8/src` and `importlib`-loads `PhaseR.2A_engineering_context`.
2. Orchestrator is constructed with `engine_root` / `v7_root` = Version8.
3. Version8 `engineering_context_factory._discover_gn_path` has **no** `STEEL_RUN_ROOT` check. Order: Version8 `beam_registry.json` → **`Version8/data/Benchmark_Set_2/general_notes/`**.
4. Web `write_r2a_gn_pointer` writes **Version10** `src/PhaseVROOT.1_.../beam_registry.json`, which Version8 factory does not read.
5. The same GN DXF also exists under `Version10/data/Benchmark_Set_2/general_notes/`; production fallback still uses the Version8 copy.
6. `run_phase_r21b_semantic_interpreter.py` likewise executes **Version8** `PhaseR2.1B_*`.
7. VROOT1 `_default_input()` still lists Version8 Benchmark_Set folders (CLI default; web passes the upload folder).

R.2A logic was **not** modified in this phase.

**VERSION8 ARCHIVE STATUS = BLOCKED.** Version9 remains REVIEW_REQUIRED.

---

## 7. Runner Classification

105 total (`Version10/Run_PY/run_phase_*.py`):

| Class | Count |
|---|---|
| Web production stages | **14** |
| Mixed-package CLIs (do not archive package) | 14 |
| Nested piece / consolidator / verify CLIs | 3 |
| QA / VA / VTEST / VRUN | 18 |
| Other experimental `run_phase_p*` | 37 |
| Extra engineering `run_phase_r*` | 15 |
| SI / L.2 (not L.2.2) / track1 | 4 |

Remaining **91** were **not** archived.

---

## 8. Files Moved

**NONE**

---

## 9. Files Deleted

| Path | Reason |
|---|---|
| `out_local_crop.txt` | Generated debug dump (Phase 1 SAFE_TO_ARCHIVE) |
| `out_local_crop2.txt` | same |
| `out_local_crop3.txt` | same |
| `out_local_crop4.txt` | same |
| `out_local_crop5.txt` | same |
| `out_local_crop6.txt` | same |
| `out_local_crop7.txt` | same |
| `Test_Input/2nd Set Drawings-Galera_GF/Estimator_Output/~$EstimatorOutput_GF Beam BBS.xlsx` | Office lock |
| `Version1/docs/~$acerBar_Computation.docx` | Office lock |
| `Version10/Downloaded_Output/~$W16_Galera_GF_Estimation_Output.xlsx` | Office lock |

Temporary Phase 2 generator scripts (created then removed, never committed): `_phase2_generate_manifests.py`, `_phase2_write_runner_manifest.py`.

No source packages, runners, or Version trees were deleted.

---

## 10. Files Modified

| Path | Change |
|---|---|
| `README.md` | Production description Version6 → Version10 Hybrid; Version6 table row archived |
| `Version10/PIPELINE.md` | Actual 14-stage pipeline including T.1 and W.6 / HYBRID |
| `Version10/webapp/wsgi.py` | Header/comment only: live `:8001`, remove “NOT YET DEPLOYED”; **no runtime change** |

**New (documentation only):**

- `PRODUCTION_TRUTH.md`
- `PRODUCTION_BOUNDARY_MANIFEST.md`
- `PRODUCTION_MODULE_INDEX.md`
- `RUNNER_MANIFEST.md`
- `PHASE_2_CLEANUP_REPORT.md` (this file)

Unrelated dirty files (architecture notes, Word docs, xlsx downloads, fixtures, `REPOSITORY_FORENSICS_REPORT.md`) were **not** overwritten and were **not** committed.

---

## 11. Documentation Corrections

**README.md:** States Version10 Hybrid W.19.1 is current production. Version6 is a frozen historical engine; its quick-start commands are labeled archive.

**PIPELINE.md:** Lists all 14 stages including T.1 and W.6 / HYBRID. 8.9.5 is labeled historical packaging, not current architecture.

**wsgi.py:** Docstring now matches live Gunicorn (`gunicorn.w3.conf.py`, `127.0.0.1:8001`, workers=1, W.19.1). Imports and `app` binding unchanged.

---

## 12. Validation

| Check | Result |
|---|---|
| `ast.parse` `wsgi.py` | PASS |
| `PRODUCTION_STAGES` count == 14 | PASS |
| T.1 present; HYBRID is W.6 runner; VB1 last | PASS |
| Version8 R.2A factory still has no `STEEL_RUN_ROOT` | PASS (unchanged) |
| R.2A runner still loads Version8 src | PASS (unchanged) |
| `test_w191_excel_metadata_binding` | PASS |
| `test_w6_hybrid_authority` (stub; stages include HYBRID+VB1) | PASS |
| `test_w16_metadata_aggregation` | PASS |
| `test_w2_smoke` stage-id / T.1 assertion | PASS |
| W.18B spacer pytest | PASS (15) |
| Live Claude production estimate | **not run** (API credits) |

No production imports were changed. No Hybrid / Vision / R.1.3 / VB.1 logic was changed.

---

## 13. Remaining Cleanup Candidates

**Do not execute in this phase.**

- Version1–Version7 trees: LIKELY_SAFE_TO_ARCHIVE for web runtime; still do not move until a dedicated archive PR.
- Version8 / Version9: blocked / review-required.
- Mixed P.253 / C.5 / E.2 / W.8 dependency packages: file-level index exists; physical split is a later phase.
- 91 non-web `Run_PY` runners: classified; none archived.
- ~415 unknown Version10 `src` files (Phase 1): still UNKNOWN.
- Generated `Version10/data/output` bulk, Downloaded_Output xlsx, V10_Report_Docs.
- Historical `pack_w3.py`–`pack_w19.py` overlay recipes (keep `pack_w191.py`).
- Stale runner comments that say `cd Version8` while `__file__` is Version10 (documentation-only later).

---

## 14. Known Risks

| Risk | Status |
|---|---|
| Version8 R.2A GN fallback / ignored Version10 GN pointer | **BLOCKED** — production can still read Benchmark_Set_2 GN (Inizio Fe550 vs Fe415 class of issue) |
| Version8 R.2.1B source on web path | Additional archive blocker |
| Version10 R.2A factory *does* honor `STEEL_RUN_ROOT` (W.16 tests it) while production runner does not use that factory | Cursor confusion: tests ≠ live R.2A |
| Version9 tree + R.1 “Version9” docstring | REVIEW_REQUIRED |
| Mixed benchmark packages | Production files co-located with experimental orchestrators |
| Unknown Version10 src (~415 files Phase 1) | UNKNOWN |
| Experimental Run_PY (91) | REVIEW_REQUIRED; easy to edit the wrong CLI |
| systemd `HYBRID_MODE=off` vs overlay `production` | Ops confusion; not changed |
| Dirty working tree | No git checkpoint |

---

## 15. Recommended Phase 3

**Do not implement here.** Suggested next controlled step:

1. Manual git checkpoint of current Hybrid baseline (excluding unrelated user artefacts).  
2. **Close the Version8 gate** with an explicit, requested production change: point web R.2A (and R.2.1B) at Version10 `src` *or* teach the *executed* factory to prefer `STEEL_RUN_ROOT/general_notes` and the Version10 GN pointer. Validate with Galera + Inizio GN artefacts, **not** a full paid Vision run unless needed.  
3. Only after that gate closes: archive Version8 from the **runtime** graph, then consider moving Version1–Version7 behind an `archive/` prefix.  
4. Keep mixed Vision packages intact until a dedicated import-safe split phase.

STOP after Phase 2.
