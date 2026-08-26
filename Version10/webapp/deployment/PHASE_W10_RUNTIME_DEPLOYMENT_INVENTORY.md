# PHASE W.10 — RUNTIME DEPLOYMENT INVENTORY

Local validation: W.10 + W.6 unit tests OK. Crop generation: **NO CHANGE**.

## A. REQUIRED RUNTIME (new)

- `src/PhaseW10_hybrid_production_monitoring/{__init__,__main__,config,monitor,sanitize,writer}.py`

## B. EXISTING PRODUCTION FILE — UPDATED

- `src/PhaseW6_hybrid_production_authority/orchestrator.py` — time evidence prep; fail-safe W.10 write after persist
- `webapp/config.py` — `APP_RELEASE = "W.10"`
- `webapp/routes.py` — `/health` `phase=W.10`
- `webapp/deployment/steel-beam-estimator-v10.service` — comment only; still `--workers 1`

## C. TEST ONLY — DO NOT DEPLOY

- `src/PhaseW10_hybrid_production_monitoring/unit_tests.py`
- `webapp/tests/test_w5_hybrid_shadow.py` / `test_w6_hybrid_authority.py` (label-only)

## D. RESEARCH / CROP — DO NOT DEPLOY

No P2.6.10 / C1 / C2 / C3 / C.5 / E.2 / VB.1 changes.

## E. NOT TOUCHED

- `/etc/steel-beam-estimator-v10.env`
- Nginx, worker count, anthropic pin

Rollback files: `/opt/steel-beam-estimation/backups/w10_predeploy_*`
Primary Hybrid rollback remains `HYBRID_MODE=off`.
