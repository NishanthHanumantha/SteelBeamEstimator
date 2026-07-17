# Version 8 — Pipeline Steps

Run from `Version8/` with `PYTHONPATH=src` (or rely on each runner’s path setup).

## Core production path

```text
1. V.ROOT.1     Beam registry + drawing manifest
2. R.2A         Engineering context (Ld, cover, grades)
3. R.3 / R.3.1  Geometry context + leader relationships
4. R.1          Reinforcement annotation discovery (includes R.1.1A adaptive association)
5. R.1.2A       GeometryProvider — per-beam spans (no shared defaults)
6. R.1.3        EngineeringBarModels → production reinforcement models
7. V.B.1        Steel weight + BBS + Estimation_Output.xlsx
```

## Commands

```powershell
python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py
python Run_PY/run_phase_r2a_engineering_context.py
python Run_PY/run_phase_r3_geometry_context_engine.py
python Run_PY/run_phase_r31_engineering_relationship_engine.py
python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py
python Run_PY/run_phase_r12a_geometry_accuracy.py
python Run_PY/run_phase_r13_pipeline_integration.py
python Run_PY/run_phase_vb1_production_output_completion.py
```

## Optional audits

```powershell
python Run_PY/run_phase_r11a_annotation_coverage.py
python Run_PY/run_phase_r11b_production_integration.py
python Run_PY/run_phase_vtest32_estimator_comparison_engine.py
```

## Next

**R.1.2B — EngineeringBar Deduplication & Consolidation Engine**
