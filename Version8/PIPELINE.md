```text
1. V.ROOT.1     Beam registry + drawing manifest
2. R.2A         Engineering context (Ld, cover, grades)
3. R.3 / R.3.1  Geometry context + leader relationships
4. R.1          Reinforcement annotation discovery
5. R.1.2A       GeometryProvider — per-beam spans
6. R.1.2C       Engineering Intent Resolution
7. R.1.2D       Reinforcement Detailing
8. R.1.3        Reinforcement Piece Generation (manufacturing members)
9. R.1.3-PI     EngineeringBarModels from Pieces (+ R.1.2B consolidation)
10. V.B.1       Steel weight + BBS + Estimation_Output.xlsx
11. R.1.4       Production Accuracy Benchmark (official workbook interpretation)
12. R.1.5       Engineering Error Intelligence (clustered issues + backlog)
13. R.1.6       Engineering Rule Synthesis (deterministic rule library)
14. R.1.6.1     Estimator Stirrup Computation Engine
15. R.1.6.2     RULE-012 Mandatory Stirrup Coverage Validation
16. R.1.6.3     Annotation Discovery Analysis & Engineering Review
```

## Commands

```powershell
python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py
python Run_PY/run_phase_r2a_engineering_context.py
python Run_PY/run_phase_r3_geometry_context_engine.py
python Run_PY/run_phase_r31_engineering_relationship_engine.py
python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py
python Run_PY/run_phase_r12a_geometry_accuracy.py
python Run_PY/run_phase_r12c_engineering_intent_resolution.py
python Run_PY/run_phase_r12d_reinforcement_detailing.py
python Run_PY/run_phase_r13_reinforcement_piece_generation.py
python Run_PY/run_phase_r13_pipeline_integration.py
python Run_PY/run_phase_vb1_production_output_completion.py
python Run_PY/run_phase_r14_production_accuracy_benchmark.py
python Run_PY/run_phase_r15_engineering_error_intelligence.py
python Run_PY/run_phase_r16_engineering_rule_synthesis.py
python Run_PY/run_phase_r161_estimator_stirrup_computation.py
python Run_PY/run_phase_r162_stirrup_coverage_validation.py
python Run_PY/run_phase_r163_annotation_discovery_analysis.py
```

## Architecture

```text
Engineering Facts
  → Engineering Intent
  → Reinforcement Detail
  → Reinforcement Piece
  → EngineeringBar
  → Steel
  → BBS

Official Estimator Workbook
  → Workbook Interpretation Engine
  → Official Engineering Model
  → Production Snapshot + Benchmark KPIs / Root Cause
  → Engineering Error Intelligence (issues, rankings, backlog)
  → Engineering Rule Library (gap resolution + roadmap)
  → Estimator Stirrup Computation (equal zones + GN hooks)
  → RULE-012 Mandatory Stirrup Coverage Validation (detection only)
  → R.1.6.3 Annotation Discovery Analysis (engineering review package)
```
