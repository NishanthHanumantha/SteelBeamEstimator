# Deployment Guide — Steel Beam Reinforcement Estimation

**Phase:** D.4.1 (path abstraction & existing-install support)  
**Target:** AWS Lightsail (independent of Concrete Estimator)  
**Deployment package version:** D.4.1

---

## Supported installation layouts

### Mode A — Fresh / flat package

```text
/opt/steel-beam-estimation/                  # application_directory
└── Steel-Beam-Estimation/                   # project_directory
    └── current_model/                       # model_directory
```

`repository_directory` may be left empty. The git root is typically
`application_directory` itself (or the project root).

### Mode B — Existing monorepo checkout (common on Lightsail)

```text
/opt/steel-beam-estimation/                  # application_directory
└── SteelBeamEstimator/                      # repository_directory
    └── Steel-Beam-Estimation/               # project_directory
        └── current_model/                   # model_directory
```

Both modes work without editing shell scripts. Configure `deployment/config.yaml`
or rely on **automatic discovery**.

---

## Path resolution (single source of truth)

All scripts source `deployment/scripts/_common.sh`.

That file is the **only** place paths are calculated. It exports:

| Variable | Meaning |
|----------|---------|
| `APPLICATION_DIRECTORY` | Install root from config |
| `REPOSITORY_ROOT` | Git clone root |
| `PROJECT_ROOT` | `Steel-Beam-Estimation/` package (has `deployment/` + `current_model/`) |
| `MODEL_ROOT` | `current_model/` |
| `VENV_DIR` / `VENV_BIN` | Virtualenv under model root |
| `DEPLOYMENT_MODE` | Fresh / Existing / auto-detected |

### Resolution order

1. Build paths from `config.yaml`  
2. If configured `MODEL_ROOT` exists and is valid → use it  
3. Else search `application_directory` for a single `current_model` → derive parents  
4. Else try the package that contains the running scripts  
5. Else keep configured paths for **fresh install** (clone next)

If multiple `current_model` directories are found → **fail with diagnostics**.

Every script prints a configuration summary before running.

---

## Configuration (`deployment/config.yaml`)

```yaml
application_directory: "/opt/steel-beam-estimation"
repository_directory: "SteelBeamEstimator"   # empty for Mode A
project_directory: "Steel-Beam-Estimation"
model_directory: "current_model"
```

### Backwards compatibility

Legacy keys still work:

- `app_subdirectory` → treated as `project_directory`
- `model_subdirectory` → treated as `model_directory`

If optional fields are missing, automatic discovery is attempted.

---

## Fresh deployment sequence

```bash
cd /path/to/Steel-Beam-Estimation/deployment/scripts
chmod +x *.sh

# Edit ../config.yaml first (repo URL, branch, directories)
sudo ./01_server_setup.sh
./02_clone_project.sh
./03_create_venv.sh
./04_install_requirements.sh
./05_configure_environment.sh
# edit MODEL_ROOT/.env
./06_validate_application.sh
sudo ./07_install_gunicorn.sh
sudo ./08_install_nginx.sh
sudo ./09_restart_services.sh
```

---

## Existing deployment (already cloned)

If the tree already looks like Mode B:

1. Pull latest deployment package (or `./10_update_application.sh`)  
2. Ensure `config.yaml` has `repository_directory: SteelBeamEstimator` **or** leave discovery to auto-detect  
3. Run:

```bash
./03_create_venv.sh          # reuses venv if present
./04_install_requirements.sh
./06_validate_application.sh
sudo ./09_restart_services.sh
```

`03_create_venv.sh` no longer fails when the old flat path is absent — it uses the resolved `MODEL_ROOT`.

---

## Clone script behaviour (`02_clone_project.sh`)

| Case | Behaviour |
|------|-----------|
| Git repo already at `REPOSITORY_ROOT` | `git pull --ff-only` |
| Path missing / empty | `git clone` |
| Non-empty unrelated files | Abort safely |
| Different `origin` remote | Warn and exit |

---

## GitHub update procedure

```bash
./10_update_application.sh
```

Updates `REPOSITORY_ROOT` (not a hardcoded folder name), reinstalls requirements, validates, restarts services.

---

## Rollback procedure

```bash
cd "$REPOSITORY_ROOT"    # from the summary printed by scripts
git fetch --all
git checkout <known-good-sha>
cd Steel-Beam-Estimation/deployment/scripts   # or your project_directory/deployment/scripts
./04_install_requirements.sh
sudo ./09_restart_services.sh
```

---

## Troubleshooting

### `Model root not found` / unable to locate `current_model`

1. Run any script and read the **Deployment Configuration** summary.  
2. Confirm a single `current_model` exists under `application_directory`.  
3. Set explicit path segments in `config.yaml`:

```yaml
application_directory: "/opt/steel-beam-estimation"
repository_directory: "SteelBeamEstimator"
project_directory: "Steel-Beam-Estimation"
model_directory: "current_model"
```

4. Or remove duplicate `current_model` trees so auto-discovery can pick one.

### Virtualenv path wrong

Always use `03_create_venv.sh` after pulling D.4.1 — it creates/reuses `${MODEL_ROOT}/.venv`.

### Nginx static files 404

`08_install_nginx.sh` renders `__APP_ROOT__` as `PROJECT_ROOT`. Re-run 08 after path fixes.

---

## Script catalogue

| Script | Purpose |
|--------|---------|
| `_common.sh` | Config + path resolution + summary (only path calculator) |
| `01_server_setup.sh` | OS packages |
| `02_clone_project.sh` | Clone / pull repository |
| `03_create_venv.sh` | Create or reuse venv at `MODEL_ROOT` |
| `04_install_requirements.sh` | pip install |
| `05_configure_environment.sh` | `.env` from example if missing |
| `06_validate_application.sh` | Packaging checks |
| `07_install_gunicorn.sh` | gunicorn + systemd unit |
| `08_install_nginx.sh` | nginx site |
| `09_restart_services.sh` | Restart + `/health` |
| `10_update_application.sh` | Pull + refresh + restart |

---

## Local packaging checklist (D.3)

Still valid for laptop validation — see earlier checklist in ReleaseNotes. Use `python run.py` under `current_model/` with `.env` configured.

---

## Phase roadmap

| Phase | Status |
|-------|--------|
| D.1–D.3 | Done |
| D.4 | Done (assets) |
| **D.4.1** | **Done** (layout-independent paths) |
| D.5+ | Lightsail cutover / TLS (planned) |

---

## Related docs

- [Architecture.md](Architecture.md)
- [../deployment/README.md](../deployment/README.md)
- [ReleaseNotes.md](ReleaseNotes.md)
