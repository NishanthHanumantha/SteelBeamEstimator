# Steel Beam Estimation Web Application

**MODEL_VERSION:** 8.9.5  
**Status:** Version9 accuracy branch (baseline 8.9.5)  
**Scope:** Presentation layer only. Does **not** modify engineering logic.

## What it does

1. Upload exactly three DXF drawings:
   - General Notes
   - Beam Framing Plan
   - Beam Reinforcement Plan
2. Run the Version9 production pipeline via `RunContext` (per-run `web_runs/<run_id>/`)
3. Download the generated `Estimation_Output.xlsx` from the **same** run

## Requirements

- Python 3.10+
- Version9 engineering dependencies (`Version9/requirements.txt`)
- Flask webapp deps:

```powershell
cd Version9\webapp
pip install -r requirements.txt
```

## Run (development)

```powershell
cd Version9\webapp
python app.py
```

Open: http://127.0.0.1:5000  
Health: http://127.0.0.1:5000/health

## Run (production-style)

```powershell
cd Version9\webapp
gunicorn -b 0.0.0.0:5000 --timeout 3600 "app:app"
```

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `STEEL_WEB_MAX_UPLOAD_MB` | `256` | Max total upload size (MB) |
| `STEEL_WEB_SECRET_KEY` | dev key | Flask secret |
| `STEEL_ENGINE_ROOT` | Version9 | Set by service per stage |
| `STEEL_RUN_ROOT` | `web_runs/<run_id>` | Set by service per stage |
| `STEEL_OUTPUT_ROOT` | `â€¦/data/output` | Set by service per stage |

## Production pipeline

```text
Upload â†’ VROOT1 â†’ R1 â†’ R2A â†’ R.2.1B â†’ R.2.1C â†’ R.2.1D
      â†’ L.2.2 â†’ R.3 â†’ R.3.1 â†’ R.1.2A â†’ R.1.3 â†’ VB.1
      â†’ web_runs/<run_id>/data/output/Production_Output/Estimation_Output.xlsx
      â†’ download Estimation_Output_<run_id>.xlsx
```

All artefacts are written under the current run tree. No Version7 seeding and no
shared `Version9/data/output` dependency on the web path.

## Notes

- Only `.dxf` uploads are accepted.
- All three files are mandatory.
- UI errors are engineering-readable; Python stack traces are not shown.
- Per-run `web_runs/<run_id>/` artefacts are retained for support/inspection.

