# Production Module Index

Phase: 2 — Production Boundary
Scope: mixed production / experimental packages. Files classified individually.

**Do not physically split these packages in this phase.**
Safe To Move? is a future-archive flag, not an instruction to move now.

Categories: `PRODUCTION` | `PRODUCTION_SUPPORT` | `PRODUCTION_TEST` | `EXPERIMENTAL` | `UNKNOWN`

| Package | File | Production Role | Imported By | Category | Safe To Move? |
|---|---|---|---|---|---|
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `benchmark_evaluator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `claude_vision_client.py` | Anthropic Vision client wrapper | C.5 claude_call | PRODUCTION | NO |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `interpretation_validator.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `metrics.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `phase_p253_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `pilot_candidate_loader.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `pilot_runner.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `report_builder.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `response_schema.py` | JSON extract for Vision responses | C.5 vision_contract | PRODUCTION | NO |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.253 (`PhaseP253_claude_vision_interpretation_pilot`) | `vision_prompt.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `candidate.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `claude_call.py` | call_selected_beam live Vision | E.2 live_caller | PRODUCTION | NO |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `comparison.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `config.py` | Contract constants | C.5 vision_contract | PRODUCTION_SUPPORT | NO |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `discovery.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `length_evidence.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `normalize.py` | Spec/layer/count helpers used by contract | C.5 vision_contract | PRODUCTION | NO |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `phase_p2610c5_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `sampler.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `strata.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `vision_contract.py` | Constrained Vision JSON parse/validate | C.5 claude_call; E.2 unusable() | PRODUCTION | NO |
| C.5 / P.2610C5 (`PhaseP2610C5_stratified_vision_semantic_benchmark`) | `vision_prompt.py` | Vision system/user prompts | C.5 claude_call | PRODUCTION | NO |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `claude_client.py` | encode_png for API image parts | C.5 claude_call | PRODUCTION | NO |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `comparison.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `diagnostics.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `evidence_model.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `manifest_loader.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `phase_p2610c3_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `target_anchor_validator.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `vision_benchmark.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `vision_contract.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `vision_prompt.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| C.3 / P.2610C3 (`PhaseP2610C3_visual_completeness_claude_shadow`) | `visual_completeness_gate.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `artefact_reuse.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `checkpoint.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `eligibility.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `live_caller.py` | Live retry / fail-closed Claude call | W.5 live_invoke | PRODUCTION | NO |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `pdf_report_writer.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `phase_p2610e2_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `population.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `subset_kpis.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `vision_loop.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.2 / P.2610E2 (`PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark`) | `visual_sources.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `benchmark_mapper.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `benchmark_truth_loader.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `error_analyzers.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `hybrid_runner_adapter.py` | Vision vs deterministic payloads (module also imports D.3/D.4/P.269) | W.5 semantic.resolve_semantic | PRODUCTION | NO |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `kpis.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `pdf_report_writer.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `phase_p2610e1_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `population_discovery.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `provenance_analyzer.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| E.1 / P.2610E1 (`PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark`) | `vision_artifact_loader.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `config.py` | Authority constants | D.2 resolver | PRODUCTION_SUPPORT | NO |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `discovery.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `hybrid_authority_contract.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `matching.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `normalize.py` | Semantic field normalize | W.5 comparison | PRODUCTION | NO |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `phase_p2610d1_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `resolver.py` | resolve_group field authority | D.2 resolver | PRODUCTION | NO |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `vision_normalizer.py` | extract_vision_payload / extract_deterministic_groups | E.2 live_caller; E.1 adapter | PRODUCTION | NO |
| D.1 / P.2610D1 (`PhaseP2610D1_vision_semantic_contract_hybrid_foundation`) | `vision_validator.py` | Duplicate flags | D.2 resolver | PRODUCTION | NO |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `audit.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `canonical.py` | Canonical hybrid fields | D.2 resolver | PRODUCTION | NO |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `config.py` | D.2 constants | D.2 resolver | PRODUCTION_SUPPORT | NO |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `discovery.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `matching.py` | Conservative group/stirrup match | D.2 resolver | PRODUCTION | NO |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `metrics.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `phase_p2610d2_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `resolver.py` | resolve_hybrid_beam | W.5 semantic | PRODUCTION | NO |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| D.2 / P.2610D2 (`PhaseP2610D2_shadow_hybrid_semantic_resolver`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `cropper.py` | render_crop via M.1 dxf_renderer | W.8 generator | PRODUCTION | NO |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `dataset.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `evaluator.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `inventory.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `phase_p2610a_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `quality.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `region_builder.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `title_localizer.py` | choose_mark / collect_beam_titles | W.8 generator | PRODUCTION | NO |
| P.2610A (`PhaseP2610A_beam_region_crop_audit`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `completeness.py` | evaluate_completeness | W.8 generator | PRODUCTION | NO |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `envelope.py` | build_adaptive_regions | W.8 generator | PRODUCTION | NO |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `evaluator.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `evidence.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `phase_p2610b_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610B (`PhaseP2610B_adaptive_beam_detail_crop`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `border.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `candidates.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `config.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `gates.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `geometry.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `orientation.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `phase_p2610b2_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `pipeline.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `population.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `quality.py` | validate_render | W.8 generator | PRODUCTION | NO |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `recovery.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `render_session.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `timing.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610B2 (`PhaseP2610B2_render_quality_directional_recovery`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `anti_hardcoding.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `config.py` | SOURCE_B1 | W.8 generator | PRODUCTION | NO |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `inventory.py` | _candidate | W.8 generator | PRODUCTION | NO |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `phase_p2610c1c2_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `policy.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `regression.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `report.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `selector.py` | select_for_type | W.8 generator | PRODUCTION | NO |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| P.2610C1C2 (`PhaseP2610C1C2_evidence_inventory_candidate_selection`) | `unit_tests.py` | Package tests | local unit/regression | PRODUCTION_TEST | REVIEW_REQUIRED |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `__init__.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `__main__.py` | W.5 CLI entry | manual CLI | PRODUCTION_SUPPORT | REVIEW_REQUIRED |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `adapter.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `catalog.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `comparison.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `config.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `cost.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `live_invoke.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `paths.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `semantic.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `settings.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `unit_tests.py` | W.5 unit tests | pytest / package tests | PRODUCTION_TEST | NO |
| W.5 (`PhaseW5_production_hybrid_shadow`) | `visual_sources.py` | W.5 production hybrid loop | W.6 orchestrator | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `__init__.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `__main__.py` | W.6 CLI entry | manual CLI | PRODUCTION_SUPPORT | REVIEW_REQUIRED |
| W.6 (`PhaseW6_hybrid_production_authority`) | `config.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `coverage.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `handoff.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `observability.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `orchestrator.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `resolution_trace.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `unit_tests.py` | W.6 unit tests | pytest / package tests | PRODUCTION_TEST | NO |
| W.6 (`PhaseW6_hybrid_production_authority`) | `visuals.py` | W.6 production hybrid authority | web HYBRID stage | PRODUCTION | NO |
| W.8 (`PhaseW8_production_vision_evidence`) | `__init__.py` | W.8 evidence package | W.6 visuals | PRODUCTION | NO |
| W.8 (`PhaseW8_production_vision_evidence`) | `config.py` | W.8 evidence package | W.6 visuals | PRODUCTION | NO |
| W.8 (`PhaseW8_production_vision_evidence`) | `generator.py` | W.8 evidence package | W.6 visuals | PRODUCTION | NO |
| W.8 (`PhaseW8_production_vision_evidence`) | `package.py` | W.8 evidence package | W.6 visuals | PRODUCTION | NO |
| W.8 (`PhaseW8_production_vision_evidence`) | `unit_tests.py` | W.8 unit tests | package tests | PRODUCTION_TEST | NO |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `__init__.py` | Package init | imports | PRODUCTION_SUPPORT | NO |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `annotation_builder.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `beam_cropper.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `dataset_exporter.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `dataset_validator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `dxf_renderer.py` | DXF region PNG render | P.2610A cropper | PRODUCTION | NO |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `manifest_builder.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `metadata_builder.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `phase_m1_orchestrator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `pipeline_reader.py` | Not on traced W.5/W.6/W.8 import graph | unknown / mixed-package remainder | UNKNOWN | NO — do not move |
| M.1 (`PhaseM.1_engineering_vision_dataset`) | `preview_generator.py` | Benchmark / trial / report / orchestrator in mixed package | CLI / lab, not PRODUCTION_STAGES | EXPERIMENTAL | NO — package stays; file not split in Phase 2 |

## Category counts (listed packages only)

- PRODUCTION: **48**
- PRODUCTION_SUPPORT: **17**
- PRODUCTION_TEST: **24**
- EXPERIMENTAL: **59**
- UNKNOWN: **71**

## Transitive note (do not archive)

`PhaseP2610E1_.../hybrid_runner_adapter.py` imports at module load:

- `PhaseP2610D3_hybrid_engineering_binding_compatibility.hybrid_binding_engine`
- `PhaseP2610D4_...beam_calculator`
- `PhaseP269_reinforcement_group_interpretation.extractor`

W.5 `semantic.py` only *calls* payload builders + D.2 `resolve_hybrid_beam`, but importing E.1 still loads D.3 / D.4 / P.269.
Those packages remain **REVIEW_REQUIRED / do not archive** until the E.1 import surface is narrowed in a later phase.
