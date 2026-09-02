# Phase 5b — Version8 Archive Go/No-Go Decision

**Date:** 2026-09-02  
**Phase:** 5b — audit + decision only  
**Version8 moved/deleted/modified:** No  
**Production code changed:** No

---

## 1. Starting Baseline

- **Commit:** `768aab113c668fd937de5c7a5d983c382d7b00b9`  
  `fix: remove VROOT1 Version8 path dependency`
- **Branch:** `main` tracking `origin/main`
- **Phase 5a status:** COMPLETE. Live VROOT1 no longer writes under `Version8/data/output/` and no longer defaults CLI input to `Version8/data/Benchmark_Set_*`. Archive decision after 5a was still **CONDITIONAL_GO**.
- **Authority:** `PRODUCTION_TRUTH.md` (W.19.1, 14 stages, Hybrid W.6, VB.1 last).

Unrelated dirty/untracked files were present and left untouched.

---

## 2. Production Dependency Result

| Check | Result |
|-------|--------|
| Live Version8 **execution** | **NONE.** Web entry `wsgi.py` / `app.py` / `routes.py` / `estimation_service.py` / `version10_adapter.py`: no Version8 path. Adapter iterates only `PRODUCTION_STAGES` (14 Version10 `Run_PY` scripts), `cwd` = Version10, `STEEL_ENGINE_ROOT` = Version10. `V8_ROOT` in `config.py` is an alias for Version10. Web tests: zero Version8 matches. |
| Live Version8 **required read** | **NONE.** Uploaded GN + Version10 factory + Version10 `Benchmark_Set_2` fallback. R.2.1B dictionary loads `engine_root/src/PhaseR2.1A_*` (Version10 package), not the Version8 R.2.1A CLI. |
| Live Version8 **required write** | **NONE.** Phase 5a removed VROOT1 `_write_v7_copy()`. Canonical artefacts remain run-scoped (`STEEL_OUTPUT_ROOT`). |
| VROOT1 | **Closed.** Package has no `Version8` / `_V7` / `_write_v7_copy` strings. `_ENGINE = parents[2]` = Version10. `_default_input()` = Version10 `data/Benchmark_Set_2`. Web still passes the upload folder. |
| R2A / R21B | **Closed (Phase 3).** Both runners `importlib`-load Version10 packages with `engine_root=Version10`. R.2A / R.2.1B source packages contain no Version8 path. |
| Hybrid / Vision | **No Version8 runtime.** W.5 / W.6 / W.8, T.1 runner, P.253 `claude_vision_client`, C.5, D.2: no Version8 string. W.6 is stage 13 (`run_phase_w6_hybrid_production_authority.py`). |
| R.1.3 | **Version10-owned.** Runner `parent.parent` is Version10 (stale “Version8/” comments only). `importlib` loads Version10 `PhaseR1_3_*` / `PhaseR1_2B_*` / `PhaseR1_2C_*` / `PhaseR1_2D_*` / M.2. Comment in `pipeline_integration_manager.py` still says “engine_root: Version8”; resolved path is Version10. |
| VB.1 | **Version10-owned.** Last stage. Offline `_V6 = parents[2]` is Version10 (stale Version8 comment). Web runner passes RunContext. `IntegrationEngineValidator` may *inspect* `repo/Version8/data/output/phase_i` if present; missing files skip; absence does **not** fail Excel. Live BBS stirrup helper imports Version10 `PhaseSI.1` `StirrupImprover.compute_beam()` — in-memory; the SI.1 module’s unused `_V6 = repo/Version8` path constants are not a required read/write. |

**Live production Version8 dependency = CLOSED.**

`PRODUCTION_STAGES` == **14**. Order: VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → HYBRID (W.6) → VB1.

---

## 3. Remaining References

Grouped. Text occurrence ≠ production dependency.

| Area | Version8 references | Production? | Archive impact | Decision |
|------|---------------------|-------------|----------------|----------|
| Web entry + adapter + 14 stage scripts | None that load Version8. Stale comments on R21C–VB1 (`parent.parent  # Version8/`) | Yes (Version10) | None | Ignore comments |
| VROOT1 live package | None after Phase 5a | Yes | None | Closed |
| R2A / R21B live packages | “not Version8” comments only | Yes | None | Closed |
| Hybrid / Vision (W.5/W.6/W.8, C.5, P.253, D.2) | None | Yes | None | Closed |
| R.1.3 comments / `run_context.py` comments | Historical wording; paths resolve to Version10 via `__file__` / `STEEL_ENGINE_ROOT` | Yes (Version10) | None | Comment cleanup later |
| VB.1 `IntegrationEngineValidator` | Optional inspect of `Version8/.../phase_i` | Soft; not required | If moved: skip / false-positive only | Not a blocker |
| Version10 `PhaseSI.1` path constants | `_V6 = repo/Version8` at import; unused by live `StirrupImprover` | No required I/O | CLI SI.1 would break; live BBS would not | Not a live blocker |
| Non-web Run_PY that `importlib`-load `Version8/src` | R.2.1A, R.2.0, R.2.0.1, R.2B, R.1.4, SI.0, SI.1 | No | Those CLIs break if invoked | Accept breakage |
| Experimental QA / VA / VTEST / VRUN packages | Hardcoded `Version8` data/output / pipeline | No | Those CLIs break if invoked | Accept breakage |
| `vroot1_verify` | Hardcoded Version8 Benchmark_Set_2 + output | No | Verify CLI breaks | Accept breakage |
| YAML under `Version10/config/` | Historical `Version8/data/output/...` strings | No (live uses RunContext) | Offline YAML consumers break | Accept / later retarget |
| Deployment rollback docs + `nginx-v8-rollback.conf` | `:8000` Version8 recipe | Not current public service | Git archive does not by itself stop a **server** copy; deploying a tree without Version8 would | **Operational policy pending** |
| `gunicorn.w21.conf.py` / `LAUNCH_W21.txt` bind `:8000` | Version10 **local unpublished** template, not the 8.9.x unit | No | None | Not Version8 production |
| Live systemd `steel-beam-estimator-v10.service` + `nginx-v10.conf` + `gunicorn.w3.conf.py` | Bind **:8001**, WorkingDirectory Version10; comments mention old `:8000` | Yes (Version10) | None | Current production |
| Docs (Phase 2/3/4 reports, Version8 README, packaging 8.9.x) | Historical / stale | No | Operator confusion only | Docs only |

---

## 4. Non-Web CLI Policy

Inspected invocation, not filenames.

**None of the following are in `PRODUCTION_STAGES`.**  
**None are invoked by `Version10/webapp` (adapter loops only the 14 stage scripts).**  
**None are required by the current web estimation path (Excel / Hybrid / Vision / R.1.3 / VB.1).**

| Tool | Evidence | If Version8 moved | Classification |
|------|----------|-------------------|----------------|
| R.2.1A CLI | `importlib` loads `Version8/src/PhaseR2.1A_*`. Live R21B loads Version10’s copy of that package in-process. | CLI breaks | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| SI.0 / SI.1 CLIs | Runners sys.path-insert `Version8/src/PhaseSI.*` and write Version8 output. Web stirrups: T.1 + M.2 inside R.1.3; live BBS uses Version10 `StirrupImprover`. | CLI breaks | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| VA.2 | Runner comment `cd Version8`; Version10 VA.2 package hardcodes `_ROOT / "Version8"`. Experimental / not a current test gate. | Breaks if invoked | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| VTEST3 / VTEST3.2 | Same experimental pattern; packages write/read Version8 output. | Breaks if invoked | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| VRUN.1 | Re-executes historical L.2/SI/VB.1 against Version8 paths. | Breaks if invoked | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| QA.2B.2 / QA.3.0 report runners | Version8 DOCX/template paths. Not W.16 / W.19.1 / W.6 web tests. | Breaks if invoked | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| `vroot1_verify` | Hardcoded Version8 Benchmark_Set_2 + PhaseVROOT.1 output. Read-only audit, not a web stage. | Breaks if invoked | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| R.2.0 / R.2.0.1 / R.2B / R.1.4 CLIs | `PROJECT_ROOT / "Version8" / "src"` load. | Breaks if invoked | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |
| L.2 (not L.2.2) CLI | Not a web stage (web uses L.2.2). Usage says `cd Version8`; runner parent is Version10. | Historical CLI only | **NON-PRODUCTION — ACCEPTABLE TO BREAK** |

**Policy recorded this phase:** leftover Version8-hardcoded **non-web** CLIs are **not** retargeted here. Their breakage after a future archive/move is **accepted**.

**Requires retargeting before archive:** none for the live web path.

**HARD STOP:** not triggered — no remaining CLI is part of the production web path.

---

## 5. Lightsail :8000 Rollback

**Did not SSH. Did not change server config.**

**Current production (repository):**

- Unit `steel-beam-estimator-v10.service`: WorkingDirectory Version10, Gunicorn `wsgi:app`, bind **`127.0.0.1:8001`**, config `gunicorn.w3.conf.py` (`bind = 127.0.0.1:8001`).
- Sample `nginx-v10.conf`: upstream **:8001**, static aliases under Version10.
- `PRODUCTION_TRUTH.md`: public Nginx → `http://13.127.104.99/` via `:8001`.

**Rollback artefacts still in the repository (not live public config):**

- `nginx-v8-rollback.conf` — restore recipe, upstream **`127.0.0.1:8000`**, Version8-era static root.
- `ROLLBACK_W3.txt` — keep 8.9.x on `:8000`; engine `/opt/.../Version8`; **“Do not delete the old application directory or stop `steel-beam-estimator.service` until later explicit approval.”**
- W.3–W.12 deployment reports (last dated **2026-08-26**, W.12): `:8000` still described as the 8.9.x rollback; “Do not delete 8.9.x on `:8000`.”
- No later in-repo document states that `steel-beam-estimator.service` was stopped or that `:8000` was retired.

**Not Version8 production:** `gunicorn.w21.conf.py` / `LAUNCH_W21.txt` bind `:8000` for an **undeployed Version10** local template.

`:8001` being current public production is **not** sufficient evidence that `:8000` is retired.

**Classification:** **unknown / policy pending** (OPERATIONAL POLICY PENDING).  
Cannot declare the operational rollback path retired from repository evidence alone.

---

## 6. FINAL DECISION

**ARCHIVE_CONDITIONAL_GO**

Technical Version10 Hybrid production no longer executes, requires-reads, or requires-writes Version8. Phase 5a closed VROOT1 coupling. R2A/R21B remain Version10. Remaining Version8-dependent CLIs are non-production; breakage is accepted. **Lightsail `:8000` Version8 rollback is not confirmed retired**, and the owner has not explicitly accepted losing that capability. Per Phase 5b rules that operational gap blocks **ARCHIVE_GO**.

Version8 must **not** be moved or deleted in this phase.

---

## 7. Phase 5c Recommendation

Do **not** start the physical archive/move yet.

To convert this to **ARCHIVE_GO**, only these operator decisions are required:

1. **Lightsail `:8000`:** project owner/operator explicitly confirms the 8.9.x / Version8 loopback rollback is **retired**, **or** explicitly accepts losing that rollback if the Version8 tree is moved in git and later deployed.
2. After that confirmation, run a dedicated **controlled Version8 archive/move** (move, not delete). Keep the Lightsail **server** copy independent of the git move unless operators also retire it on the host.

No production-code retarget remains for the live 14-stage path.
