# PHASE W.7 — DEPLOYMENT INVENTORY

Prepared: 2026-08-25  
Remote tree: `/opt/steel-beam-estimation/SteelBeamEstimator/Version10/`

This inventory is the W.6 Hybrid production-authority runtime plus W.7 coverage/health labels. It is not a full Version10 re-copy.

## A. DEPLOY REQUIRED

### New package (absent on Lightsail)

```
Version10/src/PhaseW6_hybrid_production_authority/
  __init__.py
  __main__.py
  config.py
  coverage.py
  handoff.py
  observability.py
  orchestrator.py
  visuals.py
```

`unit_tests.py` is local-only and is not required on the instance.

```
Version10/Run_PY/run_phase_w6_hybrid_production_authority.py
```

### Updated W.5 Hybrid adapter (already on Lightsail; overwrite)

```
Version10/src/PhaseW5_production_hybrid_shadow/
  adapter.py
  catalog.py
  comparison.py
  config.py
  cost.py
  live_invoke.py
  paths.py
  semantic.py
  settings.py
  visual_sources.py
  __init__.py
  __main__.py
```

### Web / pipeline wiring

```
Version10/webapp/config.py
Version10/webapp/routes.py
Version10/webapp/services/estimation_service.py
Version10/webapp/services/version10_adapter.py
Version10/webapp/services/hybrid_shadow_service.py
Version10/src/config/run_context.py
```

### systemd / env template

```
Version10/webapp/deployment/steel-beam-estimator-v10.service
Version10/webapp/deployment/steel-beam-estimator-v10.env.example
```

The live unit file `/etc/systemd/system/steel-beam-estimator-v10.service` is updated to the W.7 comment + same runtime flags (`workers=1`, `HYBRID_MODE=off` default, EnvironmentFile).

`/etc/steel-beam-estimator-v10.env` is rewritten on the instance (not from git): `HYBRID_MODE` (`off` then `production`), `ANTHROPIC_API_KEY` present, production caps `HYBRID_MAX_LIVE_CALLS=0` / `HYBRID_MAX_WALL_S=0`, `chmod 600`. The workstation `.env` file itself is not copied.

### Python dependency pin (required for live Claude)

```
Version10/requirements.txt
```

`anthropic` is pinned to `>=0.49.0,<1`. The W.3 venv had resolved `anthropic==1.0.0`, which is incompatible with the existing C.5/P253 client (`ClaudeAPIError` in 0.000 s, 0 tokens). Production venv was updated to `anthropic==0.125.0`. Do not allow `anthropic>=1` on Lightsail.

## B. ALREADY ON INSTANCE — DO NOT RECOPY UNLESS MISSING

- `src/PhaseM.1_engineering_vision_dataset/` (W.6 crop fallback renderer)
- T1 / VB.1 / remaining production runners
- `webapp/.venv` (created in W.3 from `Version10/requirements.txt`, includes `anthropic` and `python-dotenv`)
- Nginx site (upstream already `:8001`)
- First Set DXFs under `/home/ubuntu/w3_smoke/smoke/`

## C. DO NOT DEPLOY

- `C:\Users\nishanth.h\SteelBeamEstimator\.env` (or any filled dotenv)
- API keys in git or reports
- `__pycache__/`, `*.pyc`
- local `.venv`
- `Version10/data/web_runs/`
- `Version10/data/output/` research / benchmark trees
- `src/PhaseP2610*`
- `Test_Input/`
- webapp `uploads/`, `outputs/`, `logs/` contents
- old 8.9.x tree / W.3 rollback copies

## D. DEPLOY METHOD

1. Build a file-list tarball locally (`w7_runtime.tar.gz`), excluding `__pycache__` and `.env`.
2. `scp` to `/tmp/w7_runtime.tar.gz`.
3. Extract into `/opt/steel-beam-estimation/SteelBeamEstimator/Version10/`.
4. Install `/etc/systemd/system/steel-beam-estimator-v10.service` from the extracted copy.
5. Install `/etc/steel-beam-estimator-v10.env` via a one-shot temp file (never echo the key).
6. `systemctl daemon-reload && systemctl restart steel-beam-estimator-v10`.
7. Validate Hybrid **off** before flipping to `production`.

## E. VERIFY AFTER COPY

- `PhaseW6_hybrid_production_authority/orchestrator.py` exists
- `Run_PY/run_phase_w6_hybrid_production_authority.py` exists
- `webapp/config.py` contains `APP_RELEASE = "W.7"` and a HYBRID stage between R13 and VB1
- Public `/health` `phase=W.7`, `hybrid.mode=off`, `api_key_configured=true` (boolean only)
