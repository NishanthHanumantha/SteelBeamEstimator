# Phase D.5.4 — Web Pipeline Completion (R.3)

**MODEL_VERSION:** 8.9.3  
**Date:** 2026-07-28  
**Scope:** Web-enable Phase R.3 (Geometry Context Engine) on RunContext

---

## 1. Architecture summary

D.5.3 produced run-scoped `EngineeringFacts.json` (R.2.1D) and
`geometry_registry.json` (L.2.2). D.5.4 migrates R.3 so it consumes those
artefacts (plus VROOT1 `beam_registry` and R.1 annotations) from the **same**
run via `RunContext`.

Removed:

- `version7_root` constructor parameter
- `_find_output()` shared-path discovery
- `_find_production_workbook()` shared-output search
- Version7 / Benchmark / shared `data/output` assumptions in the R.3 hot path

Engineering algorithms (axis, supports, projection, zones, validation) unchanged.

Production pipeline stops after R.3 (R.3.1 / Excel deferred to D.5.5).

---

## 2. Updated pipeline diagram

```text
Upload → VROOT1 → R1 → R2A → R.2.1B → R.2.1C → R.2.1D → L.2.2 → R.3 → SUCCESS
```

---

## 3. RunContext integration summary

| Item | Detail |
|------|--------|
| Constant | `PHASE_R3 = "PhaseR3_geometry_context_engine"` |
| Env | `STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT` |
| Runner | `run_phase_r3_geometry_context_engine.py [<run_root>]` |
| Offline default | `run_root = engine_root` → `Version8/data/output/...` |

---

## 4. R.3 input/output redesign

| Direction | Path under run `output_root` |
|-----------|------------------------------|
| **In** | `PhaseR2.1D_.../EngineeringFacts.json` |
| **In** | `PhaseL.2.2_geometry_recovery/geometry_registry.json` |
| **In** | `PhaseVROOT.1_.../beam_registry.json` |
| **In** | `PhaseR.1_.../reinforcement_annotations.json` |
| **Out** | `PhaseR3_geometry_context_engine/` (`GeometryContexts.json` + 11 siblings) |

Folder name kept as `PhaseR3_geometry_context_engine` (engineering contract),
not a short `PhaseR3/` alias.

---

## 5. Files modified

| Area | Files |
|------|--------|
| R.3 | `phase_r3_orchestrator.py`, `__init__.py`, `Run_PY/run_phase_r3_...py` |
| Run context | `PHASE_R3`, MODEL_VERSION 8.9.3 |
| Local web | `webapp/config.py`, `app.py`, `services/estimation_service.py` |
| Deploy web | `settings.py`, `model_info.yaml`, `webapp/config.py`, `services.py` |
| Docs | this file, `PIPELINE.md`, `ReleaseNotes.md`, README |

---

## 6. Removed Version7 / Benchmark dependencies

- No `version7_root` parameter
- No Benchmark_Set path usage in R.3
- No shared Version8/data/output discovery for required inputs
- No seed / copy of R.3 prerequisites in the D.5.4 hot path

---

## 7. Removed `_find_output()` usage

| Before | After |
|--------|-------|
| `_find_output(rel)` → `self._root / "data/output" / rel` | Explicit paths from `RunContext.artefact(...)` / constructor args |
| `_find_production_workbook()` searched shared Production_Output | Removed; validator receives `production_workbook=None` (Excel deferred) |

---

## 8. Validation results

- [x] `PRODUCTION_STAGES` includes R3 after L22 (both webapps)
- [x] Success requires facts + registry + `GeometryContexts.json`
- [x] Orchestrator has no `_find_output` / `version7_root`
- [x] Grep R.3 package + runner: no `_find_output` / `version7_root` / Benchmark_Set
- [x] Synthetic run-scoped smoke: same-run facts+registry → 12 artefacts, 12/12 rules, exit 0
- [ ] End-to-end upload smoke (operator)

---

## 9. Remaining blockers before D.5.5

| Blocker | Notes |
|---------|--------|
| R.3.1 | Still offline / shared-output assumptions |
| R.1.2 / R.1.3 / VB.1 | Not in production stages |
| Excel workbook | Intentionally out of scope |

---

## 10. MODEL_VERSION

`8.9.2` → **`8.9.3`**

---

## 11. Suggested git commit message

```text
feat(D.5.4): web-enable R.3 Geometry Context Engine (MODEL_VERSION 8.9.3)

Consume same-run EngineeringFacts + geometry_registry via RunContext;
extend production pipeline through R.3; leave R.3.1/Excel for D.5.5.
```

---

## 12. Production readiness assessment

| Capability | Ready? |
|------------|--------|
| Upload → … → L.2.2 → R.3 | **Yes** (architecture) |
| Same-run facts + registry → GeometryContexts | **Yes** |
| No Benchmark / Version7 / shared-output for R.3 | **Yes** |
| R.3.1 / Excel | **Not ready** — D.5.5 |
