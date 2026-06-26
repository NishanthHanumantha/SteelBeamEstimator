# Steel Beam Estimator — Version 3

Focused fork through engineering parsing and reinforcement classification (Phases D.3–D.4.1).

Version 2 remains frozen as the stable production fallback. All new development happens here.

## Setup

```powershell
pip install -r requirements.txt
cd Version3
```

## Runners

All phase entry-point scripts are in **`Run_PY/`**:

```powershell
python Run_PY/run_phases_abc.py
python Run_PY/run_phase_d3_beam_group_detection.py
python Run_PY/run_phase_d31_group_validation.py
python Run_PY/run_phase_d32_detail_regions.py
python Run_PY/run_phase_d33_annotation_ownership.py
python Run_PY/run_phase_d4_engineering_parser.py
python Run_PY/run_phase_d42_longitudinal_geometry.py
python Run_PY/run_phase_d41_reinforcement_classifier.py
python Run_PY/run_phase_e_general_notes.py
```

Runners set the working directory to `Version3/` automatically (`Run_PY/_bootstrap.py`), so `data/` paths and `src/` imports resolve without setting `PYTHONPATH`.

## Key outputs

| Phase | Output directory |
|-------|------------------|
| D.3 | `data/output/phase_d3/` |
| D.3.1 | `data/output/phase_d31/` |
| D.3.2 | `data/output/phase_d32/` |
| D.3.3 | `data/output/phase_d33/` |
| D.4 | `data/output/phase_d4/` |
| D.4.2 | `data/output/phase_d42/` |
| D.4.1 | `data/output/phase_d41/` |
| E | `data/output/phase_e/` — includes `project_defaults.json`, `project_engineering_report.json` |

## Architecture

```
Header → Occurrence → Sketch → Detail Region → Beam Group → Ownership → Engineering Objects → Geometry Resolution → Classification → General Notes Rules
```

## Folder structure

```
Version3/
├── Run_PY/              # All runner scripts (entry points)
├── data/input/          # Reference JSON snapshots
├── data/output/         # Phase outputs
├── src/parsing/         # Phase D.4 engineering parsers
├── src/geometry/        # Phase D.4.2 rebar geometry resolver
├── src/classification/  # Phase D.4.1 reinforcement classifier
├── src/general_notes/   # Phase E engineering rules engine
└── requirements.txt
```
