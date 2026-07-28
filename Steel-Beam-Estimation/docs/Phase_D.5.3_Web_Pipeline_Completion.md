# Phase D.5.3 — Web Pipeline Completion (L.2.2)

**MODEL_VERSION:** 8.9.2  
**Date:** 2026-07-28  
**Scope:** Web-enable Phase L.2.2 (Geometry Registry) on RunContext

---

## 1. Architecture summary

D.5.2 delivered run-scoped R.2.1D `EngineeringFacts.json`. D.5.3 adds L.2.2 so
`geometry_registry.json` is generated from the **current run’s VROOT1**
`beam_registry.json` (optional: `dynamic_beam_geometry.json`).

Output path (R.3 contract preserved):

```text
web_runs/<run_id>/data/output/PhaseL.2.2_geometry_recovery/geometry_registry.json
```

Version8 did not previously contain a production L.2.2 package on the R-spine.
The Version7 L.2.2 stage depended on L.2 / L.2.1 / Version5 and cannot run on
the web pipeline. D.5.3 introduces a Version8 `PhaseL.2.2_geometry_recovery`
package that:

- Preserves the R.3 registry **schema** and axis/support **construction rules**
  (`build_entry_recovered` / LEFT@0 + RIGHT@1)
- Replaces L.2/L.2.1/V5 inputs with VROOT1 run outputs
- Uses RunContext for all I/O

Production pipeline stops after L.2.2 (R.3 deferred to D.5.4).

---

## 2. Updated pipeline diagram

```text
Upload → VROOT1 → R1 → R2A → R.2.1B → R.2.1C → R.2.1D → L.2.2 → SUCCESS
                                                              │
                                                              ▼
                                         geometry_registry.json (run-scoped)
```

---

## 3. RunContext integration summary

| Item | Detail |
|------|--------|
| Constant | `PHASE_L22 = "PhaseL.2.2_geometry_recovery"` |
| Env | `STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT` |
| Runner | `run_phase_l2_2_geometry_recovery.py [<run_root>]` |
| Offline default | `run_root = engine_root` → `Version8/data/output/...` |

---

## 4. L.2.2 input/output redesign

| Direction | Path (relative to run `output_root`) |
|-----------|--------------------------------------|
| **Input (required)** | `PhaseVROOT.1_.../beam_registry.json` |
| **Input (optional)** | `PhaseVROOT.1_.../dynamic_beam_geometry.json` |
| **Output** | `PhaseL.2.2_geometry_recovery/geometry_registry.json` |

Removed / not used:

- Benchmark_Set_*
- Version7 / Version5 schedule paths
- L.2 beam_reinforcement_models / L.2.1 retrigger
- Shared `Version8/data/output` as web production source of truth

---

## 5. Files modified / added

| Area | Files |
|------|--------|
| New package | `Version8/src/PhaseL.2.2_geometry_recovery/*` |
| Runner | `Version8/Run_PY/run_phase_l2_2_geometry_recovery.py` |
| Run context | `PHASE_L22`, MODEL_VERSION 8.9.2 |
| Local web | `webapp/config.py`, `app.py`, `services/estimation_service.py` |
| Deploy web | `settings.py`, `model_info.yaml`, `webapp/config.py`, `services.py` |
| Docs | this file, `PIPELINE.md`, `ReleaseNotes.md`, README |

---

## 6. Removed legacy dependencies

- No Benchmark_Set path usage in L.2.2
- No Version7 path hardcoded for geometry registry generation
- No seed / copy of `geometry_registry.json` in the D.5.3 hot path
- No L.2.1 / Version5 offline prerequisite for web runs

---

## 7. Validation results

- [x] `PRODUCTION_STAGES` includes L22 after R21D (both webapps)
- [x] Success requires R.2.1D facts **and** L.2.2 `geometry_registry.json`
- [x] Package folder name matches R.3 expectation (`PhaseL.2.2_geometry_recovery`)
- [x] No Benchmark_Set / Version7 path deps in L.2.2 code (comments only)
- [x] Synthetic run-scoped smoke: VROOT1 `beam_registry` → L.2.2 wrote registry (exit 0)
- [ ] End-to-end upload smoke (operator)

---

## 8. R3 migration readiness (D.5.4 — do not implement here)

| Consumer assumption today | Required change in D.5.4 |
|---------------------------|--------------------------|
| `PhaseR3Orchestrator(version7_root=...)` | Accept `RunContext` / `output_root` |
| `_find_output(rel)` → `self._root / "data/output" / rel` | `ctx.artefact(...)` under **same** run |
| Reads `PhaseR2.1D_.../EngineeringFacts.json` | Already correct relative name — path root must be run `output_root` |
| Reads `PhaseL.2.2_geometry_recovery/geometry_registry.json` | Same — now produced in-run by D.5.3 |
| Also loads VROOT1 `beam_registry` + R1 annotations | Same relative names under run tree |
| Shared / Version7 seeding helpers in webapp | Remove when R.3 is web-enabled |

R.3 engineering logic can stay; only I/O + pipeline stage wiring belong in D.5.4.

---

## 9. Remaining blockers before R3 integration

| Blocker | Notes |
|---------|--------|
| R.3 RunContext | Still shared-output / `version7_root` constructor |
| R.3.1 | Same shared-output assumption |
| Excel / VB.1 | Intentionally out of scope |

Both critical artefacts for R.3 are now produced per run:

- `EngineeringFacts.json` (R.2.1D)
- `geometry_registry.json` (L.2.2)

---

## 10. MODEL_VERSION

`8.9.1` → **`8.9.2`**

---

## 11. Suggested git commit message

```text
feat(D.5.3): web-enable L.2.2 geometry registry (MODEL_VERSION 8.9.2)

Generate run-scoped geometry_registry.json from VROOT1 via RunContext;
extend production pipeline through L.2.2; leave R.3 for D.5.4.
```

---

## 12. Production readiness assessment

| Capability | Ready? |
|------------|--------|
| Upload → … → R.2.1D → L.2.2 | **Yes** (architecture) |
| Dynamic `EngineeringFacts.json` + `geometry_registry.json` | **Yes** |
| No Benchmark / Version7 / seed for L.2.2 | **Yes** |
| R.3 / Excel | **Not ready** — D.5.4+ |
