# Steel Beam Reinforcement Estimation

Production deployment package for the **Steel Beam Reinforcement Estimation** system.

Independent from the Concrete & Shuttering Estimation deployment.
Uses a **version-agnostic** `current_model/` slot so engine upgrades do not change infrastructure.

---

## Phase status

| Phase | Scope | Status |
|-------|--------|--------|
| D.1 | Project foundation & folder structure | Complete |
| D.2 | Application foundation & local execution | Complete |
| D.3 | Production packaging & deployment readiness | Complete |
| D.4 | Generate gunicorn/nginx/systemd + deploy scripts | Complete |
| **D.4.1** | Path abstraction & existing-install support | Complete |
| **D.4.2** | Lightsail upload / engine wiring fix | Complete |
| **D.5.1** | Per-run web pipeline (R.2.1B + R.2.1C) | Complete |
| **D.5.2** | Web-enable R.2.1D (Evidence & Hypothesis) | Complete |
| **D.5.3** | Web-enable L.2.2 (Geometry Registry) | Complete |
| **D.5.4** | Web-enable R.3 (Geometry Context) | Complete |
| **D.5.5** | Downstream through Excel (R.3.1→VB.1) | Complete |
| **D.5.6** | Production validation & cleanup | **Complete** |
| **8.9.5** | **Stable production baseline** | **Certified** |
| Future | Accuracy / performance / TLS cutover | Planned (separate) |

**Production baseline:** MODEL_VERSION **8.9.5** — web-native, run-scoped
pipeline (upload → Excel). Architecture:
[docs/Production_Architecture_8.9.5.md](docs/Production_Architecture_8.9.5.md).  
Cleanup record: [docs/Phase_D.5.6_Production_Validation_Cleanup.md](docs/Phase_D.5.6_Production_Validation_Cleanup.md).

---

## Folder overview

```text
Steel-Beam-Estimation/
├── current_model/     Active app + estimation engine slot
├── deployment/        AWS / process / reverse-proxy configs (later phases)
├── docs/
├── tests/
├── README.md
├── LICENSE
└── .gitignore
```

### `current_model/` (D.2 application layer)

| Path | Purpose |
|------|---------|
| `webapp/` | Flask app (`app.py`, `routes.py`, `services.py`, logging) |
| `config/` | `settings.py`, `paths.py`, `model_info.yaml` |
| `templates/` / `static/` | UI assets |
| `inputs/` `outputs/` `logs/` `temp/` | Runtime folders (auto-created) |
| `run.py` | Local entry: `python run.py` |
| `wsgi.py` | Production WSGI entry (gunicorn in later phase) |
| `requirements.txt` | App dependencies |
| `.env.example` | Environment template |

---

## Local setup (Phase D.2)

```powershell
cd Steel-Beam-Estimation\current_model

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

copy .env.example .env
# Edit .env:
#   SECRET_KEY=...
#   STEEL_ENGINE_ROOT=<absolute path to engine folder with Run_PY/>
```

### Run locally

```powershell
python run.py
```

Open: **http://127.0.0.1:5000**

Health check: **http://127.0.0.1:5000/health**

### Engine root (important)

Deployment never hardcodes model version folder names.

Point the app at the active engine with one of:

1. `STEEL_ENGINE_ROOT` in `.env`, or  
2. Package `Run_PY/` + `src/` inside `current_model/`, or  
3. Optional local file `config/engine_root.path` (gitignored)

---

## Design principles

1. **No version names in deployment logic** — always `current_model/` + configurable `STEEL_ENGINE_ROOT`.
2. **Application framework only in D.2** — estimation runners are invoked unchanged via subprocess.
3. **Centralised configuration** — folders, limits, and secrets come from `config/settings.py` + `.env`.
4. **Independent of Concrete Estimator** — separate app and paths.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/Architecture.md](docs/Architecture.md) | System architecture |
| [docs/DeploymentGuide.md](docs/DeploymentGuide.md) | AWS Lightsail guide (placeholders) |
| [docs/ReleaseNotes.md](docs/ReleaseNotes.md) | Release notes |
| [deployment/README.md](deployment/README.md) | Deployment folder guide |

---

## License

See [LICENSE](LICENSE).
