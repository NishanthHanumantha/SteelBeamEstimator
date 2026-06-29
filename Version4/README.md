# Steel Beam Estimator — Version 4

Active development branch for **Phase F (Framing Plan Intelligence)** and beyond.

**Version 3 is frozen** as the stable fallback through Phase E.3 (General Notes + provenance).

## What is included

Imported from Version3 (minimal runtime only):

| Area | Purpose |
|------|---------|
| `src/general_notes/` | Phase E engineering knowledge engine |
| `src/estimation/` | Estimator methodology config loader |
| `src/framing/` | Framing plan beam extraction (Phase A foundation) |
| `src/parser/`, `src/extractor/`, `src/utils/` | DXF + beam label support for framing |
| `config/` | General notes + estimator rules |
| `data/general_notes/` | General Notes DXF input |
| `data/framing/` | Framing plan DXF input |
| `data/output/phase_e/` | Baseline engineering knowledge JSON (from V3) |

Phase D modules, reinforcement pipeline, and debug outputs were **not** copied.

## Setup

```powershell
pip install -r requirements.txt
cd Version4
```

## Run Phase E (refresh engineering knowledge)

```powershell
python Run_PY/run_phase_e_general_notes.py
```

## Run Phase F (framing plan geometry + dimension resolution)

```powershell
python Run_PY/run_phase_f_framing.py
```

Runs **F.1** (geometry) through **F.5** (knowledge graph + coordinate system).

Outputs under `data/output/phase_f/`:
- `beam_geometry_model.json` — authoritative model with `length_model`, `engineering_references`, `stationing`
- `framing_knowledge_graph.json`, `engineering_coordinate_system.json`, `beam_stationing.json`
- `beam_relationships.json`, `engineering_status_registry.json`
- `phase_f_graph_validation.json`
- `phase_f_debug.dxf` — includes `DEBUG_GRAPH`, `DEBUG_STATIONING`, `DEBUG_RELATIONSHIPS`

## Architecture

```
Phase D (Drawing Intelligence)     — in Version3 (frozen)
Phase E (General Notes)            — imported + runnable here
Phase F (Framing Plan Intelligence) — F.1 through F.5 complete
Phase G (Engineering Computation)  — planned
```

Future phases consume engineering rules through `EngineeringRuleCache`, not raw JSON.

## Folder structure

```
Version4/
├── Run_PY/              # Runners (_bootstrap sets cwd to Version4)
├── config/              # YAML configuration
├── data/
│   ├── general_notes/   # GN DXF
│   ├── framing/         # Framing plan DXF
│   └── output/
│       ├── phase_e/     # Engineering knowledge baseline
│       └── phase_f/     # Phase F outputs (new)
└── src/
    ├── general_notes/
    ├── estimation/
    ├── framing/
    └── config/
```
