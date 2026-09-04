# Development Architecture → Current Code Map

**Authority:** `PRODUCTION_TRUTH.md` (Version10 Hybrid W.19.1)  
**Scope:** Important **live production** files under `Version10/`. Historical Version1–Version9 trees are not current production.

Phases A–G below are the **original development architecture**. They are capabilities, not the current web stage IDs. The live estimator runs **14 `PRODUCTION_STAGES`** that implement those capabilities.

```
DXF upload
  → VROOT1  (A / G.1 drawing identity)
  → R1 + T1 + R.3.1   (B / C annotation & ownership)
  → R2A + R21B–D      (D / E engineering meaning + GN knowledge)
  → L.2.2 + R3 + R.1.2A  (A / F framing geometry)
  → R.1.3 + pieces + M.2  (G.5 reinforcement engineering)
  → W.6 Hybrid            (Vision overlay on G semantics)
  → VB.1                  (G.6 steel + G.7 Excel)
```

**Rule of authority (current):** Vision decides *what* bars exist (count / diameter / role). Deterministic engineering (R.1.3 → VB.1) decides *how* they are cut, spaced, hooked, weighed, and written to Excel.

Paths are relative to `Version10/` unless noted.

---

## How the 14 live stages sit on A–G

| Historical phase | Live stage(s) | Package |
|---|---|---|
| A CAD Geometry Foundation | VROOT1, L.2.2, R3, R.1.2A | `PhaseVROOT.1_*`, `PhaseL.2.2_*`, `PhaseR3_*`, `PhaseR1_2A_*` |
| B Reinforcement Drawing Understanding | R1, T1 | `PhaseR.1_*`, `PhaseT1_*` |
| C Annotation Intelligence | R1, R.3.1 | `PhaseR.1_*`, `PhaseR3.1_*` |
| D Reinforcement Engineering Interpretation | R21B, R21C, R21D | `PhaseR2.1B_*`, `PhaseR2.1C_*`, `PhaseR2.1D_*` |
| E Project Engineering Knowledge | R2A | `PhaseR.2A_*` |
| F Framing Engineering Intelligence | L.2.2, R3, R.1.2A | same as A geometry chain |
| G Reinforcement Intelligence & Steel Estimation | R.1.3, W.6, VB.1 | `PhaseR1.3_*`, `PhaseW6_*`, `PhaseVB.1_*` |
| Final Excel | VB.1 | `estimator_excel_generator.py` |

Orchestration (not a historical A–G phase): `webapp/` + `Run_PY/` + `src/config/run_context.py`.

---

## Web entry (runs the 14 stages)

| File | One-liner |
|---|---|
| `webapp/wsgi.py` | Gunicorn target `wsgi:app` for the public estimator. |
| `webapp/app.py` | Creates the Flask application. |
| `webapp/routes.py` | HTTP: `/`, `/health`, `/api/estimate`, `/api/status`, `/api/download`. |
| `webapp/config.py` | Release W.19.1, `PRODUCTION_STAGES` (14), engine root = Version10. |
| `webapp/services/estimation_service.py` | Accepts DXF uploads, one-flight job, starts the pipeline thread. |
| `webapp/services/version10_adapter.py` | Subprocess each of the 14 runners with `STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT`. |
| `webapp/services/result_registry.py` | Locates / reconstructs the finished workbook for download. |
| `webapp/services/flight_guard.py` | Allows only one live estimate at a time. |
| `src/config/run_context.py` | Isolates each run’s input/output folders so stages do not share a global `data/output`. |

---

## Phase A — CAD Geometry Foundation

**Intent:** Read DXFs, classify drawings, discover beams, recover span/section geometry.

**Live stages:** VROOT1 → (later) L.2.2 → R3 → R.1.2A

### VROOT1 — project / drawing / beam discovery

| File | One-liner |
|---|---|
| `Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py` | Web stage 1 runner. |
| `src/PhaseVROOT.1_dynamic_pipeline_initialization/phase_vroot1_orchestrator.py` | Sequences discovery → registry → 8 canonical JSON artefacts. |
| `project_discovery.py` | Finds framing, reinforcement, and general-notes DXFs in the upload folder. |
| `drawing_classifier.py` | Labels each DXF as framing / reinforcement / GN. |
| `drawing_manifest_builder.py` | Writes the drawing inventory for the run. |
| `dynamic_beam_discovery.py` | Reads framing DXF geometry/text to find beam IDs. |
| `beam_registry_builder.py` | Builds `beam_registry.json` (canonical beam list). |
| `engineering_object_initializer.py` | Creates empty engineering object shells for every discovered beam. |
| `initialization_export.py` | Writes run-scoped VROOT1 JSON under `STEEL_OUTPUT_ROOT`. |

### L.2.2 / R3 / R.1.2A — geometry recovery (also Phase F)

See Phase F.

---

## Phase B — Reinforcement Drawing Understanding

**Intent:** Find beam-detail regions, sketches, text, and stirrup geometry on the reinforcement DXF.

**Live stages:** R1, T1

| File | One-liner |
|---|---|
| `Run_PY/run_phase_r1_generalized_reinforcement_discovery.py` | Web stage 2 runner. |
| `src/PhaseR.1_generalized_reinforcement_discovery/phase_r1_orchestrator.py` | Full R.1 pass: details → annotations → groups. |
| `beam_detail_discovery.py` | Locates beam-detail regions on the reinforcement drawing. |
| `beam_detail_segmenter.py` | Splits continuous detail strips into per-beam segments. |
| `annotation_discovery.py` | Collects DXF TEXT/MTEXT that look like bar marks. |
| `dxf_text_utils.py` | Normalizes CAD text (Y12, 2-Y16, stirrup marks). |
| `reinforcement_geometry_mapper.py` | Maps annotations onto nearby CAD geometry. |
| `Run_PY/run_phase_t1_geometric_stirrup_evidence.py` | Web stage 3 runner. |
| `src/PhaseT1_geometric_stirrup_evidence/phase_t1_orchestrator.py` | Builds geometric stirrup evidence and crop envelopes for Vision. |
| `vector_stirrup_detector.py` | Detects stirrup symbols from DXF vectors (not Vision). |
| `geometry_envelope.py` | Beam crop envelopes later used by W.8 evidence PNGs. |
| `beam_extent.py` | Estimates beam length extent from CAD. |
| `type3_label_repair.py` | Repairs truncated Type-3 stirrup labels (`@100` → `@100/200/100`). |

---

## Phase C — Annotation Intelligence

**Intent:** Group annotations, own them to a beam, attach leaders/arrows, prepare engineering meaning.

**Live stages:** R1 (grouping/ownership), R.3.1 (leaders / relationships)

| File | One-liner |
|---|---|
| `reinforcement_annotation_classifier.py` | Classifies a text mark (main bar, extra, stirrup, SFR, spacer). |
| `reinforcement_group_builder.py` | Groups related marks into one reinforcement object. |
| `adaptive_association_engine.py` | Associates nearby text, geometry, and beam IDs when layout is messy. |
| `reinforcement_relationship_builder.py` | Links annotations to sketches / leaders. |
| `reinforcement_role_classifier.py` | Assigns TOP/BOTTOM/SIDE and MAIN/EXTRA roles. |
| `engineering_reinforcement_builder.py` | Emits the R.1 engineering reinforcement model JSON. |
| `Run_PY/run_phase_r31_engineering_relationship_engine.py` | Web stage 10 runner. |
| `src/PhaseR3.1_engineering_relationship_engine/phase_r31_orchestrator.py` | Builds drawing-level annotation ↔ geometry relationships. |
| `leader_discovery.py` | Finds leader lines from annotations. |
| `leader_chain_builder.py` | Chains leader segments to the pointed bar. |
| `arrow_detector.py` | Detects arrowheads that indicate ownership. |
| `physical_bar_detector.py` | Finds drawn bar lines in the detail. |
| `annotation_relationship_builder.py` | Owns each annotation to a bar/beam. |
| `relationship_graph_builder.py` | Graph of beam–annotation–geometry links. |

---

## Phase D — Reinforcement Engineering Interpretation

**Intent:** Turn classified marks into engineering meaning (role, quantity, placement, conflicts).

**Live stages:** R21B → R21C → R21D

| File | One-liner |
|---|---|
| `Run_PY/run_phase_r21b_semantic_interpreter.py` | Web stage 5; loads Version10 R.2.1B (not Version8). |
| `src/PhaseR2.1B_engineering_semantic_interpreter/phase_r21b_orchestrator.py` | Interprets R.1 marks using the semantic dictionary. |
| `semantic_interpreter.py` | Core “what does this mark mean?” engine. |
| `semantic_role_resolver.py` | Resolves bar role (top main, extra, stirrup, …). |
| `semantic_quantity_resolver.py` | Resolves count / spacing from the mark. |
| `semantic_placement_resolver.py` | Resolves where on the beam the bar sits. |
| `semantic_conflict_resolver.py` | Chooses among competing readings of the same mark. |
| `engineering_meaning_builder.py` | Writes `engineering_semantic_objects.json`. |
| `Run_PY/run_phase_r21c_engineering_fact_normalization.py` | Web stage 6. |
| `src/PhaseR2.1C_engineering_fact_normalization/phase_r21c_orchestrator.py` | Normalizes semantics into typed engineering facts. |
| `role_normalizer.py` / `placement_normalizer.py` / `intent_normalizer.py` | Canonicalise role, placement, and intent fields. |
| `engineering_fact_builder.py` | Builds `EngineeringFacts.json`. |
| `Run_PY/run_phase_r21d_evidence_hypothesis_engine.py` | Web stage 7. |
| `src/PhaseR2.1D_evidence_hypothesis_engine/phase_r21d_orchestrator.py` | Scores competing hypotheses with evidence. |
| `evidence_builder.py` | Attaches CAD/annotation evidence to each fact. |
| `hypothesis_ranker.py` | Ranks hypotheses; later T.1/Vision can confirm stirrups. |

Historical D.4 / D.4.1 / D.4.2 annotation parsers live in older trees; **live** interpretation is R.2.1B–D plus R.1.3.

---

## Phase E — Project Engineering Knowledge

**Intent:** Read General Notes: Ld tables, cover, grades, hooks, laps — project defaults with provenance.

**Live stage:** R2A

| File | One-liner |
|---|---|
| `Run_PY/run_phase_r2a_engineering_context.py` | Web stage 4; Version10 GN factory. |
| `src/PhaseR.2A_engineering_context/phase_r2a_orchestrator.py` | Parses GN DXF into Engineering Context. |
| `engineering_context_factory.py` | GN search order: uploaded `STEEL_RUN_ROOT/general_notes` → registry pointer → Version10 Benchmark_Set_2. |
| `general_notes_text_extractor.py` | Pulls all text from the GN drawing (including blocks). |
| `general_notes_classifier.py` | Splits GN text into Ld / cover / grade / hook / lap topics. |
| `development_length_parser.py` | Parses development-length tables (Ld). |
| `cover_parser.py` | Parses clear cover. |
| `steel_grade_parser.py` / `concrete_grade_parser.py` | Parses Fe415/Fe550 and concrete grade. |
| `hook_rule_parser.py` / `lap_rule_parser.py` | Parses hook multiples and lap lengths. |
| `engineering_context_builder.py` | Assembles the typed Engineering Context object. |
| `engineering_context_writer.py` | Writes run-scoped R.2A JSON used later by R.1.3 / VB.1. |

---

## Phase F — Framing Engineering Intelligence

**Intent:** Framing geometry: supports, spans, axes, engineering lengths, validated beam section.

**Live stages:** L.2.2 → R3 → R.1.2A

| File | One-liner |
|---|---|
| `Run_PY/run_phase_l2_2_geometry_recovery.py` | Web stage 8 (L.2.2, **not** historical L.2). |
| `src/PhaseL.2.2_geometry_recovery/phase_l22_orchestrator.py` | Recovers geometry registry from VROOT1 `beam_registry.json`. |
| `geometry_registry.py` | Per-beam span / depth / width / support slots. |
| `geometry_registry_engine.py` | Fills those slots from framing CAD. |
| `Run_PY/run_phase_r3_geometry_context_engine.py` | Web stage 9. |
| `src/PhaseR3_geometry_context_engine/phase_r3_orchestrator.py` | Builds `GeometryContexts.json` (axis, zones, supports). |
| `beam_axis_builder.py` | Beam centreline / axis. |
| `support_locator.py` / `support_zone_classifier.py` | Support locations and support vs span zones. |
| `span_zone_classifier.py` | Mid-span vs support shear zones (needed for stirrups). |
| `normalized_position_builder.py` | Station 0→1 along the beam. |
| `extent_evidence_builder.py` | Evidence for how far a bar extends. |
| `Run_PY/run_phase_r12a_geometry_accuracy.py` | Web stage 11. |
| `src/PhaseR1_2A_geometry_accuracy/phase_r12a_orchestrator.py` | Validates / freezes `validated_beam_geometry.json`. |
| `geometry_provider.py` | Single geometry source for downstream R.1.3. |
| `geometry_validators.py` | Span/section sanity checks. |

---

## Phase G — Reinforcement Intelligence & Steel Estimation

**Intent:** Own every bar, compute pieces / cut lengths / spacers, optionally overlay Vision semantics, then steel kg + BBS + Excel.

Split below as G.5 (engineering model), Hybrid (Vision overlay), G.6–G.7 (quantities / Excel).

### G.5 — R.1.3 engineering model (live stage 12)

| File | One-liner |
|---|---|
| `Run_PY/run_phase_r13_pipeline_integration.py` | Web stage 12; loads Version10 R.1.3 and nested packages. |
| `src/PhaseR1.3_pipeline_integration/phase_r13_orchestrator.py` | Integrates facts + geometry into production bar models. |
| `pipeline_integration_manager.py` | Dynamically loads pieces, R.1.2B, R.1.2C/D, M.2 spacers. |
| `engineering_bar_builder.py` | Builds `EngineeringBarModel` per bar from pieces/details. |
| `engineering_bar_model.py` | The production bar record (role, dia, qty, Ld, hooks, …). |
| `reinforcement_source_selector.py` | Chooses which upstream artefact is the reinforcement source. |
| `src/PhaseR1_3_reinforcement_piece_generation/piece_builder.py` | Turns details into fabricable pieces (loaded **inside** R.1.3, not a web stage). |
| `piece_geometry.py` | Piece shape (straight, crank, hook). |
| `piece_quantity.py` | Piece counts. |
| `src/PhaseV9_spacer_rule/spacer_engine.py` | M.2 spacer / cover bars from geometry + cover. |
| `r13_injector.py` | Injects spacer bars into the R.1.3 production model. |
| `src/PhaseSI.1_stirrup_improvement/phase_si1_orchestrator.py` | `StirrupImprover.compute_beam()` — zone-wise stirrup BBS rows used by VB.1 (Version10 copy). |

### Hybrid overlay — W.5 / W.8 / Vision / D.2 / W.6 (live stage 13)

Not in the original A–G list; this is the current **semantic** path. It does **not** recompute cut length, stirrup quantity, kg, or Excel.

**What Claude sees:** two PNGs per beam (`hybrid_evidence/<id>/context/selected.png` and `detail/selected.png`) and a JSON answer (`groups` + `stirrups`). See `VISION_CROP_AND_CLAUDE_RESPONSE.md`. To open a finished run in the browser: `python Version10/tools/view_hybrid_evidence.py <run_folder>`.

| File | One-liner |
|---|---|
| `Run_PY/run_phase_w6_hybrid_production_authority.py` | Web stage 13. |
| `src/PhaseW8_production_vision_evidence/generator.py` | Builds context + detail PNG evidence from T.1 envelopes. |
| `src/PhaseW5_production_hybrid_shadow/adapter.py` | Wires evidence → Claude → D.2 resolver. |
| `live_invoke.py` | Places the live Claude Vision call (fail-closed). |
| `semantic.py` | Applies Vision vs deterministic field authority. |
| `src/PhaseP2610C5_*/vision_prompt.py` | Production Vision prompt. |
| `claude_call.py` | Constrained JSON Vision call. |
| `src/PhaseP253_*/claude_vision_client.py` | Anthropic Vision client wrapper. |
| `src/PhaseP2610E2_*/live_caller.py` | Retry / fail-closed live caller used by W.5. |
| `src/PhaseP2610C3_*/claude_client.py` | `encode_png` for image parts. |
| `src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py` | Renders DXF regions to PNG. |
| `src/PhaseP2610D2_*/resolver.py` | Hybrid semantic resolution (D.2). |
| `src/PhaseW6_hybrid_production_authority/orchestrator.py` | `run_production_hybrid` — production Hybrid entry. |
| `handoff.py` | Patches count/diameter/role onto R.1.3 JSON; **protects** cut length, stirrup qty, geometry, spacers, kg, BBS. |
| `visuals.py` | Hybrid coverage / visual completeness helpers. |

### G.6 / G.7 — steel, BBS, Excel (live stage 14)

| File | One-liner |
|---|---|
| `Run_PY/run_phase_vb1_production_output_completion.py` | Web stage 14. |
| `src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py` | Steel → BBS → Excel; reads run-scoped R.1.3 (+ Hybrid patches). |
| `steel_weight_completion.py` | Cut length × unit weight → kg (uses GN Ld/cover when present). |
| `bbs_completion_engine.py` | Estimator-style BBS rows (stirrups via SI.1 `StirrupImprover`). |
| `estimator_excel_generator.py` | Writes `Production_Output/Estimation_Output.xlsx`. |
| `excel_structure_builder.py` | Workbook sheets/layout. |
| `worksheet_formatter.py` | Estimator formatting. |
| `workbook_validator.py` | Checks the workbook is a valid deliverable. |

**Final artefact:** `<run>/data/output/Production_Output/Estimation_Output.xlsx`

---

## End-to-end (current Hybrid)

```
DXF
 → VROOT1 discovery                         (A, G.1)
 → R1 annotation / groups                   (B, C)
 → T1 stirrup geometry + envelopes          (B)
 → R2A General Notes context                (E)
 → R21B–D semantic facts                    (D)
 → L.2.2 / R3 / R.1.2A framing geometry     (A, F)
 → R.3.1 leaders / ownership                (C)
 → R.1.3 bars + pieces + spacers            (G.5)
 → W.8 evidence → Claude → D.2 → W.6 handoff  (Hybrid overlay)
 → VB.1 steel / BBS / Excel                 (G.6, G.7)
```

---

## Explicitly not current production

Do not treat these as the live A–G implementation:

- `Version1/` … `Version9/` and `Steel-Beam-Estimation/`
- `Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py` (historical L.2; web uses **L.2.2**)
- `Run_PY/run_phase_r13_reinforcement_piece_generation.py` as a web stage (pieces load **inside R.1.3**)
- Benchmark/QA CLIs (`PhaseVA.2`, `PhaseVTEST*`, `PhaseVRUN.1`, `PhaseQA*`)
- Remaining files inside Vision packages that are only benchmark orchestrators (see `V10_Organize/PRODUCTION_MODULE_INDEX.md`)
