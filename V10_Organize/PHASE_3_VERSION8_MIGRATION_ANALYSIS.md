# Phase 3 Version8 Migration Analysis

**Date:** 2026-08-31  
**Git baseline:** `f1febd2f` — checkpoint: freeze Version10 Hybrid W.19.1 production baseline  
**Scope:** Live web R.2A and R.2.1B runtime only. Version8 is not archived.

---

## 1. Current Version8 Runtime Dependencies

Live web (`Version10/webapp/services/version10_adapter.py`) runs each stage as:

```
cwd = Version10
STEEL_ENGINE_ROOT = Version10
STEEL_RUN_ROOT = data/web_runs/<run_id>
STEEL_OUTPUT_ROOT = <run>/data/output
argv[1] = staging path
```

Two of the 14 stages then **ignore Version10 `src` and importlib-load Version8**:

| Stage | Runner | Loaded package | `engine_root` passed to orchestrator |
|---|---|---|---|
| R2A | `Version10/Run_PY/run_phase_r2a_engineering_context.py` | `Version8/src/PhaseR.2A_engineering_context` | `Version8/` |
| R21B | `Version10/Run_PY/run_phase_r21b_semantic_interpreter.py` | `Version8/src/PhaseR2.1B_engineering_semantic_interpreter` | `Version8/` |

`config.run_context` for those subprocesses is also taken from **Version8** `src` because that path is inserted first.

All other web stages already bootstrap from `Path(__file__).parent.parent` = Version10.

---

## 2. R2A Execution Chain

```
version10_adapter._run_live_stage(R2A)
  → python Version10/Run_PY/run_phase_r2a_engineering_context.py <staging>
  → sys.path += Version8/src
  → importlib load PhaseR.2A_* (22 modules) from Version8
  → resolve_run_context(engine_root=Version8)
  → PhaseR2AOrchestrator(v7_root=Version8, output_dir=<run>/data/output/PhaseR.2A_*)
  → EngineeringContextFactory._discover_gn_path(Version8)
       1. Version8 src/.../beam_registry.json   (NOT the web pointer)
       2. Version8/data/Benchmark_Set_2/general_notes/
  → EngineeringContextBuilder.parse GN
  → EngineeringContextWriter → 7 JSON artefacts under STEEL_OUTPUT_ROOT
```

Web pointer (`Version10/src/PhaseVROOT.1_.../beam_registry.json`, `write_r2a_gn_pointer`) is **not read**.  
Version8 factory has **no** `STEEL_RUN_ROOT` check.

Downstream consumers of R.2A **artefacts** (run-scoped JSON), not of Version8 source:

- VB.1 `loader_summary_from_r2a_artefacts()` (W.19.1)
- R.1.3 optional in-process R.2A package load from `self._engine` (Version10 on later stages)

---

## 3. R2.1B Execution Chain

```
python Version10/Run_PY/run_phase_r21b_semantic_interpreter.py <staging>
  → sys.path += Version8/src + Version8/
  → importlib load PhaseR2.1B_* from Version8
  → resolve_run_context(engine_root=Version8)
  → PhaseR21BOrchestrator(engine_root=Version8, output_root=STEEL_OUTPUT_ROOT, ...)
  → _load_annotations() from run-scoped PhaseR.1 JSON
  → _load_semantic_dictionary() from engine_root/src/PhaseR2.1A_*
  → SemanticInterpreter.interpret_all
  → export engineering_semantic_objects.json (R.2.1C contract)
  → _run_production() nested R.1.3/VB.1 from engine_root (errors swallowed)
```

R.2.1C (already Version10) reads:

`<STEEL_OUTPUT_ROOT>/PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json`

---

## 4. Version10 Candidate Implementations

| Concern | Version8 live | Version10 candidate | Same files? |
|---|---|---|---|
| R.2A package | `Version8/src/PhaseR.2A_engineering_context/` | `Version10/src/PhaseR.2A_engineering_context/` | Same 27 filenames |
| R.2.1B package | `Version8/src/PhaseR2.1B_*` | `Version10/src/PhaseR2.1B_*` | **Byte-identical (all 15 files)** |
| R.2.1A (loaded by R.2.1B) | `Version8/src/PhaseR2.1A_*` | `Version10/src/PhaseR2.1A_*` | **Byte-identical (all 13 files)** |
| Dictionary YAML | `Version8/config/engineering_semantic_dictionary.yaml` | Version10 copy | **Same SHA-256** |
| Notation inventory | missing both trees | missing both trees | Same (empty/fail → empty dict) |

---

## 5. R2A Comparison

| Topic | Version8 (live) | Version10 candidate |
|---|---|---|
| GN discovery | registry under **v7_root** then Benchmark_Set_2 | **0. STEEL_RUN_ROOT/general_notes/*.dxf** then registry then Benchmark_Set_2 |
| Web GN pointer | Ignored (written under Version10) | Read if v7_root=Version10 and no run GN |
| Orchestrator / writer / model | Identical | Identical |
| Cover / DL / grade parsers | Absolute Galera TABLE 2 windows | Table-title-relative windows (W.16) + Galera fallback |
| Loader.summary() | Core keys only | Additive `cover_source`, `dev_length_source`, `gn_dxf_path` |
| Output dir | Run-scoped via STEEL_OUTPUT_ROOT | Same if runner passes Version10 engine + env |
| Output JSON schema | 7 artefacts, same writer | Same writer |

**Same Benchmark_Set_2 GN DXF (SHA identical in V8 and V10) parsed both factories:**

| Field | V8 | V10 |
|---|---|---|
| passed | True | True |
| primary_steel_grade | Fe550 | Fe550 |
| cover_beam_mm | 30 | 30 |
| concrete_grade_beam | M30 | M30 |
| dev_length_factor | 50 | 50 |
| parse_confidence | 1.0 | 1.0 |
| cover_source | (absent) | GN_DXF_TABLE_2 |

Material engineering values match on the shared Galera-class GN. Version10 extra keys are provenance for W.16/W.19.1 Excel.

---

## 6. R2.1B Comparison

Interpreter, models, export, validation: **identical source**.

| Topic | Live (engine_root=Version8) | After (engine_root=Version10) |
|---|---|---|
| Annotations | Run-scoped R.1 JSON | Unchanged |
| Dictionary code/YAML | Identical | Identical |
| Inventory JSON | Missing | Missing |
| Nested R.1.3/VB.1 in `_run_production` | Version8 src; exceptions swallowed | Version10 src; still swallowed; later web stages already run V10 R.1.3/VB.1 |
| ESO JSON contract for R.2.1C | Same exporter | Same exporter |

---

## 7. GN Path Comparison

| Source | Role |
|---|---|
| Upload `STEEL_RUN_ROOT/general_notes/` | **Authoritative production GN** (web contract) |
| Version10 `beam_registry.json` pointer | Web fallback; unused by live Version8 factory |
| `Version8/data/Benchmark_Set_2/general_notes/` | Live accidental fallback (Galera Fe550 sheet) |
| `Version10/data/Benchmark_Set_2/general_notes/` | Same DXF bytes as Version8 copy |

**Correct production behaviour:** prefer uploaded run GN (`STEEL_RUN_ROOT`), then Version10 pointer, then Version10 Benchmark_Set_2. That is already implemented in **Version10** `engineering_context_factory.py` and tested by W.16 `test_gn_discovery_prefers_steel_run_root`. Live never executes that factory.

Do **not** patch the Version8 factory; migrate the web runner to Version10 source.

---

## 8. Behavioural Differences

- Live R.2A can parse **Benchmark_Set_2 Galera GN** instead of the uploaded project GN (Inizio Fe550 vs expected project table — known issue).  
- Version10 parsers locate TABLE 1/2 by title (W.16), so non-Galera sheets parse correctly.  
- On the identical Galera GN file, V8 and V10 produce the same cover/grade/Ld numbers.

---

## 9. Data Contract Differences

- R.2A artefact **filenames and writer** unchanged.  
- Loader summary **gains** optional keys; VB.1 W.19.1 mapping already expects run artefacts, not loader-in-process.  
- R.2.1B `engineering_semantic_objects.json` unchanged.

---

## 10. Migration Risks

| Risk | Mitigation |
|---|---|
| Nested R.2.1B `_run_production` switches V8→V10 R.1.3 | Side path; errors swallowed; web R.1.3/VB.1 stages unchanged |
| Inizio GN parse changes vs current live fallback | Intended; W.16 tests Version10 Inizio TABLE 2 |
| Offline CLI without STEEL_RUN_ROOT | Falls back to Version10 Benchmark_Set_2 (same DXF as Version8) |
| Unrelated dirty tree | Stage only the two runners + Phase 3 docs |

---

## 11. Recommended Migration Strategy

**Minimal runner retarget only.** Do not rewrite parsers, orchestrators, W.6, R.1.3, or VB.1.

1. Point `run_phase_r2a_engineering_context.py` at `Version10/src/PhaseR.2A_*`; `engine_root=Version10`.  
2. Point `run_phase_r21b_semantic_interpreter.py` at `Version10/src/PhaseR2.1B_*`; `engine_root=Version10`.  
3. Leave Version8 tree untouched.

---

## 12. Validation Strategy

- Syntax/import of the two runners.  
- Grep live runners: no `Version8/src` load.  
- `PRODUCTION_STAGES` still 14; T.1; HYBRID=W.6; VB.1 last.  
- W.16, W.19.1, W.6 stub, W.2 smoke, W.18B spacer.  
- No live Claude estimate.

---

## 13. Go / No-Go Decision

**GO**

Evidence: R.2.1B/R.2.1A byte-identical; R.2A Version10 is the W.16 production factory already tested; same GN bytes yield same engineering numbers plus provenance; output writers identical; web env already supplies `STEEL_RUN_ROOT`; Hybrid/R.1.3/VB.1 untouched.

---

## 14. Implementation (after GO)

Minimal runner retarget applied 2026-08-31:

- `Version10/Run_PY/run_phase_r2a_engineering_context.py` — `ENGINE_ROOT = Version10`
- `Version10/Run_PY/run_phase_r21b_semantic_interpreter.py` — `ENGINE_ROOT = Version10`

Version8 tree not deleted, moved, or archived.

