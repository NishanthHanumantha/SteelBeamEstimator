# Phase UI.1 — Steel Beam Estimation Web Application

**MODEL_VERSION:** 8.8.3  
**Scope:** Presentation layer only. Does **not** modify engineering logic.

## What it does

1. Upload exactly three DXF drawings:
   - General Notes
   - Beam Framing Plan
   - Beam Reinforcement Plan
2. Run the existing Version8 production pipeline (V.ROOT.1 → … → V.B.1)
3. Download the generated `Estimation_Output.xlsx`

No diagnostics, JSON exports, RULE dashboards, or engineering review screens.

## Requirements

- Python 3.10+
- Version8 engineering dependencies already installed (`Version8/requirements.txt`)
- Flask webapp deps:

```powershell
cd Version8\webapp
pip install -r requirements.txt
```

## Run (development)

```powershell
cd Version8\webapp
python app.py
```

Open: http://127.0.0.1:5000

## Run (production-style)

```powershell
cd Version8\webapp
gunicorn -b 0.0.0.0:5000 --timeout 3600 "app:app"
```

Compatible with Nginx reverse proxy and AWS Lightsail.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `STEEL_WEB_MAX_UPLOAD_MB` | `256` | Max total upload size (MB) |
| `STEEL_WEB_SECRET_KEY` | dev key | Flask secret |

## Folder layout

```text
webapp/
  app.py
  routes.py
  config.py
  requirements.txt
  README.md
  services/estimation_service.py
  templates/index.html
  static/css/app.css
  static/js/app.js
  uploads/          temporary per-run copies (cleaned after run)
  outputs/          retained workbooks for download
  logs/webapp.log
```

Staged DXFs for the engine are placed under `Version8/data/web_runs/<run_id>/` in the standard `general_notes/`, `framing/`, `reinforcement/` layout expected by V.ROOT.1.

## Pipeline invoked (unchanged runners)

1. `run_phase_vroot1_dynamic_pipeline_initialization.py`
2. `run_phase_r1_generalized_reinforcement_discovery.py` (before R.3 — annotations required)
3. `run_phase_r2a_engineering_context.py`
4. `run_phase_r3_geometry_context_engine.py`
5. `run_phase_r31_engineering_relationship_engine.py`
6. `run_phase_r12a_geometry_accuracy.py`
7. `run_phase_r12c_engineering_intent_resolution.py`
8. `run_phase_r12d_reinforcement_detailing.py`
9. `run_phase_r13_reinforcement_piece_generation.py`
10. `run_phase_r13_pipeline_integration.py`
11. `run_phase_vb1_production_output_completion.py`

R.3 also needs `EngineeringFacts.json` (R.2.1D) and `geometry_registry.json` (L.2.2).
If those are missing under `Version8/data/output/`, the webapp seeds them from
`Version7/data/output/` when available.

Workbook source: `Version8/data/output/Production_Output/Estimation_Output.xlsx`  
Copied to `webapp/outputs/Estimation_Output_<run_id>.xlsx` for download.

## Notes

- Only `.dxf` uploads are accepted.
- All three files are mandatory.
- UI errors are engineering-readable; Python stack traces are not shown.
- Temporary upload/staging folders are cleaned after each run; output workbooks are retained until manually removed.
