# PHASE W.9 — CHECKPOINT

Status: **COMPLETE**  
Classification: **W9_PASS_PRODUCTION_GO_LIVE**  
Date: 2026-08-26

Public: http://13.127.104.99/  
`/health`: `status=ok`, `phase=W.9`, `app_release=W.9`, `hybrid.mode=production`, `api_key_status=PRESENT`

## Deployed

W.8 runtime evidence adapter + Hybrid wiring + P2.6.10 A/B/B.2/C1C2/C3 **functions** (not research orchestrators). Production C1C2/B2/C3 `__init__.py` stubs avoid loading research orchestrators.

Backup: `/opt/steel-beam-estimation/backups/w9_predeploy_20260826T064810Z`

Canonical run: `20260826_065256_4ba41266`  
18/18 Claude, 13 P2.6.10 primary, 5 explicit fallbacks, unexplained=0, Excel 1425.732 kg.

## Rollback (no code deletion)

1. In `/etc/steel-beam-estimator-v10.env` set `HYBRID_MODE=off`
2. `sudo systemctl restart steel-beam-estimator-v10`
3. File rollback if needed: restore from `w9_predeploy_20260826T064810Z`

Do **not** install `anthropic` 1.x. Do **not** copy workstation `.env`.

## Next step

No further deployment phase is required. Monitor production evidence quality, review the five explicit fallback beams, and measure Hybrid semantic benefit/cost over accumulated runs.
