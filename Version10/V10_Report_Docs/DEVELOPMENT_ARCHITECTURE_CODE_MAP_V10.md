# Development Architecture & Code Map

**Source:** [DEVELOPMENT_ARCHITECTURE_CODE_MAP_V10.pdf](DEVELOPMENT_ARCHITECTURE_CODE_MAP_V10.pdf)  
**Authority:** [`PRODUCTION_TRUTH.md`](../../PRODUCTION_TRUTH.md) — Version10 Hybrid W.19.1  
**Scope:** Live production files under `Version10/`. Version1–Version9 are not current production.

**How to open a file:** every code row uses the **full path from the repo root**. In Cursor, Ctrl+click the path. You can also paste it into Explorer under `C:\Users\nishanth.h\SteelBeamEstimator\`.

---

## Contents

1. [Architecture at a glance](#1-architecture-at-a-glance)
2. [Web entry (runs the 14 stages)](#2-web-entry-runs-the-14-stages)
3. [Phase A — CAD Geometry Foundation](#3-phase-a--cad-geometry-foundation)
4. [Phase B — Reinforcement Drawing Understanding](#4-phase-b--reinforcement-drawing-understanding)
5. [Phase C — Annotation Intelligence](#5-phase-c--annotation-intelligence)
6. [Phase D — Reinforcement Engineering Interpretation](#6-phase-d--reinforcement-engineering-interpretation)
7. [Phase E — Project Engineering Knowledge](#7-phase-e--project-engineering-knowledge)
8. [Phase F — Framing Engineering Intelligence](#8-phase-f--framing-engineering-intelligence)
9. [Phase G — Reinforcement Intelligence & Steel Estimation](#9-phase-g--reinforcement-intelligence--steel-estimation)
10. [Claude call, prompt, and answer](#claude-call-prompt-and-answer)
11. [End-to-end Hybrid pipeline](#10-end-to-end-current-hybrid-pipeline)
12. [Not current production](#11-explicitly-not-current-production)
13. [Quick reference — live stage sequence](#12-quick-reference--live-stage-sequence)

---

## 1. Architecture at a glance

Original development phases (capabilities, **not** web stage IDs):

```
Phase A  CAD Geometry Foundation
  ↓
Phase B  Reinforcement Drawing Understanding
  ↓
Phase C  Annotation Intelligence
  ↓
Phase D  Reinforcement Engineering Interpretation
  ↓
Phase E  Project Engineering Knowledge
  ↓
Phase F  Framing Engineering Intelligence
  ↓
Phase G  Reinforcement Intelligence & Steel Estimation
  ↓
Final    Beam Steel Excel Sheet
```

**Current production flow**

```
DXF upload
  → VROOT1
  → R1 + T1 + R.3.1
  → R2A + R21B–D
  → L.2.2 + R3 + R.1.2A
  → R.1.3 + pieces + M.2
  → W.6 Hybrid
  → VB.1
  → Steel + BBS + Excel
```

**Rule of authority:** Vision decides *what* bars exist (count / diameter / role). Deterministic engineering (R.1.3 → VB.1) decides *how* they are cut, spaced, hooked, weighed, and written to Excel.

The live estimator runs **14 `PRODUCTION_STAGES`**. Orchestration lives in `webapp/` + `Run_PY/` + [`Version10/src/config/run_context.py`](../src/config/run_context.py).

### Historical A–G → live 14-stage mapping

| Historical phase | Live stage(s) | Package folder |
|---|---|---|
| A — CAD Geometry Foundation | VROOT1, L.2.2, R3, R.1.2A | [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/) · [`PhaseL.2.2_geometry_recovery/`](../src/PhaseL.2.2_geometry_recovery/) · [`PhaseR3_geometry_context_engine/`](../src/PhaseR3_geometry_context_engine/) · [`PhaseR1_2A_geometry_accuracy/`](../src/PhaseR1_2A_geometry_accuracy/) |
| B — Reinforcement Drawing Understanding | R1, T1 | [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/`](../src/PhaseR.1_generalized_reinforcement_discovery/) · [`PhaseT1_geometric_stirrup_evidence/`](../src/PhaseT1_geometric_stirrup_evidence/) |
| C — Annotation Intelligence | R1, R.3.1 | [`PhaseR.1_generalized_reinforcement_discovery/`](../src/PhaseR.1_generalized_reinforcement_discovery/) · [`PhaseR3.1_engineering_relationship_engine/`](../src/PhaseR3.1_engineering_relationship_engine/) |
| D — Reinforcement Engineering Interpretation | R21B, R21C, R21D | [`PhaseR2.1B_engineering_semantic_interpreter/`](../src/PhaseR2.1B_engineering_semantic_interpreter/) · [`PhaseR2.1C_engineering_fact_normalization/`](../src/PhaseR2.1C_engineering_fact_normalization/) · [`PhaseR2.1D_evidence_hypothesis_engine/`](../src/PhaseR2.1D_evidence_hypothesis_engine/) |
| E — Project Engineering Knowledge | R2A | [`Version10/src/PhaseR.2A_engineering_context/`](../src/PhaseR.2A_engineering_context/) |
| F — Framing Engineering Intelligence | L.2.2, R3, R.1.2A | Same geometry chain as A |
| G — Reinforcement Intelligence & Steel Estimation | R.1.3, W.6, VB.1 | [`PhaseR1.3_pipeline_integration/`](../src/PhaseR1.3_pipeline_integration/) · [`PhaseW6_hybrid_production_authority/`](../src/PhaseW6_hybrid_production_authority/) · [`PhaseVB.1_production_output_completion/`](../src/PhaseVB.1_production_output_completion/) |
| Final Excel | VB.1 | [`Version10/src/PhaseVB.1_production_output_completion/estimator_excel_generator.py`](../src/PhaseVB.1_production_output_completion/estimator_excel_generator.py) |

---

## 2. Web entry (runs the 14 stages)

| Navigate to | What it does |
|---|---|
| [`Version10/webapp/wsgi.py`](../webapp/wsgi.py) | Gunicorn target `wsgi:app` for the public estimator. |
| [`Version10/webapp/app.py`](../webapp/app.py) | Creates the Flask application. |
| [`Version10/webapp/routes.py`](../webapp/routes.py) | HTTP: `/`, `/health`, `/api/estimate`, `/api/status`, `/api/download`. |
| [`Version10/webapp/config.py`](../webapp/config.py) | Release W.19.1, `PRODUCTION_STAGES` (14), engine root = Version10. |
| [`Version10/webapp/services/estimation_service.py`](../webapp/services/estimation_service.py) | Accepts DXF uploads, one-flight job, starts the pipeline thread. |
| [`Version10/webapp/services/version10_adapter.py`](../webapp/services/version10_adapter.py) | Subprocess each of the 14 runners with `STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT`. |
| [`Version10/webapp/services/result_registry.py`](../webapp/services/result_registry.py) | Locates / reconstructs the finished workbook for download. |
| [`Version10/webapp/services/flight_guard.py`](../webapp/services/flight_guard.py) | Allows only one live estimate at a time. |
| [`Version10/src/config/run_context.py`](../src/config/run_context.py) | Isolates each run’s input/output folders so stages do not share a global `data/output`. |

---

## 3. Phase A — CAD Geometry Foundation

**Intent:** Read DXFs, classify drawings, discover beams, and recover span/section geometry.

**Live stages:** VROOT1 → (later) L.2.2 → R3 → R.1.2A

### VROOT1 — project / drawing / beam discovery

**Folder:** [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py`](../Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py) | Web stage 1 runner. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/phase_vroot1_orchestrator.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/phase_vroot1_orchestrator.py) | Sequences discovery → registry → 8 canonical JSON artefacts. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/project_discovery.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/project_discovery.py) | Finds framing, reinforcement, and general-notes DXFs in the upload folder. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/drawing_classifier.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/drawing_classifier.py) | Labels each DXF as framing / reinforcement / GN. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/drawing_manifest_builder.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/drawing_manifest_builder.py) | Writes the drawing inventory for the run. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/dynamic_beam_discovery.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/dynamic_beam_discovery.py) | Reads framing DXF geometry/text to find beam IDs. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry_builder.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry_builder.py) | Builds `beam_registry.json` (canonical beam list). |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/engineering_object_initializer.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/engineering_object_initializer.py) | Creates empty engineering object shells for every discovered beam. |
| [`Version10/src/PhaseVROOT.1_dynamic_pipeline_initialization/initialization_export.py`](../src/PhaseVROOT.1_dynamic_pipeline_initialization/initialization_export.py) | Writes run-scoped VROOT1 JSON under `STEEL_OUTPUT_ROOT`. |

### L.2.2 / R3 / R.1.2A — geometry recovery

See [Phase F](#8-phase-f--framing-engineering-intelligence).

---

## 4. Phase B — Reinforcement Drawing Understanding

**Intent:** Find beam-detail regions, sketches, text, and stirrup geometry on the reinforcement DXF.

**Live stages:** R1 → T1

### R1 — reinforcement discovery

**Folder:** [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/`](../src/PhaseR.1_generalized_reinforcement_discovery/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r1_generalized_reinforcement_discovery.py`](../Run_PY/run_phase_r1_generalized_reinforcement_discovery.py) | Web stage 2 runner. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/phase_r1_orchestrator.py`](../src/PhaseR.1_generalized_reinforcement_discovery/phase_r1_orchestrator.py) | Full R.1 pass: details, annotations, groups. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/beam_detail_discovery.py`](../src/PhaseR.1_generalized_reinforcement_discovery/beam_detail_discovery.py) | Locates beam-detail regions on the reinforcement drawing. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/beam_detail_segmenter.py`](../src/PhaseR.1_generalized_reinforcement_discovery/beam_detail_segmenter.py) | Splits continuous detail strips into per-beam segments. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/annotation_discovery.py`](../src/PhaseR.1_generalized_reinforcement_discovery/annotation_discovery.py) | Collects DXF TEXT/MTEXT that look like bar marks. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/dxf_text_utils.py`](../src/PhaseR.1_generalized_reinforcement_discovery/dxf_text_utils.py) | Normalizes CAD text (Y12, 2-Y16, stirrup marks). |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_geometry_mapper.py`](../src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_geometry_mapper.py) | Maps annotations onto nearby CAD geometry. |

### T1 — geometric stirrup evidence

**Folder:** [`Version10/src/PhaseT1_geometric_stirrup_evidence/`](../src/PhaseT1_geometric_stirrup_evidence/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_t1_geometric_stirrup_evidence.py`](../Run_PY/run_phase_t1_geometric_stirrup_evidence.py) | Web stage 3 runner. |
| [`Version10/src/PhaseT1_geometric_stirrup_evidence/phase_t1_orchestrator.py`](../src/PhaseT1_geometric_stirrup_evidence/phase_t1_orchestrator.py) | Builds geometric stirrup evidence and crop envelopes for Vision. |
| [`Version10/src/PhaseT1_geometric_stirrup_evidence/vector_stirrup_detector.py`](../src/PhaseT1_geometric_stirrup_evidence/vector_stirrup_detector.py) | Detects stirrup symbols from DXF vectors (not Vision). |
| [`Version10/src/PhaseT1_geometric_stirrup_evidence/geometry_envelope.py`](../src/PhaseT1_geometric_stirrup_evidence/geometry_envelope.py) | Beam crop envelopes later used by W.8 evidence PNGs. |
| [`Version10/src/PhaseT1_geometric_stirrup_evidence/beam_extent.py`](../src/PhaseT1_geometric_stirrup_evidence/beam_extent.py) | Estimates beam length extent from CAD. |
| [`Version10/src/PhaseT1_geometric_stirrup_evidence/type3_label_repair.py`](../src/PhaseT1_geometric_stirrup_evidence/type3_label_repair.py) | Repairs truncated Type-3 stirrup labels (`@100` → `@100/200/100`). |

---

## 5. Phase C — Annotation Intelligence

**Intent:** Group annotations, own them to a beam, attach leaders/arrows, and prepare engineering meaning.

**Live stages:** R1 (grouping / ownership) + R.3.1 (leaders / relationships)

### R1 — grouping / ownership (same package as Phase B)

**Folder:** [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/`](../src/PhaseR.1_generalized_reinforcement_discovery/)

| Navigate to | What it does |
|---|---|
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotation_classifier.py`](../src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotation_classifier.py) | Classifies a text mark (main bar, extra, stirrup, SFR, spacer). |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_group_builder.py`](../src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_group_builder.py) | Groups related marks into one reinforcement object. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py`](../src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py) | Associates nearby text, geometry, and beam IDs when layout is messy. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_relationship_builder.py`](../src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_relationship_builder.py) | Links annotations to sketches / leaders. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_role_classifier.py`](../src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_role_classifier.py) | Assigns TOP/BOTTOM/SIDE and MAIN/EXTRA roles. |
| [`Version10/src/PhaseR.1_generalized_reinforcement_discovery/engineering_reinforcement_builder.py`](../src/PhaseR.1_generalized_reinforcement_discovery/engineering_reinforcement_builder.py) | Emits the R.1 engineering reinforcement model JSON. |

### R.3.1 — leaders / relationships

**Folder:** [`Version10/src/PhaseR3.1_engineering_relationship_engine/`](../src/PhaseR3.1_engineering_relationship_engine/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r31_engineering_relationship_engine.py`](../Run_PY/run_phase_r31_engineering_relationship_engine.py) | Web stage 10 runner. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/phase_r31_orchestrator.py`](../src/PhaseR3.1_engineering_relationship_engine/phase_r31_orchestrator.py) | Builds drawing-level annotation ↔ geometry relationships. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/leader_discovery.py`](../src/PhaseR3.1_engineering_relationship_engine/leader_discovery.py) | Finds leader lines from annotations. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/leader_chain_builder.py`](../src/PhaseR3.1_engineering_relationship_engine/leader_chain_builder.py) | Chains leader segments to the pointed bar. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/arrow_detector.py`](../src/PhaseR3.1_engineering_relationship_engine/arrow_detector.py) | Detects arrowheads that indicate ownership. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/physical_bar_detector.py`](../src/PhaseR3.1_engineering_relationship_engine/physical_bar_detector.py) | Finds drawn bar lines in the detail. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/annotation_relationship_builder.py`](../src/PhaseR3.1_engineering_relationship_engine/annotation_relationship_builder.py) | Owns each annotation to a bar / beam. |
| [`Version10/src/PhaseR3.1_engineering_relationship_engine/relationship_graph_builder.py`](../src/PhaseR3.1_engineering_relationship_engine/relationship_graph_builder.py) | Graph of beam–annotation–geometry links. |

---

## 6. Phase D — Reinforcement Engineering Interpretation

**Intent:** Turn classified marks into engineering meaning: role, quantity, placement, and conflicts.

**Live stages:** R21B → R21C → R21D

Historical D.4 / D.4.1 / D.4.2 annotation parsers live in older trees. **Live** interpretation is R.2.1B–D plus R.1.3.

### R21B — semantic interpreter

**Folder:** [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/`](../src/PhaseR2.1B_engineering_semantic_interpreter/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r21b_semantic_interpreter.py`](../Run_PY/run_phase_r21b_semantic_interpreter.py) | Web stage 5; loads Version10 R.2.1B (not Version8). |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/phase_r21b_orchestrator.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/phase_r21b_orchestrator.py) | Interprets R.1 marks using the semantic dictionary. |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/semantic_interpreter.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/semantic_interpreter.py) | Core “what does this mark mean?” engine. |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/semantic_role_resolver.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/semantic_role_resolver.py) | Resolves bar role (top main, extra, stirrup, …). |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/semantic_quantity_resolver.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/semantic_quantity_resolver.py) | Resolves count / spacing from the mark. |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/semantic_placement_resolver.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/semantic_placement_resolver.py) | Resolves where on the beam the bar sits. |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/semantic_conflict_resolver.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/semantic_conflict_resolver.py) | Chooses among competing readings of the same mark. |
| [`Version10/src/PhaseR2.1B_engineering_semantic_interpreter/engineering_meaning_builder.py`](../src/PhaseR2.1B_engineering_semantic_interpreter/engineering_meaning_builder.py) | Writes `engineering_semantic_objects.json`. |

### R21C — engineering fact normalization

**Folder:** [`Version10/src/PhaseR2.1C_engineering_fact_normalization/`](../src/PhaseR2.1C_engineering_fact_normalization/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r21c_engineering_fact_normalization.py`](../Run_PY/run_phase_r21c_engineering_fact_normalization.py) | Web stage 6. |
| [`Version10/src/PhaseR2.1C_engineering_fact_normalization/phase_r21c_orchestrator.py`](../src/PhaseR2.1C_engineering_fact_normalization/phase_r21c_orchestrator.py) | Normalizes semantics into typed engineering facts. |
| [`Version10/src/PhaseR2.1C_engineering_fact_normalization/role_normalizer.py`](../src/PhaseR2.1C_engineering_fact_normalization/role_normalizer.py) | Canonicalise role fields. |
| [`Version10/src/PhaseR2.1C_engineering_fact_normalization/placement_normalizer.py`](../src/PhaseR2.1C_engineering_fact_normalization/placement_normalizer.py) | Canonicalise placement fields. |
| [`Version10/src/PhaseR2.1C_engineering_fact_normalization/intent_normalizer.py`](../src/PhaseR2.1C_engineering_fact_normalization/intent_normalizer.py) | Canonicalise intent fields. |
| [`Version10/src/PhaseR2.1C_engineering_fact_normalization/engineering_fact_builder.py`](../src/PhaseR2.1C_engineering_fact_normalization/engineering_fact_builder.py) | Builds `EngineeringFacts.json`. |

### R21D — evidence / hypothesis engine

**Folder:** [`Version10/src/PhaseR2.1D_evidence_hypothesis_engine/`](../src/PhaseR2.1D_evidence_hypothesis_engine/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r21d_evidence_hypothesis_engine.py`](../Run_PY/run_phase_r21d_evidence_hypothesis_engine.py) | Web stage 7. |
| [`Version10/src/PhaseR2.1D_evidence_hypothesis_engine/phase_r21d_orchestrator.py`](../src/PhaseR2.1D_evidence_hypothesis_engine/phase_r21d_orchestrator.py) | Scores competing hypotheses with evidence. |
| [`Version10/src/PhaseR2.1D_evidence_hypothesis_engine/evidence_builder.py`](../src/PhaseR2.1D_evidence_hypothesis_engine/evidence_builder.py) | Attaches CAD / annotation evidence to each fact. |
| [`Version10/src/PhaseR2.1D_evidence_hypothesis_engine/hypothesis_ranker.py`](../src/PhaseR2.1D_evidence_hypothesis_engine/hypothesis_ranker.py) | Ranks hypotheses; later T.1 / Vision can confirm stirrups. |

---

## 7. Phase E — Project Engineering Knowledge

**Intent:** Read General Notes for Ld tables, cover, grades, hooks, and laps — project defaults with provenance.

**Live stage:** R2A  
**Folder:** [`Version10/src/PhaseR.2A_engineering_context/`](../src/PhaseR.2A_engineering_context/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r2a_engineering_context.py`](../Run_PY/run_phase_r2a_engineering_context.py) | Web stage 4; Version10 GN factory. |
| [`Version10/src/PhaseR.2A_engineering_context/phase_r2a_orchestrator.py`](../src/PhaseR.2A_engineering_context/phase_r2a_orchestrator.py) | Parses GN DXF into Engineering Context. |
| [`Version10/src/PhaseR.2A_engineering_context/engineering_context_factory.py`](../src/PhaseR.2A_engineering_context/engineering_context_factory.py) | GN search order: uploaded `STEEL_RUN_ROOT/general_notes` → registry pointer → Version10 Benchmark_Set_2. |
| [`Version10/src/PhaseR.2A_engineering_context/general_notes_text_extractor.py`](../src/PhaseR.2A_engineering_context/general_notes_text_extractor.py) | Pulls all text from the GN drawing (including blocks). |
| [`Version10/src/PhaseR.2A_engineering_context/general_notes_classifier.py`](../src/PhaseR.2A_engineering_context/general_notes_classifier.py) | Splits GN text into Ld / cover / grade / hook / lap topics. |
| [`Version10/src/PhaseR.2A_engineering_context/development_length_parser.py`](../src/PhaseR.2A_engineering_context/development_length_parser.py) | Parses development-length tables (Ld). |
| [`Version10/src/PhaseR.2A_engineering_context/cover_parser.py`](../src/PhaseR.2A_engineering_context/cover_parser.py) | Parses clear cover. |
| [`Version10/src/PhaseR.2A_engineering_context/steel_grade_parser.py`](../src/PhaseR.2A_engineering_context/steel_grade_parser.py) | Parses Fe415 / Fe550. |
| [`Version10/src/PhaseR.2A_engineering_context/concrete_grade_parser.py`](../src/PhaseR.2A_engineering_context/concrete_grade_parser.py) | Parses concrete grade. |
| [`Version10/src/PhaseR.2A_engineering_context/hook_rule_parser.py`](../src/PhaseR.2A_engineering_context/hook_rule_parser.py) | Parses hook multiples. |
| [`Version10/src/PhaseR.2A_engineering_context/lap_rule_parser.py`](../src/PhaseR.2A_engineering_context/lap_rule_parser.py) | Parses lap lengths. |
| [`Version10/src/PhaseR.2A_engineering_context/engineering_context_builder.py`](../src/PhaseR.2A_engineering_context/engineering_context_builder.py) | Assembles the typed Engineering Context object. |
| [`Version10/src/PhaseR.2A_engineering_context/engineering_context_writer.py`](../src/PhaseR.2A_engineering_context/engineering_context_writer.py) | Writes run-scoped R.2A JSON used later by R.1.3 / VB.1. |

---

## 8. Phase F — Framing Engineering Intelligence

**Intent:** Recover supports, spans, axes, engineering lengths, and a validated beam section.

**Live stages:** L.2.2 → R3 → R.1.2A

### L.2.2 — geometry recovery

**Folder:** [`Version10/src/PhaseL.2.2_geometry_recovery/`](../src/PhaseL.2.2_geometry_recovery/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_l2_2_geometry_recovery.py`](../Run_PY/run_phase_l2_2_geometry_recovery.py) | Web stage 8 (L.2.2, **not** historical L.2). |
| [`Version10/src/PhaseL.2.2_geometry_recovery/phase_l22_orchestrator.py`](../src/PhaseL.2.2_geometry_recovery/phase_l22_orchestrator.py) | Recovers geometry registry from VROOT1 `beam_registry.json`. |
| [`Version10/src/PhaseL.2.2_geometry_recovery/geometry_registry.py`](../src/PhaseL.2.2_geometry_recovery/geometry_registry.py) | Per-beam span / depth / width / support slots. |
| [`Version10/src/PhaseL.2.2_geometry_recovery/geometry_registry_engine.py`](../src/PhaseL.2.2_geometry_recovery/geometry_registry_engine.py) | Fills those slots from framing CAD. |

### R3 — geometry context

**Folder:** [`Version10/src/PhaseR3_geometry_context_engine/`](../src/PhaseR3_geometry_context_engine/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r3_geometry_context_engine.py`](../Run_PY/run_phase_r3_geometry_context_engine.py) | Web stage 9. |
| [`Version10/src/PhaseR3_geometry_context_engine/phase_r3_orchestrator.py`](../src/PhaseR3_geometry_context_engine/phase_r3_orchestrator.py) | Builds `GeometryContexts.json` (axis, zones, supports). |
| [`Version10/src/PhaseR3_geometry_context_engine/beam_axis_builder.py`](../src/PhaseR3_geometry_context_engine/beam_axis_builder.py) | Beam centreline / axis. |
| [`Version10/src/PhaseR3_geometry_context_engine/support_locator.py`](../src/PhaseR3_geometry_context_engine/support_locator.py) | Support locations. |
| [`Version10/src/PhaseR3_geometry_context_engine/support_zone_classifier.py`](../src/PhaseR3_geometry_context_engine/support_zone_classifier.py) | Support vs span zones. |
| [`Version10/src/PhaseR3_geometry_context_engine/span_zone_classifier.py`](../src/PhaseR3_geometry_context_engine/span_zone_classifier.py) | Mid-span vs support shear zones (needed for stirrups). |
| [`Version10/src/PhaseR3_geometry_context_engine/normalized_position_builder.py`](../src/PhaseR3_geometry_context_engine/normalized_position_builder.py) | Station 0→1 along the beam. |
| [`Version10/src/PhaseR3_geometry_context_engine/extent_evidence_builder.py`](../src/PhaseR3_geometry_context_engine/extent_evidence_builder.py) | Evidence for how far a bar extends. |

### R.1.2A — geometry accuracy

**Folder:** [`Version10/src/PhaseR1_2A_geometry_accuracy/`](../src/PhaseR1_2A_geometry_accuracy/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r12a_geometry_accuracy.py`](../Run_PY/run_phase_r12a_geometry_accuracy.py) | Web stage 11. |
| [`Version10/src/PhaseR1_2A_geometry_accuracy/phase_r12a_orchestrator.py`](../src/PhaseR1_2A_geometry_accuracy/phase_r12a_orchestrator.py) | Validates / freezes `validated_beam_geometry.json`. |
| [`Version10/src/PhaseR1_2A_geometry_accuracy/geometry_provider.py`](../src/PhaseR1_2A_geometry_accuracy/geometry_provider.py) | Single geometry source for downstream R.1.3. |
| [`Version10/src/PhaseR1_2A_geometry_accuracy/geometry_validators.py`](../src/PhaseR1_2A_geometry_accuracy/geometry_validators.py) | Span / section sanity checks. |

---

## 9. Phase G — Reinforcement Intelligence & Steel Estimation

**Intent:** Own every bar, compute pieces / cut lengths / spacers, overlay Vision semantics when needed, then produce steel kg + BBS + Excel.

Split as G.5 (engineering model), Hybrid (Vision overlay), G.6–G.7 (quantities / Excel).

### G.5 — R.1.3 engineering model (live stage 12)

**Folder:** [`Version10/src/PhaseR1.3_pipeline_integration/`](../src/PhaseR1.3_pipeline_integration/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_r13_pipeline_integration.py`](../Run_PY/run_phase_r13_pipeline_integration.py) | Web stage 12; loads Version10 R.1.3 and nested packages. |
| [`Version10/src/PhaseR1.3_pipeline_integration/phase_r13_orchestrator.py`](../src/PhaseR1.3_pipeline_integration/phase_r13_orchestrator.py) | Integrates facts + geometry into production bar models. |
| [`Version10/src/PhaseR1.3_pipeline_integration/pipeline_integration_manager.py`](../src/PhaseR1.3_pipeline_integration/pipeline_integration_manager.py) | Dynamically loads pieces, R.1.2B, R.1.2C/D, and M.2 spacers. |
| [`Version10/src/PhaseR1.3_pipeline_integration/engineering_bar_builder.py`](../src/PhaseR1.3_pipeline_integration/engineering_bar_builder.py) | Builds `EngineeringBarModel` per bar from pieces / details. |
| [`Version10/src/PhaseR1.3_pipeline_integration/engineering_bar_model.py`](../src/PhaseR1.3_pipeline_integration/engineering_bar_model.py) | Production bar record: role, dia, qty, Ld, hooks, … |
| [`Version10/src/PhaseR1.3_pipeline_integration/reinforcement_source_selector.py`](../src/PhaseR1.3_pipeline_integration/reinforcement_source_selector.py) | Chooses which upstream artefact is the reinforcement source. |
| [`Version10/src/PhaseR1_3_reinforcement_piece_generation/piece_builder.py`](../src/PhaseR1_3_reinforcement_piece_generation/piece_builder.py) | Turns details into fabricable pieces (loaded **inside** R.1.3, not a web stage). |
| [`Version10/src/PhaseR1_3_reinforcement_piece_generation/piece_geometry.py`](../src/PhaseR1_3_reinforcement_piece_generation/piece_geometry.py) | Piece shape: straight, crank, hook. |
| [`Version10/src/PhaseR1_3_reinforcement_piece_generation/piece_quantity.py`](../src/PhaseR1_3_reinforcement_piece_generation/piece_quantity.py) | Piece counts. |
| [`Version10/src/PhaseV9_spacer_rule/spacer_engine.py`](../src/PhaseV9_spacer_rule/spacer_engine.py) | M.2 spacer / cover bars from geometry + cover. |
| [`Version10/src/PhaseV9_spacer_rule/r13_injector.py`](../src/PhaseV9_spacer_rule/r13_injector.py) | Injects spacer bars into the R.1.3 production model. |
| [`Version10/src/PhaseSI.1_stirrup_improvement/phase_si1_orchestrator.py`](../src/PhaseSI.1_stirrup_improvement/phase_si1_orchestrator.py) | `StirrupImprover.compute_beam()` — zone-wise stirrup BBS rows used by VB.1. |

### Hybrid overlay — W.5 / W.8 / Vision / D.2 / W.6 (live stage 13)

This is the current **semantic** path. It does **not** recompute cut length, stirrup quantity, kg, or Excel.

What Claude sees: two PNGs per beam (`hybrid_evidence/<id>/context/selected.png` and `detail/selected.png`) and a JSON answer (`groups` + `stirrups`). See [`VISION_CROP_AND_CLAUDE_RESPONSE.md`](../../VISION_CROP_AND_CLAUDE_RESPONSE.md). To open a finished run in the browser: `python Version10/tools/view_hybrid_evidence.py <run_folder>`.

Jump to the live Claude path: [Claude call, prompt, and answer](#claude-call-prompt-and-answer).

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_w6_hybrid_production_authority.py`](../Run_PY/run_phase_w6_hybrid_production_authority.py) | Web stage 13. |
| [`Version10/src/PhaseW8_production_vision_evidence/generator.py`](../src/PhaseW8_production_vision_evidence/generator.py) | Builds context + detail PNG evidence from T.1 envelopes. |
| [`Version10/src/PhaseW5_production_hybrid_shadow/adapter.py`](../src/PhaseW5_production_hybrid_shadow/adapter.py) | Wires evidence → Claude → D.2 resolver. |
| [`Version10/src/PhaseW5_production_hybrid_shadow/live_invoke.py`](../src/PhaseW5_production_hybrid_shadow/live_invoke.py) | Places the live Claude Vision call (fail-closed). |
| [`Version10/src/PhaseW5_production_hybrid_shadow/semantic.py`](../src/PhaseW5_production_hybrid_shadow/semantic.py) | Applies Vision vs deterministic field authority. |
| [`Version10/src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_prompt.py`](../src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_prompt.py) | Production Vision prompt. |
| [`Version10/src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py`](../src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py) | Constrained JSON Vision call. |
| [`Version10/src/PhaseP253_claude_vision_interpretation_pilot/claude_vision_client.py`](../src/PhaseP253_claude_vision_interpretation_pilot/claude_vision_client.py) | Anthropic Vision client wrapper. |
| [`Version10/src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/live_caller.py`](../src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/live_caller.py) | Retry / fail-closed live caller used by W.5. |
| [`Version10/src/PhaseP2610C3_visual_completeness_claude_shadow/claude_client.py`](../src/PhaseP2610C3_visual_completeness_claude_shadow/claude_client.py) | `encode_png` for image parts. |
| [`Version10/src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py`](../src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py) | Renders DXF regions to PNG. |
| [`Version10/src/PhaseP2610D2_shadow_hybrid_semantic_resolver/resolver.py`](../src/PhaseP2610D2_shadow_hybrid_semantic_resolver/resolver.py) | Hybrid semantic resolution (D.2). |
| [`Version10/src/PhaseW6_hybrid_production_authority/orchestrator.py`](../src/PhaseW6_hybrid_production_authority/orchestrator.py) | `run_production_hybrid` — production Hybrid entry. |
| [`Version10/src/PhaseW6_hybrid_production_authority/handoff.py`](../src/PhaseW6_hybrid_production_authority/handoff.py) | Patches count / diameter / role onto R.1.3 JSON; **protects** cut length, stirrup qty, geometry, spacers, kg, BBS. |
| [`Version10/src/PhaseW6_hybrid_production_authority/visuals.py`](../src/PhaseW6_hybrid_production_authority/visuals.py) | Hybrid coverage / visual completeness helpers. |
| [`Version10/tools/view_hybrid_evidence.py`](../tools/view_hybrid_evidence.py) | Local gallery of context/detail crops from a finished run. |

---

## Claude call, prompt, and answer

Live path (one beam): **W.8 crops → W.5 invoke → C.5 prompt + two PNGs → Anthropic API → JSON parse → D.2 resolve → W.6 handoff**.

```
W.6 orchestrator
    → W.8 generator          two PNGs (context + detail)
    → W.5 adapter             per-beam live call
         → live_invoke.call_shadow_beam
         → E.2 live_caller.call_live_beam
         → C.5 claude_call.call_selected_beam
              system  = vision_prompt.SYSTEM_PROMPT
              user    = vision_prompt.build_user_prompt(beam_id)
              images  = encode_png(context) + encode_png(detail)
              API     = ClaudeClient.generate_vision_response
                        → anthropic.messages.create
    ← raw_text
         → C.5 vision_contract.parse_and_validate
         → W.5 semantic.resolve_semantic  (D.2)
    → W.6 handoff.apply_production_handoff   patches count / diameter / role only
```

### 1. Where Claude is called

| Step | Navigate to | Function | What happens |
|---|---|---|---|
| Production stage 13 | [`Version10/src/PhaseW6_hybrid_production_authority/orchestrator.py`](../src/PhaseW6_hybrid_production_authority/orchestrator.py) | `run_production_hybrid` | Starts Hybrid; calls W.5 shadow then W.6 handoff. |
| Per-beam invoke | [`Version10/src/PhaseW5_production_hybrid_shadow/adapter.py`](../src/PhaseW5_production_hybrid_shadow/adapter.py) | `_invoke` → `call_shadow_beam` | One live Vision call per beam (timeout / fail-closed). |
| W.5 wrapper | [`Version10/src/PhaseW5_production_hybrid_shadow/live_invoke.py`](../src/PhaseW5_production_hybrid_shadow/live_invoke.py) | `call_shadow_beam` | Forwards context + detail paths to E.2. |
| Retry wrapper | [`Version10/src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/live_caller.py`](../src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/live_caller.py) | `call_live_beam` | Retries API / schema failures; never invents a result. |
| Assemble request | [`Version10/src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py`](../src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py) | `call_selected_beam` | Builds prompt, encodes 2 PNGs, calls Vision, parses JSON. |
| Anthropic wrapper | [`Version10/src/PhaseP253_claude_vision_interpretation_pilot/claude_vision_client.py`](../src/PhaseP253_claude_vision_interpretation_pilot/claude_vision_client.py) | `call_claude_vision` | Loads client; returns `raw_text` + audit (no API key). |
| **Actual API call** | [`Version10/src/llm/claude_client.py`](../src/llm/claude_client.py) | `ClaudeClient.generate_vision_response` | `content[0]` image, `content[1]` image, `content[2]` text; `system` = C.5 system prompt. Hits `messages.create`. |
| Model / temperature | [`Version10/src/llm/claude_config.py`](../src/llm/claude_config.py) | `MODEL_NAME`, `TEMPERATURE` | Production model `claude-sonnet-4-5`, temperature `0`. |

Payload on the wire:

```
system     = C.5 SYSTEM_PROMPT
messages   = [{ role: user, content: [
                 { type: image, source: base64 CONTEXT png },
                 { type: image, source: base64 DETAIL png },
                 { type: text,  text: user prompt with TARGET BEAM ID + JSON schema }
             ]}]
```

### 2. How prompts are given

| Piece | Navigate to | Function | What is sent |
|---|---|---|---|
| System rules | [`Version10/src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_prompt.py`](../src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_prompt.py) | `SYSTEM_PROMPT` | Image 1 = CONTEXT, Image 2 = DETAIL; interpret only the target beam; return **only JSON**; do not compute kg / BBS / cut length. |
| User prompt | same file | `build_user_prompt` | `TARGET BEAM ID`, image provenance, JSON schema (`groups` + `stirrups`). |
| Crop windows | [`Version10/src/PhaseP2610B_adaptive_beam_detail_crop/envelope.py`](../src/PhaseP2610B_adaptive_beam_detail_crop/envelope.py) | envelope builder | Adaptive context vs detail extents on the DXF. |
| Render PNGs | [`Version10/src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py`](../src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py) | DXF → PNG | Renders those windows. |
| Write evidence | [`Version10/src/PhaseW8_production_vision_evidence/generator.py`](../src/PhaseW8_production_vision_evidence/generator.py) | generator | `hybrid_evidence/<BEAM>/context/selected.png` and `detail/selected.png`. |
| Pick files | [`Version10/src/PhaseW5_production_hybrid_shadow/visual_sources.py`](../src/PhaseW5_production_hybrid_shadow/visual_sources.py) | `discover_visuals` | Prefers W.8 pair, else T.1, else W.6 crop. |
| Base64 encode | [`Version10/src/PhaseP2610C3_visual_completeness_claude_shadow/claude_client.py`](../src/PhaseP2610C3_visual_completeness_claude_shadow/claude_client.py) | `encode_png` | `{ media_type, data_base64 }` for each image. |

`n_images` is always **2** on the live C.5 path.

### 3. How answers are sent back

Claude returns **one JSON object** as text. Production never uses markdown from the model.

| Step | Navigate to | Function | What happens |
|---|---|---|---|
| Pull text from SDK | [`Version10/src/llm/response_parser.py`](../src/llm/response_parser.py) | `extract_text` | Reads `response.content` into `raw_text`. |
| Parse + schema check | [`Version10/src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_contract.py`](../src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_contract.py) | `parse_and_validate` | JSON must match schema; `target_beam_id` must match. Else **fail-closed**. |
| Normalize Vision | [`Version10/src/PhaseP2610D1_vision_semantic_contract_hybrid_foundation/vision_normalizer.py`](../src/PhaseP2610D1_vision_semantic_contract_hybrid_foundation/vision_normalizer.py) | `extract_vision_payload` | Typed Vision payload (`groups`, `stirrups`). |
| Vision vs R.1.3 | [`Version10/src/PhaseW5_production_hybrid_shadow/semantic.py`](../src/PhaseW5_production_hybrid_shadow/semantic.py) | `resolve_semantic` | Builds Vision + deterministic payloads. |
| D.2 resolver | [`Version10/src/PhaseP2610D2_shadow_hybrid_semantic_resolver/resolver.py`](../src/PhaseP2610D2_shadow_hybrid_semantic_resolver/resolver.py) | `resolve_hybrid_beam` | Vision preferred for count / diameter / role when usable. |
| Patch R.1.3 | [`Version10/src/PhaseW6_hybrid_production_authority/handoff.py`](../src/PhaseW6_hybrid_production_authority/handoff.py) | `apply_production_handoff` | Patches those fields onto R.1.3 JSON; **protects** cut length, stirrup qty, geometry, spacers, kg, BBS. |

Expected JSON shape (from the C.5 schema): `target_beam_id`, `target_identified`, `groups[]` (layer, spec, bar_count, role_hypothesis), `stirrups[]` (spec only), `ambiguities`.

If JSON is bad, API fails, or the beam ID does not match: Hybrid is **unusable** for that beam and deterministic R.1.3 is kept.

### Where the answer is stored (per run, not in git)

| What | Path under the run folder |
|---|---|
| Crops sent | `data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence/<BEAM>/{context,detail}/selected.png` |
| Per-beam parse / Hybrid | `data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json` → `beams[]` (`parsed`, `hybrid_interpretation`) |
| What was patched | `data/output/PhaseW6_hybrid_semantic_resolution/hybrid_handoff_ledger.json` |

---

### G.6 / G.7 — steel, BBS, Excel (live stage 14)

**Folder:** [`Version10/src/PhaseVB.1_production_output_completion/`](../src/PhaseVB.1_production_output_completion/)

| Navigate to | What it does |
|---|---|
| [`Version10/Run_PY/run_phase_vb1_production_output_completion.py`](../Run_PY/run_phase_vb1_production_output_completion.py) | Web stage 14. |
| [`Version10/src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py`](../src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py) | Steel → BBS → Excel; reads run-scoped R.1.3 (+ Hybrid patches). |
| [`Version10/src/PhaseVB.1_production_output_completion/steel_weight_completion.py`](../src/PhaseVB.1_production_output_completion/steel_weight_completion.py) | Cut length × unit weight → kg (uses GN Ld / cover when present). |
| [`Version10/src/PhaseVB.1_production_output_completion/bbs_completion_engine.py`](../src/PhaseVB.1_production_output_completion/bbs_completion_engine.py) | Estimator-style BBS rows (stirrups via SI.1 `StirrupImprover`). |
| [`Version10/src/PhaseVB.1_production_output_completion/estimator_excel_generator.py`](../src/PhaseVB.1_production_output_completion/estimator_excel_generator.py) | Writes `Production_Output/Estimation_Output.xlsx`. |
| [`Version10/src/PhaseVB.1_production_output_completion/excel_structure_builder.py`](../src/PhaseVB.1_production_output_completion/excel_structure_builder.py) | Workbook sheets / layout. |
| [`Version10/src/PhaseVB.1_production_output_completion/worksheet_formatter.py`](../src/PhaseVB.1_production_output_completion/worksheet_formatter.py) | Estimator formatting. |
| [`Version10/src/PhaseVB.1_production_output_completion/workbook_validator.py`](../src/PhaseVB.1_production_output_completion/workbook_validator.py) | Checks the workbook is a valid deliverable. |

**Final artefact:** `<run>/data/output/Production_Output/Estimation_Output.xlsx`

---

## 10. End-to-end current Hybrid pipeline

1. DXF upload  
2. **VROOT1** — discovery (A, G.1)  
3. **R1** — annotation / groups (B, C)  
4. **T1** — stirrup geometry + envelopes (B)  
5. **R2A** — General Notes context (E)  
6. **R21B–D** — semantic facts (D)  
7. **L.2.2 / R3 / R.1.2A** — framing geometry (A, F)  
8. **R.3.1** — leaders / ownership (C)  
9. **R.1.3** — bars + pieces + spacers (G.5)  
10. **W.8 evidence → Claude → D.2 → W.6 handoff** (Hybrid overlay)  
11. **VB.1** — steel / BBS / Excel (G.6, G.7)

---

## 11. Explicitly not current production

Do not treat these as the live A–G implementation:

- `Version1/` … `Version9/` and `Steel-Beam-Estimation/`
- [`Version10/Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py`](../Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py) — historical L.2; web uses **L.2.2**
- [`Version10/Run_PY/run_phase_r13_reinforcement_piece_generation.py`](../Run_PY/run_phase_r13_reinforcement_piece_generation.py) — not a web stage; pieces load **inside R.1.3**
- Benchmark / QA CLIs: `PhaseVA.2`, `PhaseVTEST*`, `PhaseVRUN.1`, `PhaseQA*`
- Remaining files inside Vision packages that are only benchmark orchestrators — see [`V10_Organize/PRODUCTION_MODULE_INDEX.md`](../../V10_Organize/PRODUCTION_MODULE_INDEX.md)

---

## 12. Quick reference — live stage sequence

| Web stage | Live ID | Runner (navigate here) | Primary responsibility | Historical |
|---|---|---|---|---|
| 1 | VROOT1 | [`Version10/Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py`](../Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py) | Project / drawing / beam discovery | A / G.1 |
| 2 | R1 | [`Version10/Run_PY/run_phase_r1_generalized_reinforcement_discovery.py`](../Run_PY/run_phase_r1_generalized_reinforcement_discovery.py) | Reinforcement discovery + annotation grouping | B / C |
| 3 | T1 | [`Version10/Run_PY/run_phase_t1_geometric_stirrup_evidence.py`](../Run_PY/run_phase_t1_geometric_stirrup_evidence.py) | Geometric stirrup evidence + envelopes | B |
| 4 | R2A | [`Version10/Run_PY/run_phase_r2a_engineering_context.py`](../Run_PY/run_phase_r2a_engineering_context.py) | General Notes engineering context | E |
| 5 | R21B | [`Version10/Run_PY/run_phase_r21b_semantic_interpreter.py`](../Run_PY/run_phase_r21b_semantic_interpreter.py) | Semantic interpretation | D |
| 6 | R21C | [`Version10/Run_PY/run_phase_r21c_engineering_fact_normalization.py`](../Run_PY/run_phase_r21c_engineering_fact_normalization.py) | Engineering fact normalization | D |
| 7 | R21D | [`Version10/Run_PY/run_phase_r21d_evidence_hypothesis_engine.py`](../Run_PY/run_phase_r21d_evidence_hypothesis_engine.py) | Evidence / hypothesis ranking | D |
| 8 | L.2.2 | [`Version10/Run_PY/run_phase_l2_2_geometry_recovery.py`](../Run_PY/run_phase_l2_2_geometry_recovery.py) | Geometry recovery | A / F |
| 9 | R3 | [`Version10/Run_PY/run_phase_r3_geometry_context_engine.py`](../Run_PY/run_phase_r3_geometry_context_engine.py) | Geometry context / supports / zones | A / F |
| 10 | R.3.1 | [`Version10/Run_PY/run_phase_r31_engineering_relationship_engine.py`](../Run_PY/run_phase_r31_engineering_relationship_engine.py) | Leaders / annotation relationships | C |
| 11 | R.1.2A | [`Version10/Run_PY/run_phase_r12a_geometry_accuracy.py`](../Run_PY/run_phase_r12a_geometry_accuracy.py) | Geometry accuracy / validation | A / F |
| 12 | R.1.3 | [`Version10/Run_PY/run_phase_r13_pipeline_integration.py`](../Run_PY/run_phase_r13_pipeline_integration.py) | Production bar model + pieces + spacers | G.5 |
| 13 | W.6 | [`Version10/Run_PY/run_phase_w6_hybrid_production_authority.py`](../Run_PY/run_phase_w6_hybrid_production_authority.py) | Vision semantic overlay / authority handoff | Hybrid |
| 14 | VB.1 | [`Version10/Run_PY/run_phase_vb1_production_output_completion.py`](../Run_PY/run_phase_vb1_production_output_completion.py) | Steel weight + BBS + Excel | G.6 / G.7 |
