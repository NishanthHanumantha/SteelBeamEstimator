```text
1.  V.ROOT.1     Drawing / beam discovery
2.  R.1          Reinforcement annotation discovery
3.  T.1          Geometric stirrup evidence
4.  R.2A         Engineering context (Ld, cover, grades)
5.  R.2.1B       Engineering semantic objects
6.  R.2.1C       Engineering fact normalization
7.  R.2.1D       Evidence / hypotheses → EngineeringFacts
8.  L.2.2        geometry_registry
9.  R.3          Geometry context
10. R.3.1        Drawing relationships
11. R.1.2A       Geometry catalog (web: catalog-only)
12. R.1.3        EngineeringBarModel + pieces + M.2 spacers
13. W.6 / HYBRID Vision semantics + D.2 resolve + production handoff
14. V.B.1        Steel / BBS / Excel
```

**Current production:** Version10 Hybrid, `APP_RELEASE=W.19.1`.  
Canonical stage list: `Version10/webapp/config.py` `PRODUCTION_STAGES` (exactly 14).  
Architecture source of truth: `PRODUCTION_TRUTH.md`.

MODEL_VERSION in older comments may still say 8.9.5. That is a **historical engineering freeze label**, not the current web architecture.

## Web / RunContext pipeline

```text
Upload DXFs
  → Version10/data/web_runs/<run_id>/{general_notes,framing,reinforcement}/
  → VROOT1 → R1 → T1 → R2A → R.2.1B → R.2.1C → R.2.1D → L.2.2 → R.3
  → R.3.1 → R.1.2A → R.1.3 → W.6 (HYBRID) → VB.1
  → <run_id>/data/output/Production_Output/Estimation_Output.xlsx
```

Hybrid (inside W.6): W.8 evidence → Claude Vision → D.2 semantic resolve → W.6 handoff onto R.1.3.  
Deterministic engine remains authority for geometry, spacers, lengths, Ld, pieces, kg, BBS, Excel.

Env for every stage subprocess:
- `STEEL_ENGINE_ROOT` = Version10
- `STEEL_RUN_ROOT` = web_runs/<run_id>
- `STEEL_OUTPUT_ROOT` = web_runs/<run_id>/data/output

Historical 8.9.5 packaging (not current production):  
`Steel-Beam-Estimation/docs/Production_Architecture_8.9.5.md`

## Commands (offline / CLI)

```powershell
python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py <run_or_input_folder>
python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py <run_root>
python Run_PY/run_phase_t1_geometric_stirrup_evidence.py <run_root>
python Run_PY/run_phase_r2a_engineering_context.py <run_root>
python Run_PY/run_phase_r21b_semantic_interpreter.py <run_root>
python Run_PY/run_phase_r21c_engineering_fact_normalization.py <run_root>
python Run_PY/run_phase_r21d_evidence_hypothesis_engine.py <run_root>
python Run_PY/run_phase_l2_2_geometry_recovery.py <run_root>
python Run_PY/run_phase_r3_geometry_context_engine.py <run_root>
python Run_PY/run_phase_r31_engineering_relationship_engine.py <run_root>
python Run_PY/run_phase_r12a_geometry_accuracy.py <run_root>
python Run_PY/run_phase_r13_pipeline_integration.py <run_root>
python Run_PY/run_phase_w6_hybrid_production_authority.py <run_root>
python Run_PY/run_phase_vb1_production_output_completion.py <run_root>

cd webapp
python app.py
```
