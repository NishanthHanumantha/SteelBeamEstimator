# PHASE W.12 — PRODUCTION DEPLOYMENT REPORT

Saved: 2026-08-26  
Public: http://13.127.104.99/

---

## Pre-deploy audit (W.11 live)

| Item | Value |
|------|--------|
| `/health` phase | W.11 |
| `HYBRID_MODE` | production |
| Workers | 1 (`127.0.0.1:8001`) |
| Anthropic | 0.125.0 (`<1`) |
| API key | PRESENT (value not recorded) |
| Busy | false |

Sixth Set Excel from W.11 already on disk: `Estimation_Output_20260826_084708_f74912b8.xlsx` (85,800 bytes). Status/download 404 before W.12 because `_JOBS` was empty.

---

## Backup

`/opt/steel-beam-estimation/backups/w12_predeploy_20260826T110729Z`

Contains previous runtime files and `health_before.json`. `/etc/steel-beam-estimator-v10.env` was **not** replaced. No local `.env` copied. No API keys copied.

---

## Runtime files deployed (minimum)

- `webapp/config.py` (APP_RELEASE W.12)
- `webapp/routes.py`
- `webapp/templates/index.html`
- `webapp/static/js/app.js`
- `webapp/static/css/app.css`
- `webapp/services/estimation_service.py`
- `webapp/services/result_registry.py`
- `webapp/deployment/steel-beam-estimator-v10.service`

Pack: `pack_w12.py` → `/tmp/w12_runtime.tar.gz`. Nginx **not** modified.

---

## Post-deploy

| Item | Value |
|------|--------|
| Unit | `steel-beam-estimator-v10.service` active |
| `/health` | `status=ok`, `phase=W.12`, `app_release=W.12` |
| `result_delivery` | `durable_registry=true`, `download_reconstructs_from_disk=true` |
| `HYBRID_MODE` | production |
| Workers | 1 |
| Anthropic | 0.125.0 |
| Key | PRESENT |
| Home | Version10 production pipeline, Download Excel is a button |

---

## Rollback test

1. Set `HYBRID_MODE=off`, restart → `/health` hybrid `mode=off`.
2. Restore `HYBRID_MODE=production`, restart → `mode=production`.
3. After both restarts, Sixth Set artefact `20260826_084708_f74912b8` still downloaded HTTP 200 / PK.

File rollback remains: restore from `w12_predeploy_20260826T110729Z`. Do not delete 8.9.x on `:8000`.

---

## Final production state

W.12, `HYBRID_MODE=production`, 1 worker, anthropic 0.125.0, key PRESENT, result registry on disk.
