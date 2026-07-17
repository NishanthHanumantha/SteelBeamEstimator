# Steel Beam Estimator — Version 8

**Active development branch.** Continues from frozen **Version 7** at MODEL_VERSION **8.3.0**.

**Version 7 is frozen.** Do not add new features there. All new work starts here.

---

## Why Version 8

Version 7 accumulated many forensic / audit / legacy packages and regenerated outputs that made the production path hard to follow. Version 8 keeps only the packages required for the working engineering → estimation spine.

---

## Production pipeline (clear order)

| Step | Phase | Package | Runner |
|------|-------|---------|--------|
| 1 | V.ROOT.1 | `PhaseVROOT.1_dynamic_pipeline_initialization` | `run_phase_vroot1_dynamic_pipeline_initialization.py` |
| 2 | R.2A | `PhaseR.2A_engineering_context` | `run_phase_r2a_engineering_context.py` |
| 3 | R.3 / R.3.1 | geometry + relationships (leaders) | `run_phase_r3_*.py` / `run_phase_r31_*.py` |
| 4 | R.1 (+ R.1.1A) | annotation discovery | `run_phase_r1_generalized_reinforcement_discovery.py` |
| 5 | R.1.2A | GeometryProvider / span fix | `run_phase_r12a_geometry_accuracy.py` |
| 6 | R.1.3 | EngineeringBarModels | `run_phase_r13_pipeline_integration.py` |
| 7 | V.B.1 | Steel / BBS / Excel | `run_phase_vb1_production_output_completion.py` |

Supporting / validation (as needed):

- `PhaseR1_1A_annotation_coverage` — coverage regression
- `PhaseR1_1B_production_integration` — production source audit
- `PhaseR1.4_integrity_validation` — called from V.B.1
- `PhaseSI.0` / `PhaseSI.1` — stirrup path used by V.B.1
- `PhaseL.2` — legacy fallback only (not primary)
- `PhaseVTEST3*` / `PhaseVA.2` — benchmark comparison

**Next planned phase:** R.1.2B — EngineeringBar Deduplication & Consolidation Engine

---

## What was copied from Version 7

| Area | Included |
|------|----------|
| `src/` shared libs | ai, config, engineering_*, extractor, llm, parser, project, property_*, reinforcement*, services, utils |
| `src/` active phases | V.ROOT.1, R.1, R.1.1A/B, R.1.2A, R.1.3, R.1.4, R.2A/B, R.3/R.3.1, SI.0/SI.1, L.2 (fallback), V.B.1, V.RUN.1, V.TEST3*, V.A.2 |
| `Run_PY/` | runners for packages above only |
| `config/`, `schemas/`, `prompts/` | yes |
| `data/Benchmark_Set_*`, framing, notes, Excel template | yes (inputs) |
| `data/output/**` | **not copied** — regenerate locally |

## What was intentionally excluded

Forensic / superseded packages left in Version 7 only, for example:

- PhaseGN.1, PhaseL.2.1, PhaseL.2.2, PhaseL.3
- PhaseR.1.1 / R.1.2 audits, PhaseR1.5*, PhaseR2.0*, PhaseR2.1*
- PhaseR.2A.AUDIT, PhaseVA.1.1, PhaseVTRACE*, PhaseVTEST3_3
- All regenerated `data/output/**` artefacts
- Temp logs, `__pycache__`, Excel lock files (`~$*`)

---

## Setup

```powershell
pip install -r requirements.txt
cd Version8
$env:PYTHONPATH="src"
```

## Quick start (Set 3 production path)

```powershell
cd Version8
python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py
python Run_PY/run_phase_r2a_engineering_context.py
python Run_PY/run_phase_r31_engineering_relationship_engine.py
python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py
python Run_PY/run_phase_r12a_geometry_accuracy.py
python Run_PY/run_phase_r13_pipeline_integration.py
python Run_PY/run_phase_vb1_production_output_completion.py
```

Outputs appear under `Version8/data/output/`.

---

## Freeze baseline (from Version 7)

- MODEL_VERSION: **8.3.0**
- Annotation coverage: 61/61 beams (R.1.1A)
- Production source: EngineeringBarModels only (R.1.1B)
- Geometry: GeometryProvider, no constant 8.775 m span (R.1.2A)
