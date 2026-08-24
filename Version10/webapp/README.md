# Steel Beam Estimation Web Application (Version10)

**App release:** W.2  
**Engine:** Version10 production pipeline (VROOT1 → R1 → **T1** → R2A → … → VB.1)  
**Scope:** Presentation + adapter only. Does **not** modify engineering logic.

This is not the packaged Lightsail 8.9.5 engine. `ENGINE_ROOT` is `Version10/`.

## What it does

1. Upload exactly three DXF drawings:
   - General Notes
   - Beam Framing Plan
   - Beam Reinforcement Plan
2. Create an isolated `data/web_runs/<run_id>/` workspace
3. Invoke the Version10 production runners via RunContext
4. Download `Estimation_Output_<run_id>.xlsx` from that run

Only one estimation runs at a time (single-flight). Concurrent runs are rejected.

## Requirements

Install **engine** dependencies, then web dependencies:

```powershell
cd Version10
pip install -r requirements.txt
cd webapp
pip install -r requirements.txt
```

T1 uses matplotlib, Pillow, and opencv-python-headless from `Version10/requirements.txt`.

## Run (development)

```powershell
cd Version10\webapp
python app.py
```

Open: http://127.0.0.1:5000  
Health: http://127.0.0.1:5000/health

## Production-style launch (Linux / Lightsail)

PREPARED FOR FUTURE DEPLOYMENT — NOT YET DEPLOYED.

From `Version10/webapp`, workers **must** be 1:

```bash
gunicorn --workers 1 --timeout 3600 --bind 127.0.0.1:8000 "wsgi:app"
```

Gunicorn cannot be started on Windows (`fcntl` is Unix-only). See `deployment/LAUNCH_W21.txt`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `STEEL_WEB_MAX_UPLOAD_MB` | `256` | Max total upload size (MB) |
| `STEEL_WEB_SECRET_KEY` | dev key | Flask secret |
| `STEEL_ENGINE_ROOT` | Version10 | Set by adapter per stage |
| `STEEL_RUN_ROOT` | `web_runs/<run_id>` | Set by adapter per stage |
| `STEEL_OUTPUT_ROOT` | `…/data/output` | Set by adapter per stage |
| `STEEL_WEB_PIPELINE_MODE` | `live` | `stub` is **tests only** |

## Production pipeline

```text
Upload → VROOT1 → R1 → T1 → R2A → R.2.1B → R.2.1C → R.2.1D
      → L.2.2 → R.3 → R.3.1 → R.1.2A → R.1.3 → VB.1
      → web_runs/<run_id>/data/output/Production_Output/Estimation_Output.xlsx
      → download Estimation_Output_<run_id>.xlsx
```

The hybrid D.1–D.4 / E.* shadow path is not invoked.

## Notes

- Only `.dxf` uploads are accepted.
- All three files are mandatory and must be non-empty.
- UI errors are estimator-readable; Python stack traces are not shown.
- Per-run `web_runs/<run_id>/` artefacts are retained.
- Do not deploy this phase to Lightsail (W.2 is local validation only).
