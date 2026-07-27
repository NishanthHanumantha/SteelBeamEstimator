# Deployment Guide — Steel Beam Reinforcement Estimation

**Phase:** D.3 (production packaging & local deployment readiness)  
**Target:** AWS Lightsail (independent of Concrete Estimator)  
**Note:** AWS instance / Nginx / systemd commands are deferred to later phases.

---

## Folder overview

```text
Steel-Beam-Estimation/
├── current_model/          # Deployable application package
│   ├── webapp/             # Flask presentation layer
│   ├── config/             # settings, paths, model_info.yaml
│   ├── templates/          # UI (do not redesign in deployment phases)
│   ├── static/             # CSS / JS
│   ├── inputs/             # Optional staged inputs
│   ├── outputs/            # Generated Excel workbooks
│   ├── temp/               # Temporary uploads (cleaned after runs)
│   ├── logs/               # application.log
│   ├── run.py              # Local: python run.py
│   ├── wsgi.py             # Production WSGI entry (gunicorn later)
│   ├── requirements.txt
│   └── .env.example
├── deployment/             # Infra configs (gunicorn/nginx/systemd later)
├── docs/
└── tests/
```

Runtime rule: process managers always target **`current_model/`**, never a version-named folder.

---

## Local deployment checklist

Use this checklist before any AWS cutover.

1. [ ] Copy / sync `Steel-Beam-Estimation/` to the target machine  
2. [ ] `cd current_model`  
3. [ ] `python -m venv .venv` and activate it  
4. [ ] `pip install -r requirements.txt`  
5. [ ] Install engine dependencies from `STEEL_ENGINE_ROOT/requirements.txt`  
      (skip if `Run_PY/` is already packaged inside `current_model/`)  
6. [ ] `copy .env.example .env` (Windows) or `cp .env.example .env`  
7. [ ] Set required environment variables in `.env` (see below)  
8. [ ] `python run.py`  
9. [ ] Open http://127.0.0.1:5000 — UI loads  
10. [ ] Open http://127.0.0.1:5000/health — returns `status`, `model_version`, `timestamp`  
11. [ ] Optional: `python ../deployment/scripts/validate_packaging.py`  
12. [ ] Confirm uploads land under `temp/` during processing and Excel under `outputs/`  
13. [ ] Confirm `logs/application.log` records startup / upload / processing events  

**Deploy contract:** copy project → install requirements → configure `.env` → run.  
No extra manual path edits in source files.

---

## Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | **Yes in production** | Flask session / security |
| `FLASK_ENV` | Recommended | `development` or `production` |
| `STEEL_ENGINE_ROOT` | Yes if engine not packaged in `current_model/` | Absolute path to engine (`Run_PY/`, `src/`) |
| `MAX_UPLOAD_MB` | Optional (default 256) | Upload size limit |
| `STEEL_BEAM_HOST` | Optional (default `127.0.0.1`) | Bind host for `run.py` |
| `STEEL_BEAM_PORT` | Optional (default `5000`) | Bind port |
| `ANTHROPIC_API_KEY` | Optional | Placeholder only; not required for DXF pipeline |
| `STEEL_ARTEFACT_SEED_ROOT` | Optional | Seed missing intermediate artefacts |

Never commit `.env`. Never put secrets in source code.

---

## Health check

`GET /health` returns JSON suitable for later AWS validation:

```json
{
  "status": "ok",
  "service": "steel-beam-estimation",
  "phase": "D.3",
  "model_version": "...",
  "engine_ready": true,
  "timestamp": "2026-07-27T10:00:00+00:00"
}
```

---

## File storage behaviour

| Path | Role |
|------|------|
| `temp/<run_id>/` | Temporary upload copies during a run (removed after completion) |
| `outputs/Estimation_Output_<run_id>.xlsx` | Downloadable workbook |
| Engine `data/web_runs/<run_id>/` | Staging for V.ROOT.1 (cleaned after run) |
| `logs/application.log` | Application + estimation events |

---

## Phase roadmap

| Phase | Work | Status |
|-------|------|--------|
| D.1 | Folder foundation + docs | Done |
| D.2 | Flask application foundation + local `run.py` | Done |
| **D.3** | Production packaging & local deployment readiness | **Done** |
| D.4 | Gunicorn configuration | Planned |
| D.5 | systemd service | Planned |
| D.6 | Nginx reverse proxy + TLS | Planned |
| D.7 | Lightsail cutover + smoke tests | Planned |

---

## AWS Lightsail (later phases — placeholders only)

```bash
# TODO (later): create Lightsail instance / open ports / deploy user
# TODO (later): rsync Steel-Beam-Estimation to the server
# TODO (later): venv + pip install -r current_model/requirements.txt
# TODO (later): configure .env with production SECRET_KEY
# TODO (later): gunicorn via wsgi:app + systemd + nginx + TLS
```

**Upgrade rule:** replace `current_model/` contents only — do not rename to version labels.

---

## Related docs

- [Architecture.md](Architecture.md)
- [../deployment/README.md](../deployment/README.md)
- [ReleaseNotes.md](ReleaseNotes.md)
