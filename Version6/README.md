# Steel Beam Estimator — Version 6

Active development branch continuing from **Version 5** (frozen at Phase J.2.1 / 5.28.1).

**Version 5 is frozen.** All new model development happens here.

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
cd Version6
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

`Version6/data/output/Phase AI.1 – Engineering Reasoning Engine/`

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

## Run Engineering Reinforcement Interpretation (Phase L.2 — MODEL_VERSION 6.4.0)

```powershell
cd Version6
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
cd Version6/Run_PY
python run_phase_l2_engineering_rule_audit.py
```

Deterministic engineering rule audit that traces every reinforcement role
(Top Main, Bottom Main, Top Extra, Bottom Extra, Stirrups, Side Face,
Development Length, Hook, Lap Splice, Curtailment, Bent Bar, Cranked Bar, Chair Bar)
through the complete Version6 engineering pipeline.

**What this phase does (read-only diagnostic):**
- Discovers every engineering rule implemented in Version6 source
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
`Version6/data/output/PhaseL.2 - engineering_rule_audit/`

## Folder structure

```
Version6/
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
