# Steel Beam Estimator — Version 5

Active development branch continuing from **Version 4** through Phase G.5.3.4 (Property Lifecycle & Availability).

**Version 4 is frozen** at Phase G.5.3.4. All new model development happens here.

## What is included

Copied from Version4 (runtime essentials only):

| Area | Purpose |
|------|---------|
| `src/` | Full pipeline through Phase G.5.3.4 |
| `config/` | Framing, general notes, estimator rules |
| `Run_PY/` | Phase E and Phase F+G runners |
| `data/framing/` | Framing plan + reinforcement DXF inputs |
| `data/general_notes/` | General Notes DXF input |
| `data/output/phase_e/` | Phase E engineering knowledge baseline (JSON) |

**Not copied** (regenerate locally):

- `data/output/phase_f/` — framing geometry outputs
- `data/output/phase_g/` — reinforcement / property pipeline outputs
- Debug DXF files, temp run logs, `__pycache__`

## Setup

```powershell
pip install -r requirements.txt
cd Version5
$env:PYTHONPATH="."
```

## Run Phase E (refresh engineering knowledge)

```powershell
python Run_PY/run_phase_e_general_notes.py
```

## Run Phase F + G pipeline

```powershell
python Run_PY/run_phase_f_framing.py
```

Regenerates outputs under `data/output/phase_f/` and `data/output/phase_g/`.

## Current pipeline status (inherited from V4)

- Phase F — Framing plan intelligence
- Phase G.1–G.3 — Reinforcement loading through beam matching
- Phase G.4–G.5.0.1 — Engineering objects, semantic roles/relationships
- Phase G.5.1–G.5.3.4 — Property graph, parser, resolver, confidence, lifecycle

## Folder structure

```
Version5/
├── Run_PY/
├── config/
├── data/
│   ├── framing/
│   ├── general_notes/
│   └── output/
│       └── phase_e/     # Baseline only; phase_f/phase_g generated on run
└── src/
```
