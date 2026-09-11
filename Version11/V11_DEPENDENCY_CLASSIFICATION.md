# V11.0 Dependency Classification

Source of truth: Version10 executable production path (`webapp/config.py` `PRODUCTION_STAGES` + static/dynamic imports), not stale READMEs.

Classes: `MUST_COPY` | `SUPPORTING` | `EXCLUDED` | `GENERATED` | `EXPERIMENTAL` | `UNKNOWN`

---

## MUST_COPY

Required for the Version11 production/runtime boundary.

### Web entry

- `webapp/wsgi.py`, `app.py`, `routes.py`, `config.py`
- `webapp/services/{estimation_service,version10_adapter,result_registry,flight_guard,hybrid_shadow_service}.py`
- `webapp/templates/`, `webapp/static/`

### 14 runners

All `PRODUCTION_STAGES` scripts listed in `V11_BASELINE_MANIFEST.md`.

### Deterministic packages

VROOT.1, R.1, T.1, T.16, R.2A, R.2.1B, R.2.1C, R.2.1D, L.2.2, R3, R.3.1, R.1.2A, R.1.3, R.1.2B, R.1.2C, R.1.2D, R.1.3 piece generation, V.9 spacer, SI.1, VB.1, `src/config`, `src/llm`.

### Hybrid / Vision (proven imports)

| Package | Proven production use |
|---|---|
| W.5 | hybrid shadow adapter / live_invoke |
| W.6 | production hybrid stage / handoff |
| W.8 | crop/evidence generator |
| W.10 | `write_run_monitor` from W.6 orchestrator (fail-safe) |
| W.11 | hybrid reliability support |
| P.253 | Claude Vision client |
| C.5 | `claude_call`, `vision_prompt`, `vision_contract`, `normalize` |
| C.3 | `claude_client.encode_png` |
| E.2 | `live_caller` |
| E.1 | `hybrid_runner_adapter` |
| D.1–D.4 | contract / resolver / binding / calculation-compat modules used on the hybrid path |
| P.269 | extractor used by W.6 handoff |
| P.26 (`role_family` only) | imported by P.269 `layer_role.py` |
| P.2610A / B / B2 / C1C2 | W.8 cropper / envelope / quality / selector |
| M.1 | DXF renderer required by W.8 path |

### Config / tests / manifests

- `config/*.yaml`
- `requirements.txt`
- W.2, W.16, W.18B, W.19.1, W.6 tests listed in the freeze manifest
- Benchmark_Set_2 DXF fixtures required for factory GN / local reproduction

---

## SUPPORTING

Copied because they sit in the same mixed package as MUST_COPY modules, or they are fork tooling / docs:

- Experimental orchestrator/report files **inside** mixed packages (C.5 `phase_p2610c5_orchestrator.py`, E.1/E.2 report writers, D.* regression, etc.). They are not production stages. They were copied with the package to avoid splitting mixed trees in V11.0. Import-time loading was neutralized via `__init__.py`.
- `docs/v10_deployment_reference/` (W.19.1 hotfix + env example) — reference only
- `Version11/tools/` bootstrap and verify scripts
- E.1/E.2 JSON fixtures under `data/baseline/` (stub KPIs)

---

## EXCLUDED

Proven non-dependencies or out of V11.0 scope:

- Version1–Version9, `Steel-Beam-Estimation/`
- Version8 (no V11 runtime import; archive is a separate hold)
- Unused `Run_PY` runners (L.2 non-web, R.1.3 piece runner as a web stage, QA/VA/VTEST/VRUN CLIs, 91 non-web scripts)
- `pack_w*.py`, live nginx/systemd, Lightsail overlays
- 86 Version10 `src/` packages not on the traced production graph, including among others:
  - `PhaseP254_semantic_reinforcement_vision_benchmark`
  - `PhaseP2610B1_population_generalization` (B.2 `population.py` research path only; W.8 production import succeeded without it after `__init__` neutralization)
  - `PhaseP2610E3_*` orchestrator package
  - `PhaseQA*`, `PhaseVA.2`, `PhaseVTEST*`, `PhaseVRUN.1`
  - P.21–P.25 / P.261–P.268 research gates
  - leftover `engineering_geometry`, `extractor`, `parser`, `ai`, `utils` stacks
- Remainder of P.26 beyond the three `role_family` files

---

## GENERATED

Must not be treated as source. Not copied into Version11 except empty `.gitkeep` placeholders:

- `Version10/data/output/**` bulk
- `Version10/data/web_runs/**` contents
- web uploads / generated Excel copies / `webapp.log`
- Office lock files, `__pycache__`, `.pytest_cache`
- benchmark review crops / Claude transcripts / E.3 per-beam review trees

Exception: a **small extracted KPI JSON** (`data/baseline/P2610E3_pooled_kpis.json`) was written from the E.3 `report_data.json` so V11 can cite the accuracy baseline without copying the generated bulk.

---

## EXPERIMENTAL

Benchmark/research orchestration that is not a production stage. Some experimental **filenames** live inside MUST_COPY mixed packages (SUPPORTING, not deleted). Standalone experimental packages were EXCLUDED unless a production import was proven (P.26 `role_family` and W.10 were proven and promoted to MUST_COPY).

Do not assume a directory is experimental merely because its name contains `benchmark`. Trace imports. Counterexamples that **are** production: C.5, E.1 adapter, E.2 live_caller, D.2 resolver.

---

## UNKNOWN

Files inside mixed packages that `PRODUCTION_MODULE_INDEX.md` marks as not on the W.5/W.6/W.8 graph (for example some P.253 / C.3 helpers). They were copied with the package rather than split. They are not used as V11 stages. Future V11 hygiene may trim them; V11.0 does not.

Ambiguities encountered and how they were resolved:

| Item | Resolution |
|---|---|
| P.26 whole package vs `role_family` | Copied three files only after W.6 unit tests proved the import |
| W.10 | Copied full small package after W.6 orchestrator import was traced |
| P.254 / B.1 | Not copied; mixed `__init__.py` neutralized so production submodules import without them |
| `config.run_context` import-checker failure | Name collision with webapp `config` in a naive loader; module compiles and is present |
| UTF-8 BOM on R21B/C/D runners | Present in Version10 originals; Python/`compileall` accept them; not a V11 divergence |

No Version8/Version9 import was found in the V11 production path.
