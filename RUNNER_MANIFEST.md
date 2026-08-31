# Runner Manifest

Phase: 2 — Production Boundary
Source: `Version10/Run_PY/run_phase_*.py` (**105** files).

Web-invoked = listed in `Version10/webapp/config.py` `PRODUCTION_STAGES`.
Do **not** archive a runner merely because it is not web-invoked.

| Runner | Stage | Web Invoked? | Production? | Role | Safe To Archive? | Confidence |
|---|---|---|---|---|---|---|
| `run_phase_vroot1_dynamic_pipeline_initialization.py` | VROOT1 | Yes | Yes | Web stage 1 — drawing/beam discovery | NO | High |
| `run_phase_r1_generalized_reinforcement_discovery.py` | R1 | Yes | Yes | Web stage 2 — DXF reinforcement discovery (loads Version10 src) | NO | High |
| `run_phase_t1_geometric_stirrup_evidence.py` | T1 | Yes | Yes | Web stage 3 — geometric stirrup evidence | NO | High |
| `run_phase_r2a_engineering_context.py` | R2A | Yes | Yes | Web stage 4 — GN context; loads Version8 PhaseR.2A source | NO | High |
| `run_phase_r21b_semantic_interpreter.py` | R21B | Yes | Yes | Web stage 5 — loads Version8 PhaseR2.1B source | NO | High |
| `run_phase_r21c_engineering_fact_normalization.py` | R21C | Yes | Yes | Web stage 6 — loads Version10 PhaseR2.1C | NO | High |
| `run_phase_r21d_evidence_hypothesis_engine.py` | R21D | Yes | Yes | Web stage 7 | NO | High |
| `run_phase_l2_2_geometry_recovery.py` | L22 | Yes | Yes | Web stage 8 — loads Version10 PhaseL.2.2 | NO | High |
| `run_phase_r3_geometry_context_engine.py` | R3 | Yes | Yes | Web stage 9 | NO | High |
| `run_phase_r31_engineering_relationship_engine.py` | R31 | Yes | Yes | Web stage 10 | NO | High |
| `run_phase_r12a_geometry_accuracy.py` | R12A | Yes | Yes | Web stage 11 | NO | High |
| `run_phase_r13_pipeline_integration.py` | R13 | Yes | Yes | Web stage 12 — bar models, pieces, spacers | NO | High |
| `run_phase_w6_hybrid_production_authority.py` | HYBRID | Yes | Yes | Web stage 13 — Vision + D.2 + W.6 handoff | NO | High |
| `run_phase_vb1_production_output_completion.py` | VB1 | Yes | Yes | Web stage 14 — steel / BBS / Excel (loads Version10 PhaseVB.1) | NO | High |
| `run_phase_l2_engineering_reinforcement_interpretation.py` | — | No | No | Historical / experimental engineering CLI | REVIEW_REQUIRED | Medium |
| `run_phase_m1_vision_dataset_generator.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p21_leader_tip_chain_analysis.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p22_leader_chain_evidence.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p23_1_controlled_engineering_recompute.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p23_controlled_production_gate.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p24_fourth_set_bar_failure_audit.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2501_evidence_spatial_sanity.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2502_top_reinforcement_trace.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2503_accepted_owned_geometry.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2504_accepted_owned_geometry_rendering.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p250_beam_evidence_crop_qa.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2510_new_stirrup_safety.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2511_evidence_enrichment.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p251_quantity_intent_schema.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2521_crop_readability_refinement.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2522_render_safe_annotation_bounds.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2523_target_beam_visual_completeness.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p252_vision_candidate_set.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p253_claude_vision_interpretation_pilot.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p254_semantic_reinforcement_vision_benchmark.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p255_controlled_shadow_integration.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p256_controlled_field_level_vision_experiment.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p257_unseen_drawing_controlled_vision_validation.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p258_controlled_vision_field_repair.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p259_beam_safe_arbitration.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2610a_beam_region_crop_audit.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610b1_population_generalization.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2610b2_render_quality_directional_recovery.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610b3_target_anchor_geometry_context_recovery.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2610b_adaptive_beam_detail_crop.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610c1c2_evidence_inventory_candidate_selection.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610c3_visual_completeness_claude_shadow.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610c4_shadow_truth_reconciliation.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p2610c5_stratified_vision_semantic_benchmark.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610d1_vision_semantic_contract_hybrid_foundation.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610d2_shadow_hybrid_semantic_resolver.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610d3_hybrid_engineering_binding.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610d4_shadow_hybrid_engineering_calculation_accuracy_benchmark.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610e1_fifth_set_hybrid_accuracy_benchmark.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610e2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.py` | — | No | No | CLI of mixed package with production-imported modules. Do not archive package. | NO | High |
| `run_phase_p2610e3_second_to_sixth_full_population_live_vision_hybrid_accuracy_benchmark.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p261_stratified_vision_candidate_recovery.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p262_selective_vision_candidate_gate.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p263_longitudinal_aware_gate.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p264_selective_role_gap_gate.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p265_spatial_context_longitudinal.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p266_semantic_longitudinal_resolver.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p267_live_semantic_arbitration.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p268_evidence_conflict_arbitration.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p269_reinforcement_group_interpretation.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_p26_vision_candidate_recovery_pilot.py` | — | No | No | Experimental / trial Vision-CAD CLI | REVIEW_REQUIRED | Medium |
| `run_phase_qa2a_ground_truth_benchmark.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa2b0_pipeline_integration.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa2b1_production_regeneration.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa2b2_accuracy_report.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa30_overall_accuracy_report.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa30_unseen.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa30_unseen_benchmark.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa31_pipeline_diagnostics.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa32_ground_truth_crop_validation.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa33_ownership_explainability.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa34_ownership_competition_validation.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa41_dropped_entity_recovery_audit.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa42_candidate_search_envelope_recovery.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_qa43_p2_leader_recovery.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_r11a_annotation_coverage.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r11b_production_integration.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r12b_engineeringbar_consolidation.py` | R1.2B nested | No | No | CLI for consolidator; R.1.3 loads package in-process | REVIEW_REQUIRED | High |
| `run_phase_r12c_engineering_intent_resolution.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r12d_reinforcement_detailing.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r13_reinforcement_piece_generation.py` | R1.3 nested | No | No | CLI for piece generation; R.1.3 loads package in-process | REVIEW_REQUIRED | High |
| `run_phase_r14_integrity_validation.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r14_production_accuracy_benchmark.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r15_engineering_error_intelligence.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r161_estimator_stirrup_computation.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r162_stirrup_coverage_validation.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r163_annotation_discovery_analysis.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r16_engineering_rule_synthesis.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r201_notation_inventory.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r20_mtext_recovery.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r21a_semantic_dictionary.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_r2b_engineering_context_consumption.py` | — | No | No | Engineering CLI not in PRODUCTION_STAGES | REVIEW_REQUIRED | Medium |
| `run_phase_si0_stirrup_recovery.py` | — | No | No | Historical / experimental engineering CLI | REVIEW_REQUIRED | Medium |
| `run_phase_si1_stirrup_improvement.py` | — | No | No | Historical / experimental engineering CLI | REVIEW_REQUIRED | Medium |
| `run_phase_track1_visual_chain.py` | — | No | No | Historical / experimental engineering CLI | REVIEW_REQUIRED | Medium |
| `run_phase_va2_benchmark_set2_validation.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_vroot1_verify.py` | VROOT1 | No | No | Verification helper; hardcoded Version8 Benchmark_Set_2 paths | REVIEW_REQUIRED | High |
| `run_phase_vrun1_pipeline_reexecution.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_vtest32_estimator_comparison_engine.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |
| `run_phase_vtest3_benchmark_set3_validation.py` | — | No | No | Benchmark / QA / re-execution CLI | REVIEW_REQUIRED | High |

## Counts

- Total: **105**
- Web production stages: **14**
- Remaining: **91**

## Remaining 91 breakdown

| Family | Count | Classification | Safe To Archive? |
|---|---|---|---|
| Mixed-package CLIs (P.253 / W.8 deps / C.5 / D.1–D.4 / E.1–E.2 / M.1) | 14 | CLI of mixed production packages | **NO** (package must remain) |
| Nested piece/consolidator/verify CLIs | 3 | Production-support CLI, not web stages | REVIEW_REQUIRED |
| QA / VA / VTEST / VRUN | 18 | Benchmark / validation | REVIEW_REQUIRED |
| Other `run_phase_p*` | 37 | Experimental Vision-CAD | REVIEW_REQUIRED |
| Extra `run_phase_r*` | 15 | Engineering CLI not web-invoked | REVIEW_REQUIRED |
| SI / L.2 (not L.2.2) / track1 | 4 | Historical / experimental | REVIEW_REQUIRED |
| Other | 0 | Unclassified | REVIEW_REQUIRED |

Checksum remaining: 91 (must be 91).

## Policy

Phase 2 does **not** archive the 91 non-web runners.
Production R.2A and R.2.1B runners still execute **Version8** `src` packages — see `PRODUCTION_BOUNDARY_MANIFEST.md`.
