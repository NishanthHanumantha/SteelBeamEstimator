# Steel Beam Estimator — Version 7

> **FROZEN (2026-07-17) at MODEL_VERSION 8.3.0.**  
> Active development continues in **`Version8/`**. See `VERSION_FREEZE.md`.

Historical development branch continuing from **Version 6** (frozen at MODEL_VERSION 6.6.3 / Phase V.A.1.1).

**Version 6 is frozen. Version 7 is frozen.** Do not add new features here.

## Production Pipeline (MODEL_VERSION 6.6.3 baseline)

| Stage | Package | Status |
|---|---|---|
| Phase L.2 | `PhaseL.2 - engineering_reinforcement_interpretation` | PASS |
| Phase SI.0 | `PhaseSI.0_stirrup_recovery` | PASS |
| Phase SI.1 | `PhaseSI.1_stirrup_improvement` | PASS |
| Phase L.2.2 | `PhaseL.2.2_geometry_recovery` | PASS |
| Phase L.2.1 | `PhaseL.2.1 - engineering_feature_extraction` | PASS |
| Phase L.3 | `PhaseL.3_beam_pattern_recognition` | PASS |
| Phase V.B.1 | `PhaseVB.1_production_output_completion` | PASS |
| Validation | `PhaseVA.1.1_end_to_end_validation_recompute` | 7/7 PASS |

## Benchmark Set 1 KPIs (inherited from Version 6)

- Steel weight: 1,038.97 kg
- Workbook match: 49.31%
- Stirrup coverage: 13/18 beams
- BBS rows: 126
- Pipeline: 6/6 stages PASS

## Benchmark Set 2

Place new drawing inputs in `data/Benchmark_Set_2/`.

## What is included

Imported from Version5 (runtime essentials only — no generated artifacts):

| Area | Purpose |
|------|---------|
| `src/` | Full E→I pipeline plus QA, audit, and recovery packages |
| `config/` | Framing, general notes, estimator rules |
| `Run_PY/` | Phase E/F runners and QA/J validation runners |
| `data/framing/` | Framing plan + reinforcement DXF inputs |
| `data/general_notes/` | General Notes DXF input |
| `data/Excel_Presentation_Format/` | Excel export template |
| `data/Estimator_Validated_Output/` | Ground-truth workbook for QA runners |

**Not copied** (regenerate locally):

- All `data/output/**` artifacts (phase E–I, QA dashboards, recovery registries, etc.)
- Debug DXF files, temp run logs, `__pycache__`

## Setup

```powershell
pip install -r requirements.txt
cd Version7
$env:PYTHONPATH="."
```

## Run core pipeline

```powershell
python Run_PY/run_phase_e_general_notes.py
python Run_PY/run_phase_f_framing.py
```

Regenerates outputs under `data/output/phase_e/` through `data/output/phase_i/`.

## Run QA and recovery tooling

After the core pipeline completes, run validation and recovery runners as needed:

```powershell
python Run_PY/run_accuracy_dashboard.py
python Run_PY/run_engineering_analysis.py
python Run_PY/run_reinforcement_discovery_analysis.py
python Run_PY/run_duplicate_legitimacy_audit.py
python Run_PY/run_engineering_recovery.py
python Run_PY/run_engineering_recovery_expansion.py
python Run_PY/run_engineering_calculation_integration.py
python Run_PY/run_engineering_recovery_validation.py
python Run_PY/run_engineering_quantity_validation.py
python Run_PY/run_engineering_recovery_statistics_validation.py
```

## Run Engineering Intent Reconstruction (Phase K.1)

After recovery phases complete:

```powershell
python Run_PY/run_engineering_intent.py
```

Outputs under `data/output/engineering_intent/`.

## Run Engineering Intent Resolution (Phase K.1.1 — MODEL_VERSION 6.0.1)

After K.1 intent reconstruction completes:

```powershell
python Run_PY/run_engineering_intent_resolution.py
```

Resolves overlapping intents into deterministic Engineering Decisions.
Priority table: `config/engineering_intent_priority.yaml`
Outputs under `data/output/engineering_intent_resolution/`.

## Run Engineering Decision Validation (Phase K.2.1 — MODEL_VERSION 6.2.0)

After K.1.1 and before K.2 execution:

```powershell
python Run_PY/run_phase_k2_1_engineering_decision_validation.py
```

Validates every Engineering Decision (read-only). Only VALID decisions may enter K.2.

- Source: `src/PhaseK.2.1 - engineering_decision_validation/`
- Config: `config/engineering_decision_validation.yaml`
- Outputs: `data/output/PhaseK.2.1 - engineering_decision_validation/`

When `enable: false`, Phase K.2 behaves exactly as MODEL_VERSION 6.1.0.

## Run Engineering Decision Execution (Phase K.2 — MODEL_VERSION 6.1.0)

After K.2.1 validation (or with validation `enable: false` for 6.1.0 passthrough):

```powershell
python Run_PY/run_phase_k2_engineering_decision_execution.py
```

Only VALIDATED decisions from `validated_decision_registry.json` may execute when K.2.1 is enabled.
Engineering Decisions become the authoritative execution objects for the production pipeline.
Existing calculation/steel/BBS/Excel engines are reused — formulas are not modified.

- Source: `src/PhaseK.2 - engineering_decision_execution/`
- Config: `config/engineering_decision_execution.yaml`
- Outputs: `data/output/PhaseK.2 - engineering_decision_execution/`

## LLM Provider (Phase LLM.1 — MODEL_VERSION 6.1.0)

Anthropic Claude is the only supported LLM. All requests go through `src/llm/`.

```powershell
# Validate Claude integration
$env:PYTHONPATH="."
python validate_claude_integration.py

# Quick connectivity test
python test_claude_api.py
```

API key: `ANTHROPIC_API_KEY` in repo-root `.env` at `C:\Users\nishanth.h\SteelBeamEstimator\.env`

## Prompt Management (Phase LLM.1.1 — MODEL_VERSION 6.1.1)

All prompts live in `prompts/` as version-controlled markdown templates. No prompts are hardcoded in Python.

```powershell
# Validate prompt engine
python validate_prompt_engine.py
```

Template usage:

```python
from src.llm import PromptExecutor

text = PromptExecutor().execute_template(
    "BEAM_REASONING",
    {"beam_name": "B12", "beam_id": "B12"},
    system_template="ENGINEERING_SYSTEM",
)
```

## Structured JSON Responses (Phase LLM.2 — MODEL_VERSION 6.2.0)

All AI-to-engineering interfaces use validated JSON schemas under `schemas/`.

```powershell
python validate_json_engine.py
```

Template + JSON usage:

```python
from src.llm import PromptExecutor

response = PromptExecutor().execute_json(
    "SAMPLE_PROMPT",
    "SAMPLE_RESPONSE",
    {"expected_response": "ok", "template_name": "SAMPLE_PROMPT"},
)
print(response.validated_data, response.confidence)
```

## Engineering Context Builder (Phase LLM.3 — MODEL_VERSION 6.3.0)

Deterministic engineering knowledge is assembled from supplied pipeline objects before any Claude call.

```powershell
python validate_context_builder.py
```

Context flow:

```
Engineering Objects → EngineeringContextBuilder → PromptExecutor.execute_engineering() → Claude → JSON Engine
```

Engineering template usage:

```python
from src.llm import PromptExecutor

response = PromptExecutor().execute_engineering(
    "BEAM_REASONING",
    "SAMPLE_RESPONSE",
    "BEAM_REASONING",
    engineering_objects,
    {"beam_name": "B-101", "beam_id": "B-101"},
)
```

Templates may reference `{{engineering_context}}`, `{{estimated_tokens}}`, `{{context_version}}`, and `{{context_checksum}}` without additional Python wiring.

## Engineering Reasoning Engine (Phase AI.1 — MODEL_VERSION 6.4.0)

First AI-powered engineering reasoning layer. Claude explains and interprets only — deterministic calculations remain authoritative.

```powershell
python validate_ai_reasoning_engine.py
```

Reasoning flow:

```
Engineering Objects → EngineeringContextBuilder → PromptExecutor → Claude → JSON Engine → EngineeringReasoningEngine → Phase Output Folder
```

Usage:

```python
from src.ai import EngineeringReasoningEngine

result = EngineeringReasoningEngine().reason(
    "BEAM_REASONING",
    engineering_objects,
    {"beam_id": "B-101", "beam_name": "B-101"},
)
print(result.summary, result.confidence)
```

Outputs are written only to:

`Version7/data/output/Phase AI.1 – Engineering Reasoning Engine/`

## Current pipeline status

- Phase E — General notes / engineering knowledge
- Phase F — Framing plan intelligence
- Phase G — Reinforcement loading, matching, property graph
- Phase H — Engineering specifications and geometry association
- Phase I — Calculations through I.17 Excel export
- Phase J — Recovery (J.1), expansion (J.2), integration (J.1.3), statistics validation (J.2.1)
- Phase K.1 (6.0.0) — Engineering Intent Reconstruction
- **Phase K.1.1 (6.0.1)** — Engineering Intent Resolution
- **Phase K.2 (6.1.0)** — Engineering Decision Execution
- **Phase K.2.1 (6.2.0)** — Engineering Decision Validation
- Phase LLM.1 (6.1.0) — Anthropic Claude Standardization
- **Phase LLM.1.1 (6.1.1)** — Prompt Management & Template Engine
- **Phase LLM.2 (6.2.0)** — Structured JSON Response Engine
- **Phase LLM.3 (6.3.0)** — Engineering Knowledge & Context Builder
- **Phase AI.1 (6.4.0)** — Engineering Reasoning Engine
- **Phase L.1 (6.3.0)** — Accuracy Sprint 1 — Estimator Gap Closure
- **Phase L.2 (6.4.0)** — Engineering Rule Audit Engine
- **Phase L.2 (6.4.0)** — Engineering Reinforcement Interpretation Engine
- **Phase L.2.1 (6.4.1)** — Engineering Feature Extraction Engine

## Run Engineering Feature Extraction (Phase L.2.1 — MODEL_VERSION 6.4.1)

```powershell
cd Version7
python Run_PY/run_phase_l2_1_engineering_feature_extraction.py
```

Deterministic engineering feature extraction layer that separates OBSERVATION from
INTERPRETATION. Produces an `EngineeringFeatureModel` for every reinforcement bar
containing pure engineering observations — no semantic role assignment.

**Architecture introduced by L.2.1:**
```
Drawing → Parser → Engineering Geometry
  → Engineering Feature Extraction (L.2.1)  ← this phase
  → Engineering Reinforcement Interpretation (L.2)
  → BeamReinforcementModel → Rules → Calculation → Steel → BBS → Excel
```

**Why this matters:** A structural engineer never classifies reinforcement immediately.
They first observe: "uppermost bar, continuous, crosses both supports, 97% span coverage."
These observations (features) then inform the classification (TOP_MAIN).

**Feature groups extracted per bar (16 fields each):**
- **Geometry**: start/end/midpoint, length, bbox, angle, is_closed, crosses_beam_axis
- **Position**: vertical_rank, depth_ratio, distances from top/bottom/left/right, position_zone
- **Continuity**: is_continuous, is_multi_span, crosses_support, beam_sequence, termination_points
- **Support**: left/right/intermediate overlap, support_zone_ratio, region_type
- **Extent**: full_span/left_only/right_only/both_supports, coverage_ratio, extent_type
- **Orientation**: LONGITUDINAL/TRANSVERSE, angle, parallel/perpendicular
- **Annotation**: callout, diameter, quantity, spacing, leader_count, priority
- **Topology**: connected_objects, adjacent_beams, support_connections, region_membership

**Non-negotiable constraints:** No semantic roles assigned. No BeamReinforcementModel
modified. No engineering rules implemented. Observations only.

**Results:** 53 bars extracted, 13 beams, 100% completeness. Validation: 21/21 PASS.

**Note:** After Phase L.2.2 runs, L.2.1 is re-triggered and processes all 18 beams
(68 features, 100% completeness, all B1–B18 covered). Phase L.3 then consumes these
features to produce deterministic structural engineering patterns for each beam.

## Run Engineering Geometry Recovery (Phase L.2.2 — MODEL_VERSION 6.4.2)

```powershell
cd Version7/Run_PY
python run_phase_l2_2_geometry_recovery.py
```

**CRITICAL pre-requisite for Phase L.2.1 full coverage.**

Investigates the pipeline consistency gap where B14–B18 exist in drawing,
engineering objects, and specifications but lack bars in the Engineering Feature Model.

**What this phase does:**

1. **Geometry Recovery Engine** — detects gap beams (in L.2 models with 0 bars),
   reconstructs `EngineeringGeometry` objects from L.2 geometry blocks, V5 beam
   schedule, and V5 engineering objects. Marks each as `ORIGINAL` or `RECOVERED`.

2. **Geometry Registry** — canonical `geometry_registry.json` with geometry_id,
   source, confidence, bounding_box, beam_axis, start_node, end_node, support_locations
   for every beam.

3. **Beam Coverage Validator** — collects beam IDs from Drawing Parser, Engineering
   Objects, Specifications, Geometry Registry, and Engineering Features. Produces the
   full Coverage Matrix (PASS/FAIL per beam × stage).

4. **Pipeline Consistency Validator** — 4 rules:
   - Feature Beam Count == Geometry Beam Count
   - Geometry Beam Count == Specification Beam Count
   - Specification Beam Count == Engineering Object Count
   - Engineering Object Count == Detected Beam Count
   Any violation raises `PIPELINE_COVERAGE_ERROR` (fail-fast).

5. **L.2.1 Re-trigger** — after recovery injects placeholder bars for B14–B18 into
   an extended beam model, Phase L.2.1 is re-run, producing features for all 18 beams.

6. **Geometry Traceability** — every beam carries `geometry_id`, `geometry_source`
   (ORIGINAL/RECOVERED), `creation_stage`, and `beam_validation_status`.

**Non-negotiable constraints:** No engineering calculations modified. No BBS generation
changed. No cut length or steel weight engine touched. Integrate before L.2.1 only.
Geometry recovery only runs when geometry is missing.

**Outputs (6 artifacts):**
`geometry_registry.json`, `geometry_recovery_report.json`, `beam_coverage_matrix.json`,
`pipeline_validation_report.json`, `geometry_traceability_map.json`,
`extended_beam_reinforcement_models.json`

**Results:**
- Detected Beams: 18 | Engineering Objects: 18 | Specifications: 18
- Geometry Objects: 18 (13 ORIGINAL + 5 RECOVERED) | Engineering Features: 18
- Recovered: B14, B15, B16, B17, B18 — all RECOVERED (0 FAILED)
- Coverage: 100% | Pipeline Validation: PASS

## Run Beam Reinforcement Pattern Recognition (Phase L.3 — MODEL_VERSION 6.5.0)

```powershell
cd Version7/Run_PY
python run_phase_l3_beam_pattern_recognition.py
```

**Prerequisites:** Phase L.2, Phase L.2.2, Phase L.2.1 must be run first.

Converts engineering features (L.2.1) into deterministic structural engineering patterns.
Acts as the semantic intelligence layer between feature extraction and future AI reasoning.
NO LLM. NO probabilistic heuristics. Deterministic engineering rules only.

**What this phase does:**

1. **SpanPatternDetector** — classifies each beam as SIMPLY_SUPPORTED,
   CONTINUOUS_END_SPAN, CONTINUOUS_INTERIOR_SPAN, DEEP_BEAM, TRANSFER_BEAM, or CANTILEVER.
   Uses support zones from L.2 + depth/span ratios.

2. **ContinuityDetector** — identifies SINGLE_BEAM, MULTI_BEAM_CONTINUOUS,
   CONTINUOUS_CHAIN (B8–B10 3-span group), or DISCONTINUOUS.

3. **ReinforcementPatternDetector** — compares top vs bottom steel area (proportional):
   TOP_REINFORCEMENT_DOMINANT, BOTTOM_REINFORCEMENT_DOMINANT, BALANCED_REINFORCEMENT,
   TOP_HEAVY, BOTTOM_HEAVY. Produces top_bottom_balance and dominant_reinforcement.

4. **SupportPatternDetector** — identifies BOTH_SIDE_REINFORCEMENT,
   ONE_SIDE_REINFORCEMENT, INTERMEDIATE_SUPPORT_REINFORCEMENT, SUPPORT_CONGESTION,
   LONG_SUPPORT_ZONE, SHORT_SUPPORT_ZONE.

5. **StructuralBehaviorDetector** — infers expected behaviour from reinforcement
   distribution: SAGGING_BEAM, HOGGING_BEAM, SAGGING_AND_HOGGING,
   SUPPORT_MOMENT_DOMINANT, MIDSPAN_MOMENT_DOMINANT, SYMMETRIC, ASYMMETRIC.

6. **PatternConfidence** — 5-component confidence score (feature completeness,
   geometry quality, bar classification, support data, continuity data).

7. **EngineeringPatternBuilder** — combines all detectors into a single
   `EngineeringPattern` per beam with full traceability.

8. **Validator** — 4 rules: Pattern Count == Feature Beams == Geometry Count
   == Engineering Objects; no duplicate beam IDs.

**Non-negotiable constraints:** No modifications to Phase L.2, L.2.1, or L.2.2.
Read-only inputs. Deterministic rules only.

**Outputs (6 artefacts):**
`engineering_patterns.json`, `engineering_pattern_registry.json`,
`pattern_summary.json`, `beam_pattern_matrix.json`,
`pattern_validation_report.json`, `pattern_statistics.json`

**Results (18 beams):**

| Category | Count |
|----------|-------|
| Simply Supported | 10 |
| Deep Beam | 5 |
| Continuous End Span (B8, B10) | 2 |
| Continuous Interior Span (B9) | 1 |
| Top Reinforcement Dominant | 6 |
| Bottom Reinforcement Dominant | 4 |
| Balanced Reinforcement | 3 |
| Minimal (recovered beams) | 5 |
| Confidence HIGH | 11 |
| Confidence MEDIUM | 7 |
| Mean Confidence | 0.84 |

**Sample — Beam B8:**
- Span Pattern: CONTINUOUS_END_SPAN
- Continuity: CONTINUOUS_CHAIN
- Reinforcement Pattern: BALANCED_REINFORCEMENT
- Support Pattern: INTERMEDIATE_SUPPORT_REINFORCEMENT
- Structural Behavior: SAGGING_AND_HOGGING
- Midspan Reinforcement: HEAVY | Top/Bottom Balance: BALANCED
- Dominant Reinforcement: STIRRUPS | Confidence: 0.948 (HIGH)

## Run Engineering Reinforcement Interpretation (Phase L.2 — MODEL_VERSION 6.4.0)

```powershell
cd Version7
python Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py
```

Deterministic semantic interpretation engine that assigns engineering meaning to every
reinforcement entity — exactly as an experienced structural estimator reads the drawings.

**What this phase does:**
- Classifies every bar into exactly one semantic role: TOP_MAIN, BOTTOM_MAIN, TOP_EXTRA,
  BOTTOM_EXTRA, STIRRUP, SIDE_FACE_REINFORCEMENT, SPACER_BAR, CHAIR_BAR, SUPPLEMENTARY_BAR
- Corrects pipeline misclassifications (e.g. 2Y20 bottom bars misclassified as TOP_MAIN)
- Produces `BeamReinforcementModel` for every beam — canonical semantic contract consumed
  by all downstream phases (Intent, Decision, Calculation, Steel, BBS, Excel)
- Anchors benchmark beams (B1, B2, B8–B10) to manually annotated reference drawings
- Detects support zones (LEFT, RIGHT, INTERMEDIATE), continuity (single vs multi-span),
  bar extent (full span vs support-only vs midspan-only), and beam ownership for multi-span

**Reference dataset used (engineering specifications):**
- `B1_Bars_Description.png`: TOP_MAIN=2Y16, TOP_EXTRA=2Y16@L+R, BOTTOM_MAIN=2Y20, SFR=4Y8
- `B2_Bars_Description.png`: TOP_MAIN=2Y16, BOTTOM_MAIN=2Y12, BOTTOM_EXTRA=2Y20@L-support
- `B8,B9,B10_Bar_Description.png`: Continuous 3-span, TOP_MAIN=2Y16, BOTTOM_MAIN=2Y16 each

**Outputs (10 artifacts):**
`beam_reinforcement_models.json`, `bar_role_classification.json`, `support_zone_analysis.json`,
`continuity_analysis.json`, `beam_ownership_analysis.json`, `reinforcement_regions.json`,
`engineering_semantics.json`, `interpretation_statistics.json`, `interpretation_dashboard.json`,
`interpretation_report.xlsx`

**Results:** 18 beams interpreted, 53 bars classified, 100% classification rate,
13 pipeline corrections, 30 reference-anchored bars. Validation: 18/18 PASS.

## Run Engineering Rule Audit (Phase L.2 — MODEL_VERSION 6.4.0)

```powershell
cd Version7/Run_PY
python run_phase_l2_engineering_rule_audit.py
```

Deterministic engineering rule audit that traces every reinforcement role
(Top Main, Bottom Main, Top Extra, Bottom Extra, Stirrups, Side Face,
Development Length, Hook, Lap Splice, Curtailment, Bent Bar, Cranked Bar, Chair Bar)
through the complete Version7 engineering pipeline.

**What this phase does (read-only diagnostic):**
- Discovers every engineering rule implemented in Version7 source
- Traces each role through all 17+ pipeline stages
- Classifies where execution stops (GEOMETRY_STOP, QUANTITY_STOP, EXPORT_STOP, etc.)
- Assigns implementation status to each capability
- Builds dependency graph for each role
- Generates the authoritative Implementation Matrix for Phase L.3+

**Key findings from audit:**

| Role | Status | Break Stage |
|------|--------|-------------|
| Top Main | PARTIALLY_EXECUTED | BEAM_SCHEDULE (all DEFERRED in V6) |
| Bottom Main | IMPLEMENTED_NOT_EXECUTED | ENGINEERING_OBJECT_CREATION |
| Top Extra | PARTIALLY_IMPLEMENTED | ENGINEERING_OBJECT_CREATION |
| Stirrup | EXECUTED_NOT_EXPORTED | STEEL_WEIGHT (all DEFERRED) |
| Side Face | EXECUTED_NOT_EXPORTED | BEAM_SCHEDULE (excluded from schedule) |
| Chair Bar | NOT_IMPLEMENTED | DRAWING_DETECTION |

Outputs saved to:
`Version7/data/output/PhaseL.2 - engineering_rule_audit/`

## Folder structure

```
Version7/
├── Run_PY/
├── config/
├── data/
│   ├── framing/
│   ├── general_notes/
│   ├── Excel_Presentation_Format/
│   ├── Estimator_Validated_Output/
│   └── output/          # Empty scaffold; all artifacts generated on run
└── src/
```
