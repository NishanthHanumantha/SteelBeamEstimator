# Steel Beam Estimation Web Application

**MODEL_VERSION:** 8.9.5  
**Status:** Production Ready (stable baseline)  
**Scope:** Presentation layer only. Does **not** modify engineering logic.

## What it does

1. Upload exactly three DXF drawings:
   - General Notes
   - Beam Framing Plan
   - Beam Reinforcement Plan
2. Run the Version8 production pipeline via `RunContext` (per-run `web_runs/<run_id>/`)
3. Download the generated `Estimation_Output.xlsx` from the **same** run

## Requirements

- Python 3.10+
- Version8 engineering dependencies (`Version8/requirements.txt`)
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
Health: http://127.0.0.1:5000/health

## Run (production-style)

```powershell
cd Version8\webapp
gunicorn -b 0.0.0.0:5000 --timeout 3600 "app:app"
```

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `STEEL_WEB_MAX_UPLOAD_MB` | `256` | Max total upload size (MB) |
| `STEEL_WEB_SECRET_KEY` | dev key | Flask secret |
| `STEEL_ENGINE_ROOT` | Version8 | Set by service per stage |
| `STEEL_RUN_ROOT` | `web_runs/<run_id>` | Set by service per stage |
| `STEEL_OUTPUT_ROOT` | `…/data/output` | Set by service per stage |

## Production pipeline

```text
Upload → VROOT1 → R1 → R2A → R.2.1B → R.2.1C → R.2.1D
      → L.2.2 → R.3 → R.3.1 → R.1.2A → R.1.3 → VB.1
      → web_runs/<run_id>/data/output/Production_Output/Estimation_Output.xlsx
      → download Estimation_Output_<run_id>.xlsx
```

All artefacts are written under the current run tree. No Version7 seeding and no
shared `Version8/data/output` dependency on the web path.

## Notes

- Only `.dxf` uploads are accepted.
- All three files are mandatory.
- UI errors are engineering-readable; Python stack traces are not shown.
- Per-run `web_runs/<run_id>/` artefacts are retained for support/inspection.
