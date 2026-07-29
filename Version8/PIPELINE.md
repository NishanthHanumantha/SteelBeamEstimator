```text
1. V.ROOT.1     Beam registry + drawing manifest
2. R.1          Reinforcement annotation discovery
3. R.2A         Engineering context (Ld, cover, grades)
4. R.2.1B       Engineering semantic objects (web-capable, D.5.1)
5. R.2.1C       Engineering fact normalization (web-capable, D.5.1)
6. R.2.1D       Evidence / hypotheses → EngineeringFacts (web-capable, D.5.2)
7. L.2.2        geometry_registry (web-capable, D.5.3)
8. R.3          Geometry context (web-capable, D.5.4)
9. R.3.1        Drawing relationships (web-capable, D.5.5)
10. R.1.2A      Geometry catalog (web catalog-only, D.5.5)
11. R.1.3       EngineeringBarModel integration (web build-only, D.5.5)
12. V.B.1       Steel / BBS / Excel (web-capable, D.5.5)
```

MODEL_VERSION: 8.9.4

## Web production pipeline (D.5.5)

```text
Upload DXFs
  → Version8/data/web_runs/<run_id>/{general_notes,framing,reinforcement}/
  → VROOT1 → R1 → R2A → R.2.1B → R.2.1C → R.2.1D → L.2.2 → R.3
  → R.3.1 → R.1.2A → R.1.3 → VB.1
  → <run_id>/data/output/Production_Output/Estimation_Output.xlsx
  → download Estimation_Output_<run_id>.xlsx
```

All stage JSON / Excel is written under the **per-run** tree  
`web_runs/<run_id>/data/output/<Phase...>/`  
(not shared `Version8/data/output/` for web runs).

Env for every stage subprocess:
- `STEEL_ENGINE_ROOT` = Version8
- `STEEL_RUN_ROOT` = web_runs/<run_id>
- `STEEL_OUTPUT_ROOT` = web_runs/<run_id>/data/output

## Commands (offline / CLI)

```powershell
python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py <run_or_input_folder>
python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py <run_root>
python Run_PY/run_phase_r2a_engineering_context.py <run_root>
python Run_PY/run_phase_r21b_semantic_interpreter.py <run_root>
python Run_PY/run_phase_r21c_engineering_fact_normalization.py <run_root>
python Run_PY/run_phase_r21d_evidence_hypothesis_engine.py <run_root>
python Run_PY/run_phase_l2_2_geometry_recovery.py <run_root>
python Run_PY/run_phase_r3_geometry_context_engine.py <run_root>
python Run_PY/run_phase_r31_engineering_relationship_engine.py <run_root>
python Run_PY/run_phase_r12a_geometry_accuracy.py <run_root>
python Run_PY/run_phase_r13_pipeline_integration.py <run_root>
python Run_PY/run_phase_vb1_production_output_completion.py <run_root>

# Web application
cd webapp
python app.py
```

## Architecture

```text
Full engineering pipeline (D.5.5)
  Upload → … → R.3 → R.3.1 → R.1.2A → R.1.3 → VB.1 Excel (run-scoped)

Next milestone
  D.5.6 — Lightsail E2E validation & cleanup
```
