# Version8 Archive Audit

**Phase:** 4 — audit only  
**Date:** 2026-09-01  
**Decision:** CONDITIONAL_GO (see `VERSION8_ARCHIVE_DECISION.md`)

---

## 1. Starting Git Baseline

```
6afdc444
6afdc444480712ecedecb985d9e0436078ad6cad
feat: close Version8 runtime dependency for R2A and R2.1B
```

Parent checkpoint: `f1febd2f`.

Verified 2026-09-01:

- `HEAD` == `origin/main` == `6afdc444`
- Branch: `main` tracking `origin/main`
- Unrelated dirty files present and **untouched** (docs, xlsx, PNGs, fixtures)
- No stash, reset, or production commit in this phase

---

## 2. Current Production Architecture

Version10 Hybrid **W.19.1**.

Entry: `Version10/webapp/wsgi.py` → Flask → `/api/estimate` → `estimation_service` → `version10_adapter`.

Adapter (live):

- `cwd` = Version10
- `STEEL_ENGINE_ROOT` = Version10 (`config.ENGINE_ROOT`; asserts path looks like Version10)
- `STEEL_RUN_ROOT` = `data/web_runs/<run_id>`
- `STEEL_OUTPUT_ROOT` = `<run>/data/output`
- `V8_ROOT` in `config.py` is an **alias for Version10**, not the Version8 directory

14 `PRODUCTION_STAGES`: VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → HYBRID (W.6) → VB1.

Authority: Vision = WHAT; R.1.3/deterministic = HOW; VB.1 = steel / BBS / Excel.

---

## 3. Live Runtime Dependency Check

### 3.1 Web Python execution of Version8

**NONE.**

| Stage | Runner | Code loaded | `engine_root` |
|---|---|---|---|
| VROOT1 | `run_phase_vroot1_...py` | Version10 `PhaseVROOT.1_*` | Version10 (`_ENGINE = runner.parent`) |
| R1 | `run_phase_r1_...py` | Version10 `PhaseR.1_*` | Version10 |
| T1 | `run_phase_t1_...py` | Version10 T.1 | Version10 |
| R2A | `run_phase_r2a_...py` | Version10 `PhaseR.2A_*` (Phase 3) | Version10 |
| R21B | `run_phase_r21b_...py` | Version10 `PhaseR2.1B_*` (Phase 3) | Version10 |
| R21C–R31, R12A, R13, VB1 | `Path(__file__).parent.parent` | Version10 `src/...` | Version10 (comments still say “Version8/”) |
| HYBRID | `run_phase_w6_...py` | Version10 W.6 | Version10 |

`version10_adapter.py`, `estimation_service.py`, `routes.py`, `wsgi.py`: **no** Version8 path.

Web tests (`Version10/webapp/tests/`): **zero** Version8 string matches.

### 3.2 Live side-effects that still *name* Version8

**VROOT1 `EngineeringObjectInitializer`:**

- Called on every web VROOT1 run with `write_adapters=True`.
- `_write_v7_copy()` always writes four JSON files to  
  `SteelBeamEstimator/Version8/data/output/PhaseVROOT.1_dynamic_pipeline_initialization/`.
- Downstream Excel does **not** read those copies. Canonical artefacts go to `STEEL_OUTPUT_ROOT`.
- If `Version8/` were moved, `mkdir(parents=True)` would **recreate** a stub `Version8/data/output/...` on the next estimate.

**VROOT1 `_default_input()`:**

- Candidates are `Version8/data/Benchmark_Set_2`, `Benchmark_Set_1`, `data/input`.
- Web runner passes `input_folder=ctx.input_root` whenever argv is present (adapter always passes staging). **Web does not use this fallback.**
- Offline CLI with no argv still would.

**VB.1 `IntegrationEngineValidator`:**

- Inspects `repo/Version8/data/output/phase_i` if present.
- Missing files: skip / false-positive only. Does **not** fail the workbook when `phase_i` is absent.
- Not a required Version8 **read** for current web Excel.

**LIVE WEB VERSION8 DEPENDENCY (execute / required read) = NONE**  
**LIVE WEB VERSION8 PATH COUPLING (optional write / CLI default) = YES**

---

## 4. Production Configuration Check

| Asset | Version8? |
|---|---|
| `Version10/webapp/config.py` `PRODUCTION_STAGES` | 14 stages; scripts under Version10 `Run_PY/` |
| `STEEL_ENGINE_ROOT` | Set to Version10 by adapter |
| systemd `steel-beam-estimator-v10.service` | WorkingDirectory Version10; bind `:8001`; no Version8 |
| `steel-beam-estimator-v10.env.example` | Hybrid/Claude only; no Version8 |
| `nginx-v10.conf` | `:8001` Version10 |
| `nginx-v8-rollback.conf` | **Historical** `:8000` Version8 upstream |
| `ROLLBACK_W3.txt` | Documents old engine path Version8 |
| `LAUNCH_W21.txt` | Instructs **not** to point `STEEL_ENGINE_ROOT` at Version8 |
| Docker | None found |
| CI (`.github`) | None found |
| YAML under `Version10/config/` | Several still **string-path** to `Version8/data/output/...` (QA / integrity / E2E historical). Live VB.1 / VROOT1 web path uses `RunContext`, not those YAML output roots. |

Historical deployment examples are allowed and are **not** the live Gunicorn unit.

---

## 5. Production Data / Resource Check

| Resource | Used by live web? |
|---|---|
| Uploaded `STEEL_RUN_ROOT/general_notes/*.dxf` | **Yes** — Version10 R.2A factory (Phase 3) |
| Version10 `beam_registry.json` GN pointer | Fallback in Version10 factory |
| `Version10/data/Benchmark_Set_2/general_notes/` | Offline factory fallback |
| `Version8/data/Benchmark_Set_2/general_notes/` | **Not** used by live R.2A after Phase 3 |
| `Version8/data/web_runs/**` | Historical QA artefacts |
| `Version8/src/**` | **Not** imported by live 14 runners |
| `Version8/prompts`, `schemas`, `config` | **Not** on live web path |
| VROOT1 copy into `Version8/data/output/PhaseVROOT.1_*` | **Written** by live VROOT1; not consumed by VB.1 Excel |

Version8 GN vs Version10 GN: Phase 3 established the Benchmark_Set_2 GN DXF is byte-identical. Current authority is Version10 factory + run upload.

---

## 6. Current Test / Validation Check

No repository CI.

| Suite | Version8 execute? | Current release gate? | Archive blocker? |
|---|---|---|---|
| `webapp/tests/test_w16_*.py` | No — Version10 factory | Yes (W.16) | No |
| `test_w191_*.py` | No | Yes | No |
| `test_w2_smoke.py` | Stub pipeline; no Version8 | Yes | No |
| `test_w6_*.py` + W.6 `unit_tests.py` | No | Yes | No |
| W.18B spacer pytest | Version10 M.2 / VB.1 | Yes | No |
| Phase VA.2 / VTEST3 / VRUN.1 / QA.2* | Would use Version8 paths if run | **No** — experimental / historical CLI | Only if those CLIs were declared required (they are not) |
| YAML `end_to_end_validation.yaml` etc. | Version8 workbook paths | Not wired to web tests | No |

**CURRENT_VALIDATION required to execute Version8: NO.**

---

## 7. Operational CLI Check

`Version10/Run_PY` contains 105 runners; **14** are web-invoked.

Runners that still **construct `PROJECT_ROOT / "Version8"`** (actual load, not stale comment):

| Runner | Class | Blocker for *git* archive of Version8? |
|---|---|---|
| `run_phase_r21a_semantic_dictionary.py` | HISTORICAL / not a web stage | Would break if invoked |
| `run_phase_r20_mtext_recovery.py` | HISTORICAL | Same |
| `run_phase_r201_notation_inventory.py` | HISTORICAL | Same |
| `run_phase_r2b_engineering_context_consumption.py` | HISTORICAL | Same |
| `run_phase_r14_integrity_validation.py` | HISTORICAL | Same |
| `run_phase_si0_stirrup_recovery.py` / `si1_*` | HISTORICAL (web uses T.1 + M.2 in R.1.3) | Same |
| `run_phase_vroot1_verify.py` | HISTORICAL verify vs Version8 Benchmark_Set_2 | Same |
| `run_phase_va2_*`, `vtest3_*`, `vrun1_*` | EXPERIMENTAL | Same |
| `run_phase_qa2b2_*`, `qa30_*` | EXPERIMENTAL / report templates under Version8 | Same |

Live runners whose comments say `python Version8/Run_PY/...` but `root = Path(__file__).parent.parent` is **Version10**: R21C, R21D, L.2.2, R3, R31, R12A, R13, VB1. **Not** a Version8 load.

`Run_PY/_bootstrap.py` docstring says Version8; `parents[1]` is Version10. Live 14 stages do not import this module.

**CURRENT operational tool required for production: NO.**

---

## 8. Documentation Check

| Document | Claim | Actual | Conflict |
|---|---|---|---|
| `PRODUCTION_TRUTH.md` | Version8 R2A/R21B gate **CLOSED** | Matches Phase 3 | None |
| `PRODUCTION_BOUNDARY_MANIFEST.md` | Live R2A/R21B Version10 | Matches | None |
| `PHASE_2_CLEANUP_REPORT.md` | Still describes live R2A **executing Version8** | **Stale** after Phase 3 | HISTORICAL_DOCUMENTATION — do not treat as production truth |
| `PHASE_W19_1_...HOTFIX.md` | GN artefact may point at Version8 Benchmark GN | Pre-Phase-3 note; live factory now Version10 | Stale operational note |
| `Version8/README.md` | Version8 is “Production baseline” 8.9.5 | Historical freeze; live is Version10 W.19.1 | Expected inside frozen tree |
| `Steel-Beam-Estimation/docs/*` | 8.9.x production architecture | Packaging archive | HISTORICAL |
| `ROLLBACK_W3.txt` | Rollback to Version8 `:8000` | Recipe only; public nginx is `:8001` | PRODUCTION_SUPPORT / historical rollback |

This phase did **not** rewrite those docs (audit only). `PRODUCTION_TRUTH.md` remains the current production file.

---

## 9. Version8 Internal Dependency Check

Version8 tree (~1300 files): `src/` (1125), `data/` (904, mostly `web_runs` QA JSON + benchmarks), `Run_PY/` (40 py), `webapp/`, `config/`, `schemas/`, `prompts/`, `docs/`, `Demo1/`.

Grep of Version8 `*.py` for `Version10`: **no matches**.

Classification: **SELF_CONTAINED** relative to Version10. Historical bootstrap `_bootstrap_from_v7.py` and Version8 webapp are internal/historical. Archival of the directory as a unit is mechanically straightforward **after** Version10 stops writing into it.

---

## 10. Version8 → Version10 Shared Resource Check

| Concern | Version8 | Version10 | Current authority | Production uses |
|---|---|---|---|---|
| R.2A package | `Version8/src/PhaseR.2A_*` | `Version10/src/PhaseR.2A_*` (W.16 factory) | Version10 | Live R2A |
| R.2.1B / R.2.1A | Byte-identical copies | Same | Version10 | Live R21B |
| Benchmark GN DXF | `Version8/data/Benchmark_Set_2/general_notes/` | Same filename/bytes in Version10 | Version10 factory | Offline fallback only |
| Semantic dictionary YAML | Version8 copy | Version10 copy (same SHA, Phase 3) | Version10 | Live R21B |
| VB.1 / R.1.3 | Full copies | Live copies | Version10 | Live |
| Prompts / Vision | Version8 `prompts/`, `src/llm` | Version10 W.8 / C.5 / P.253 | Version10 | Live Hybrid |

Do not consolidate in this phase.

---

## 11. Hidden / Dynamic Dependency Check

Searched live web + 14 runners for `importlib`, `spec_from_file_location`, `subprocess`, `STEEL_*`, `Version8` path construction.

- Live R2A/R21B `importlib` now targets **Version10** package dirs.
- Other live stages bootstrap **Version10/src** via `__file__.parent.parent`.
- Adapter subprocess scripts are Version10 `Run_PY/*.py` only.
- No symlink to Version8 found in this audit.
- Hidden live coupling is **filesystem write** (`_write_v7_copy`) and **CLI default** (`_default_input`), not dynamic import of Version8 modules.

---

## 12. Remaining Version8 References

See `VERSION8_REFERENCE_INVENTORY.md` for the classified file list.

Summary:

- Live execute: **0**
- Live required read: **0**
- Live write to Version8 path: **1 mechanism** (VROOT1 copy)
- Non-web actual Version8 `src` loads: **~12 runners / experimental packages**
- Docs / YAML / comments: **many**, not runtime

---

## 13. Risk Assessment

| Risk | If Version8 moved *today* with no code change |
|---|---|
| Live Excel / Hybrid / Vision | Should still run; adapter never imports Version8 |
| Next VROOT1 web run | Recreates `Version8/data/output/PhaseVROOT.1_*` stub |
| Offline VROOT1 no-argv | `_default_input` fails (no Benchmark_Set under Version8) |
| Non-web SI/QA/VA CLIs | Import/path errors |
| Lightsail `:8000` rollback | Unaffected until someone deletes the **server** tree |
| Accidental “Version8 still production” from `PHASE_2_CLEANUP_REPORT.md` | Operator confusion only |

Moving Version8 **without** prerequisite 1 violates “moved without changing production code” because production would keep targeting that path.

---

## 14. Archive Recommendation

**CONDITIONAL_GO.**

Do not archive in Phase 4.

Next: minimal VROOT1 path retarget (write copy + CLI default), then a dedicated archive-move phase that leaves Version8 physically recoverable and does not delete the Lightsail rollback copy unless operators retire it.

---

## Appendix A — Version8 tree inventory (significant folders)

Folded here so Phase 4 creates only the three named audit files.

| PATH | PURPOSE | TYPE | RUNTIME RELEVANCE | ARCHIVE STATUS | CONFIDENCE |
|---|---|---|---|---|---|
| `Version8/src/` | Frozen 8.9.x engineering packages | code | Not live web after Phase 3 | Historical; keep until Phase 5b | High |
| `Version8/Run_PY/` | Frozen runners | code | Not live web | Historical | High |
| `Version8/webapp/` | 8.9.x Flask app | code | Not public (`:8001` is V10) | Historical; server rollback possible | High |
| `Version8/config/` | YAML | config | Not live RunContext | Historical | High |
| `Version8/schemas/` | JSON schemas | resource | Not live | Historical | High |
| `Version8/prompts/` | LLM templates | resource | Live Hybrid uses Version10 | Historical | High |
| `Version8/data/Benchmark_Set_*` | Drawing / GN fixtures | data | CLI default only | Duplicate in Version10 | High |
| `Version8/data/web_runs/` | Old QA run JSON | generated | None | Generated artifact | High |
| `Version8/data/output/` | Includes VROOT1 copies from **Version10** live runs | generated + live write target | Write side-effect | Prerequisite to retarget | High |
| `Version8/docs/`, `README.md`, `VERSION_FREEZE.md` | Freeze narrative | docs | None | Historical | High |
| `Version8/requirements.txt` | 8.9.x deps | config | None | Historical | High |
| `Version8/_bootstrap_from_v7.py` | Historical import | code | None | Historical | High |
| `Version8/Demo1/` | Demo | data | None | Historical | High |

---

## Appendix B — Archive safety matrix

| Area | Version8 dependency | Current? | Production? | Blocker? | Action |
|---|---|---|---|---|---|
| Web runtime (Flask/adapter) | None | — | No | No | None |
| R2A | Closed (V10) | No | No | No | None |
| R2.1B | Closed (V10) | No | No | No | None |
| R2.1C+ / L.2.2 / R3 / R31 / R12A | Stale comments; load V10 | No | No | No | Later comment cleanup |
| Hybrid / Vision | None | No | No | No | None |
| R.1.3 | Comment only | No | No | No | None |
| VB.1 Excel | Optional `phase_i` inspect | Soft | No required read | No | Optional path retarget |
| VROOT1 | Write copy + CLI default | **Yes write** | Write only | **Yes for move** | Retarget before archive |
| Production config / systemd / nginx live | None | No | No | No | None |
| Deployment rollback docs | `:8000` Version8 | Recipe | Support | Conditional | Server policy |
| Production data GN | V10 + upload | No V8 read | No | No | None |
| Current tests | No | No | No | No | None |
| Operational CLI (non-web) | Many hardcoded V8 | If invoked | No | Conditional | Policy or retarget |
| Documentation | Many historical | Mixed stale | No | No | Do not use Phase 2 report as truth |
| Experiments / QA | Hardcoded V8 | If invoked | No | Conditional | Same as CLI |

---

## Appendix C — Production dependency graph (current)

```
Version10 Hybrid Production (W.19.1)
        │
        ├── Version10/webapp (wsgi, adapter, config)
        ├── Version10/Run_PY (14 PRODUCTION_STAGES)
        ├── Version10/src (R2A W.16 factory, R21B, R.1.3, W.6, VB.1, …)
        ├── STEEL_RUN_ROOT uploads (authoritative GN)
        ├── Version10/data/Benchmark_Set_2 (offline GN fallback)
        └── Version8/data/output/PhaseVROOT.1_*   ← WRITE ONLY (trace copy)
```

Desired after prerequisites:

```
Version10 Hybrid Production
        ├── Version10 runtime
        ├── approved shared Version10 resources
        └── no Version8 path on live execute/read/write
```
