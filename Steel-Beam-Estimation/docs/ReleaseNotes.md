# Release Notes — Steel-Beam-Estimation

## D.5.5 — Downstream Pipeline through Excel (2026-07-29)

### Added

- Run-scoped R.3.1, R.1.2A (catalog-only), R.1.3 (build-only), VB.1
- Production stages extended through Excel generation
- Download restores `Estimation_Output.xlsx` from the same uploaded run

### Changed

- Downstream I/O only — steel / BBS / Excel engineering logic unchanged
- Removed nested VB.1 from web R.1.3; removed R13/VB1 rebuild from web R.1.2A
- Success means run-scoped workbook exists (not R.3-only soft stop)

### MODEL_VERSION

`8.9.4`

### Docs

See [Phase_D.5.5_Web_Pipeline_Completion.md](Phase_D.5.5_Web_Pipeline_Completion.md)

---

## D.5.4 — Web-enable R.3 Geometry Context Engine (2026-07-28)

### Added

- Run-scoped Phase R.3 via `RunContext` / `PHASE_R3`
- Production stages extended through R.3 (stop; R.3.1 / Excel deferred)
- Success artefact: `PhaseR3_geometry_context_engine/GeometryContexts.json`

### Changed

- R.3 I/O only — geometry context engineering logic unchanged
- Removed `_find_output()`, `version7_root`, shared workbook search from R.3

### MODEL_VERSION

`8.9.3`

### Docs

See [Phase_D.5.4_Web_Pipeline_Completion.md](Phase_D.5.4_Web_Pipeline_Completion.md)

---

## D.5.3 — Web-enable L.2.2 Geometry Registry (2026-07-28)

### Added

- Version8 `PhaseL.2.2_geometry_recovery` (RunContext; VROOT1 → registry)
- Production stages extended through L.2.2 (stop; R.3 / Excel deferred)
- Success artefacts: R.2.1D `EngineeringFacts.json` **and**
  `PhaseL.2.2_.../geometry_registry.json` under the run tree

### Changed

- L.2.2 input wiring uses VROOT1 (R-spine), not L.2 / L.2.1 / Version5
- Registry schema / axis / default supports preserved for R.3 consumers

### MODEL_VERSION

`8.9.2`

### Docs

See [Phase_D.5.3_Web_Pipeline_Completion.md](Phase_D.5.3_Web_Pipeline_Completion.md)

---

## D.5.2 — Web-enable R.2.1D Evidence & Hypothesis Engine (2026-07-28)

### Added

- Run-scoped Phase R.2.1D via `RunContext` / `PHASE_R21D`
- Production stages extended through R.2.1D (stop; L.2.2 / R.3 / Excel deferred)
- Success artefact: `web_runs/<run_id>/data/output/PhaseR2.1D_.../EngineeringFacts.json`

### Changed

- R.2.1D I/O only — evidence / hypothesis engineering logic unchanged
- Removed Version7 / shared-output hardcodes from R.2.1D orchestrator

### MODEL_VERSION

`8.9.1`

### Docs

See [Phase_D.5.2_Web_Pipeline_Completion.md](Phase_D.5.2_Web_Pipeline_Completion.md)

---

## D.5.1 — Web Pipeline Completion Foundation (2026-07-28)

### Added

- Per-run output tree under `Version8/data/web_runs/<run_id>/data/output/`
- Shared `RunContext` (`STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT`)
- Web-capable R.2.1B + R.2.1C (I/O only; engineering logic unchanged)
- Production stages truncated at R.2.1C (Excel deferred)

### MODEL_VERSION

`8.9.0`

### Docs

See [Phase_D.5.1_Web_Pipeline_Completion.md](Phase_D.5.1_Web_Pipeline_Completion.md)

---

## D.4.2.1 — Restore Version7 R.3 artefact seeding (2026-07-28)

### Fixed

- `_ensure_r3_prerequisites()` in `current_model/webapp/services.py` now matches
  the local `Version8/webapp` behaviour: copy missing
  `EngineeringFacts.json` / `geometry_registry.json` from sibling `Version7/`
  into `Version8/data/output/...` (no `STEEL_ARTEFACT_SEED_ROOT` required).

---

## D.4.2 — Lightsail upload / engine wiring fix (2026-07-28)

### Root cause addressed

- Deployed app is `current_model` (gunicorn), **not** `Version8/webapp`
- Uploads stage to `{STEEL_ENGINE_ROOT}/data/web_runs/<run_id>/`, audit copies to `current_model/uploads/`
- Empty `Version8/webapp/uploads` and `current_model/data/web_runs` after Generate were expected (wrong folders + post-run cleanup)
- VROOT1 `0 text / 0 beams` matched missing `ezdxf` in the app venv (`04` never read `.env` / sibling Version8)

### Fixed

- Auto-discover monorepo sibling `Version8` in `config/paths.py`
- `.env.example` restored; `05` upserts absolute `STEEL_ENGINE_ROOT`
- `04` installs `Version8/requirements.txt` from `.env` or sibling engine
- Upload byte-size verification + absolute staging path for VROOT1
- Keep `web_runs` / `uploads` on failure (and when `STEEL_KEEP_WEB_RUNS=1`)
- Gunicorn default workers = 1 (in-memory job store)
- `/health` reports `engine_root`, `web_runs_root`, `upload_folder`, `ezdxf_available`

### Deployment package version

`D.4.2`

---

## D.4.1 — Path abstraction & existing-install support (2026-07-28)

### Changed

- `_common.sh` is the single path-resolution layer (config + auto-discovery)
- `config.yaml` adds `repository_directory`, `project_directory`, `model_directory`
- Scripts `01`–`10` no longer hardcode `Steel-Beam-Estimation/current_model`
- Clone script supports pull / clone / unrelated-dir abort / remote mismatch
- Venv script reuses existing venv at resolved `MODEL_ROOT`
- Deployment summary printed before each script
- Actionable diagnostics when `current_model` cannot be located

### Compatibility

- Legacy `app_subdirectory` / `model_subdirectory` still accepted
- Existing Lightsail layout `…/SteelBeamEstimator/Steel-Beam-Estimation/current_model` works via config or auto-detect

### Deployment package version

`D.4.1` (see `deployment/config.yaml` → `deployment_package_version`)

---

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
