# PHASE W.8 — PRE-DEPLOYMENT CHECKPOINT (LOCAL DRY RUN)

Prepared: 2026-08-25 after local TEST-W8-13 PASS.

Lightsail was **not mutated** in this session. Remote inspect/SCP was not completed from this workstation session, so live systemd/env values below are the last known-good W.7 go-live state (2026-08-25), to be re-verified immediately before any copy.

## Last known production (W.7 go-live)

| Item | Last known |
|---|---|
| Public | http://13.127.104.99/ |
| `/health` phase | W.7 |
| `HYBRID_MODE` | production |
| Gunicorn | 1 worker, `127.0.0.1:8001` |
| systemd | `steel-beam-estimator-v10.service` |
| Secret file | `/etc/steel-beam-estimator-v10.env` chmod 600 |
| `anthropic` | 0.125.0 (`>=0.49.0,<1`) |
| Canonical W.7 run | `20260825_113725_9a8d6014` |

Re-verify all of the above over SSH before copying files.

## Changed files to deploy (W.8 runtime only)

Local pack: `C:\Users\nishanth.h\AppData\Local\Temp\w8_runtime.tar.gz` (50 files).

Do not deploy: `.env`, venv, `__pycache__`, `data/web_runs`, research `data/output`, unit tests.

New:

- `src/PhaseW8_production_vision_evidence/{__init__,config,generator,package}.py`

Updated Hybrid wiring:

- `src/PhaseW6_hybrid_production_authority/{visuals,coverage,orchestrator}.py`
- `src/PhaseW5_production_hybrid_shadow/{adapter,live_invoke,visual_sources}.py`
- `src/PhaseP2610E2_.../live_caller.py` (optional context/detail paths)
- `webapp/config.py` (`APP_RELEASE=W.8`)
- `webapp/routes.py` (`phase=W.8`)
- `webapp/deployment/steel-beam-estimator-v10.service` (comment only)

P2.6.10 functions reused (copy if missing on the instance):

- A: `title_localizer.py`, `region_builder.py`, `cropper.py`, `config.py`
- B: `envelope.py`, `evidence.py`, `completeness.py`, `config.py`
- B.2: `quality.py`, `geometry.py`, `config.py`
- C1C2: `selector.py`, `inventory.py`, `config.py`
- C.3: `visual_completeness_gate.py`, `evidence_model.py`, `target_anchor_validator.py`, `config.py`

Do not copy C1–C5 research orchestrators.

## Environment / systemd

- Do not copy workstation `.env`
- Do not change `/etc/steel-beam-estimator-v10.env` unless `HYBRID_MODE=production` is already set (it was, at W.7 go-live)
- Do not change workers, Nginx, or the API key
- Restart Gunicorn only after files are in place (`systemctl restart steel-beam-estimator-v10`)
- Confirm `anthropic==0.125.0` and do **not** install 1.x

## Rollback

1. Restore the W.7 tarball / previous copies of the files listed above.
2. `APP_RELEASE` / `/health` `phase` back to W.7.
3. Restart Gunicorn.
4. Leave `HYBRID_MODE=production` if that was the pre-W.8 production setting.

Old 8.9.x on `:8000` remains the engine rollback; do not delete it.
