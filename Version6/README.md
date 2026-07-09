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
- Phase LLM.1 (6.1.0) — Anthropic Claude Standardization
- **Phase LLM.1.1 (6.1.1)** — Prompt Management & Template Engine
- **Phase LLM.2 (6.2.0)** — Structured JSON Response Engine
- **Phase LLM.3 (6.3.0)** — Engineering Knowledge & Context Builder
- **Phase AI.1 (6.4.0)** — Engineering Reasoning Engine

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
