```text
1. V.ROOT.1     Beam registry + drawing manifest
2. R.1          Reinforcement annotation discovery
3. R.2A         Engineering context (Ld, cover, grades)
4. R.2.1B       Engineering semantic objects (web-capable, D.5.1)
5. R.2.1C       Engineering fact normalization (web-capable, D.5.1)
--- stop (D.5.1) ---
6. R.2.1D       Evidence / hypotheses → EngineeringFacts (later)
7. L.2.2        geometry_registry (later)
8. R.3 / R.3.1  Geometry context + leader relationships (later)
9. R.1.2A–R.1.3-PI / V.B.1  Piece pipeline + Excel (later)
```

MODEL_VERSION: 8.9.0

## Web production pipeline (D.5.1)

```text
Upload DXFs
  → Version8/data/web_runs/<run_id>/{general_notes,framing,reinforcement}/
  → VROOT1 → R1 → R2A → R.2.1B → R.2.1C
  → <run_id>/data/output/PhaseR2.1C_.../EngineeringFacts.json
```

All stage JSON is written under the **per-run** tree  
`web_runs/<run_id>/data/output/<Phase...>/`  
(not shared `Version8/data/output/` for web runs).

Env for every stage subprocess:
- `STEEL_ENGINE_ROOT` = Version8
- `STEEL_RUN_ROOT` = web_runs/<run_id>
- `STEEL_OUTPUT_ROOT` = web_runs/<run_id>/data/output

## Commands (offline / CLI)

```powershell
# Optional: set STEEL_RUN_ROOT to a web_runs folder for per-run isolation
python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py <run_or_input_folder>
python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py <run_root>
python Run_PY/run_phase_r2a_engineering_context.py <run_root>
python Run_PY/run_phase_r21b_semantic_interpreter.py <run_root>
python Run_PY/run_phase_r21c_engineering_fact_normalization.py <run_root>

# Web application
cd webapp
python app.py
```

## Architecture

```text
Engineering Semantic Engine (D.5.1)
  R.2.1B ESO → R.2.1C EngineeringFacts (run-scoped)

Later milestones
  → R.2.1D / L.2.2 → R.3 → … → V.B.1 Excel
```
