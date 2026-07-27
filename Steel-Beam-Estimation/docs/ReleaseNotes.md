# Release Notes — Steel-Beam-Estimation

## D.3 — Production packaging & deployment readiness (2026-07-27)

### Added / hardened

- `/health` returns `status`, `model_version`, `timestamp`, `engine_ready`
- `wsgi.py` production entry point (for later gunicorn)
- Production `SECRET_KEY` required when `FLASK_ENV=production`
- Cleaned `requirements.txt` (no duplicate Werkzeug pin)
- `deployment/scripts/validate_packaging.py` local packaging check
- DeploymentGuide local checklist + environment variable table

### Guarantees

- Existing frontend unchanged
- Engineering / estimation logic unchanged
- No AWS / Nginx / systemd configuration yet

---

## D.2 — Application foundation & local execution (2026-07-27)

### Added

- Flask application factory under `current_model/webapp/`
- Central config: `config/settings.py`, `config/paths.py`, `config/model_info.yaml`
- Logging to `current_model/logs/application.log`
- Estimation service wrapper (`webapp/services.py`) invoking engine runners via `STEEL_ENGINE_ROOT`
- Local entry point `python run.py` → http://127.0.0.1:5000
- `.env.example`, updated `requirements.txt`, UI templates/static

### Guarantees

- No engineering / estimation logic modified
- No Gunicorn / Nginx / systemd / AWS config added yet

---

## D.1 — Project foundation (2026-07-27)

### Added

- Deployment-ready package layout under `Steel-Beam-Estimation/`
- Version-agnostic `current_model/` slot for the active estimation package
- `deployment/` placeholders for Gunicorn, Nginx, systemd, and scripts
- Documentation: README, Architecture, DeploymentGuide, deployment README
- `.gitignore`, `LICENSE`, local stubs
