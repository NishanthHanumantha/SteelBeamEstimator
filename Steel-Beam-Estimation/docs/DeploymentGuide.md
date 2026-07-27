# Deployment Guide — Steel Beam Reinforcement Estimation

**Phase:** D.4 (production deployment assets generated)  
**Target:** AWS Lightsail (independent of Concrete Estimator)  
**Status:** Assets only — this phase does **not** SSH or deploy.

---

## Folder overview

```text
Steel-Beam-Estimation/
├── current_model/                 # Application package (version-agnostic)
├── deployment/
│   ├── config.yaml                # Deploy parameters (edit before go-live)
│   ├── gunicorn/gunicorn.conf.py
│   ├── nginx/steel-beam-estimator.conf
│   ├── systemd/steel-beam-estimator.service
│   └── scripts/                   # 01–10 + _common.sh + validate_packaging.py
└── docs/
```

Process managers always target **`current_model/`**, never a version-named folder.

---

## Local packaging checklist (from D.3)

1. [ ] `cd current_model`  
2. [ ] Create venv + `pip install -r requirements.txt`  
3. [ ] Copy `.env.example` → `.env` and set secrets  
4. [ ] Set `STEEL_ENGINE_ROOT` if the engine is external  
5. [ ] `python run.py` → http://127.0.0.1:5000  
6. [ ] `GET /health` returns `status`, `model_version`, `timestamp`  
7. [ ] `python ../deployment/scripts/validate_packaging.py`

---

## Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | **Yes in production** | Flask security |
| `FLASK_ENV` | Recommended | `production` on server |
| `STEEL_ENGINE_ROOT` | If engine not inside `current_model/` | Absolute engine path |
| `MAX_UPLOAD_MB` | Optional | Upload limit (default 256) |
| `ANTHROPIC_API_KEY` | Optional | Placeholder only |

Never commit `.env`.

---

## Deployment assets (Phase D.4)

### `deployment/config.yaml`

Central placeholders used by scripts:

| Key | Meaning |
|-----|---------|
| `server_ip` | Lightsail public IP (documentation / future use) |
| `ssh_user` | OS user that owns the app (e.g. `ubuntu`) |
| `application_directory` | Install root (e.g. `/opt/steel-beam-estimation`) |
| `github_repository` | Git clone URL |
| `branch` | Git branch to deploy |
| `python_version` | Preferred Python (e.g. `3.12`) |
| `virtual_environment_name` | Venv folder under `current_model/` |
| `gunicorn_service_name` | systemd unit name |
| `nginx_site_name` | Nginx site filename stem |

Edit this file on the server (or before packaging) — scripts read it via `_common.sh`.

### Process / proxy configs

| File | Purpose |
|------|---------|
| `gunicorn/gunicorn.conf.py` | Workers, timeout, logging (env-overridable) |
| `nginx/steel-beam-estimator.conf` | Reverse proxy + `/static/` + `/health` |
| `systemd/steel-beam-estimator.service` | Gunicorn under systemd (`wsgi:app`) |

---

## Purpose of every deployment script

| Script | Purpose |
|--------|---------|
| `_common.sh` | Shared config loader + helpers (sourced by other scripts) |
| `01_server_setup.sh` | Install OS packages (git, python, nginx, build tools) |
| `02_clone_project.sh` | Clone or fast-forward update the GitHub repo |
| `03_create_venv.sh` | Create `current_model/.venv` if missing |
| `04_install_requirements.sh` | `pip install -r requirements.txt` (+ optional engine deps) |
| `05_configure_environment.sh` | Create `.env` from `.env.example` **only if absent** |
| `06_validate_application.sh` | Run packaging / health contract checks |
| `07_install_gunicorn.sh` | Install gunicorn in venv + render/enable systemd unit |
| `08_install_nginx.sh` | Render nginx site, enable it, `nginx -t`, reload |
| `09_restart_services.sh` | Restart gunicorn + reload nginx + probe `/health` |
| `10_update_application.sh` | `git pull --ff-only`, reinstall deps, validate, restart |
| `validate_packaging.py` | Local/CI packaging validator (from D.3) |

All bash scripts are intended to be **idempotent**, **fail-safe** (`set -euo pipefail`), and driven by **`config.yaml` variables**.

---

## Deployment sequence (on the Lightsail host)

> Do not run these until an operator is ready. Phase D.4 only generates assets.

```bash
# 0) Edit deployment/config.yaml (paths, repo URL, branch, user)

cd /path/to/Steel-Beam-Estimation/deployment/scripts
chmod +x *.sh

sudo ./01_server_setup.sh
./02_clone_project.sh
./03_create_venv.sh
./04_install_requirements.sh
./05_configure_environment.sh
# >>> edit current_model/.env  (SECRET_KEY, FLASK_ENV=production, STEEL_ENGINE_ROOT)
./06_validate_application.sh
sudo ./07_install_gunicorn.sh
sudo ./08_install_nginx.sh
sudo ./09_restart_services.sh
```

Expected result: Nginx on port 80 proxies to Gunicorn; `GET /health` returns JSON.

---

## GitHub update procedure

On the server:

```bash
cd /path/to/Steel-Beam-Estimation/deployment/scripts
./10_update_application.sh
```

What it does:

1. `git fetch` + checkout configured `branch`  
2. `git pull --ff-only` (aborts on divergent local commits)  
3. Re-run requirements install  
4. Validate packaging  
5. Restart gunicorn + reload nginx  

If fast-forward fails: resolve/stash server-side changes, then re-run.

---

## Rollback procedure

1. Identify last known-good commit SHA (GitHub / `git log`).  
2. On the server:

```bash
cd /opt/steel-beam-estimation   # application_directory from config.yaml
git fetch --all
git checkout <known-good-sha>
```

3. Reinstall deps and restart:

```bash
cd Steel-Beam-Estimation/deployment/scripts   # or flat layout path
./04_install_requirements.sh
sudo ./09_restart_services.sh
```

4. Confirm `curl -fsS http://127.0.0.1:8000/health` (or your `gunicorn_bind`).  
5. Optionally create a git tag for known-good releases before updates.

**Do not** force-push from the server. Prefer ff-only updates + checkout for rollback.

---

## Health check

`GET /health` should return:

```json
{
  "status": "ok",
  "service": "steel-beam-estimation",
  "phase": "D.3",
  "model_version": "...",
  "engine_ready": true,
  "timestamp": "..."
}
```

---

## Phase roadmap

| Phase | Work | Status |
|-------|------|--------|
| D.1 | Folder foundation | Done |
| D.2 | Flask application foundation | Done |
| D.3 | Production packaging readiness | Done |
| **D.4** | Generate gunicorn/nginx/systemd + deploy scripts | **Done** |
| D.5+ | Execute Lightsail cutover / TLS / monitoring | Planned |

---

## Related docs

- [Architecture.md](Architecture.md)
- [../deployment/README.md](../deployment/README.md)
- [ReleaseNotes.md](ReleaseNotes.md)
