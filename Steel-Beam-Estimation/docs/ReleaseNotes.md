# Release Notes — Steel-Beam-Estimation

## D.4 — Production deployment assets (2026-07-27)

### Added

- `deployment/config.yaml` — deploy parameters
- `deployment/gunicorn/gunicorn.conf.py`
- `deployment/nginx/steel-beam-estimator.conf`
- `deployment/systemd/steel-beam-estimator.service`
- Host scripts `01`–`10` plus `_common.sh` (idempotent, config-driven)
- DeploymentGuide: script catalogue, sequence, rollback, GitHub update

### Guarantees

- No SSH / live deploy performed
- No engineering, frontend, or estimation logic changes

---

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

---

## D.1 — Project foundation (2026-07-27)

### Added

- Deployment-ready package layout under `Steel-Beam-Estimation/`
- Version-agnostic `current_model/` slot
- Documentation stubs and `.gitignore` / `LICENSE`
