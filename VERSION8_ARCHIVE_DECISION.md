# Version8 Archive Decision

**Phase:** 4 — Version8 Archive Go / No-Go Audit  
**Date:** 2026-09-01  
**Git baseline:** `6afdc444480712ecedecb985d9e0436078ad6cad`  
**Audit only.** Version8 was not moved, deleted, or modified.

---

DECISION:  
**CONDITIONAL_GO**

LIVE PRODUCTION DEPENDENCY:  
**NO** for executing Version8 Python / reading Version8 GN as web input.  
**YES** for a live VROOT1 **write side-effect** into `Version8/data/output/...` (does not feed Excel; would recreate a Version8 stub if the tree were moved).

CURRENT VALIDATION DEPENDENCY:  
**NO** — current W.16 / W.19.1 / W.2 / W.6 / W.18B suites do not execute Version8.

CURRENT OPERATIONAL DEPENDENCY:  
**NO** for the live 14-stage web estimator.  
Non-web CLI runners that still hardcode `Version8/src` exist; they are not `PRODUCTION_STAGES`.

UNRESOLVED UNKNOWN:  
**NO** (blocking). Lightsail `:8000` 8.9.x rollback presence was not SSH-verified this phase; it is a **server** copy, not a Version10 web import.

ARCHIVE BLOCKERS:  
1. Live VROOT1 `EngineeringObjectInitializer._write_v7_copy()` writes JSON to `Version8/data/output/PhaseVROOT.1_dynamic_pipeline_initialization/` on every web estimate (`write_adapters=True`).  
2. Live VROOT1 `_default_input()` still lists `Version8/data/Benchmark_Set_*` when no input folder is passed (web always passes the upload folder; CLI without argv would fail after a move).  
3. Several **non-web** `Version10/Run_PY` scripts still `importlib`-load `Version8/src` (R.2.1A, R.2.0, SI.0/SI.1, VA.2, VTEST3, VRUN.1, QA report templates, etc.). Not live web; they would break if invoked after archival.  
4. Historical Lightsail rollback recipe (`ROLLBACK_W3.txt`, `nginx-v8-rollback.conf`) still names `/opt/.../Version8` on `:8000`. Independent of git archive.

PREREQUISITES:  
1. Retarget or remove VROOT1 `_write_v7_copy` so production does not write under `Version8/`. Prefer run-scoped `STEEL_OUTPUT_ROOT` or drop the copy.  
2. Retarget VROOT1 `_default_input()` to `Version10/data/Benchmark_Set_2` (or require an explicit folder).  
3. Explicitly accept breakage of leftover Version8-hardcoded **non-web** CLIs, **or** retarget those runners in a separate CLI pass before moving the tree.  
4. Treat Lightsail `:8000` Version8 as a **server rollback** decision; do not delete the server tree in the same git-archive action unless operators confirm rollback is retired.  
5. Do **not** change W.6, Vision, R.1.3, or VB.1 quantity/Excel logic for archival.

SAFE TO ARCHIVE:  
**AFTER PREREQUISITES**

RECOMMENDED NEXT PHASE:  
**Phase 5a — VROOT1 Version8 path retarget (minimal production-safe path fix)**  
then, only if that lands and is validated without Claude:  
**Phase 5b — Version8 tree archive (move, not delete), with non-web CLI policy documented.**

Do not start Phase 5 in this audit.
