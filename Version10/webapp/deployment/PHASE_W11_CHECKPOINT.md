# PHASE W.11 CHECKPOINT

Saved: 2026-08-26  
Classification: **W11_PASS_RELIABILITY_HARDENED**

Public: http://13.127.104.99/

## Production

| Item | Value |
|------|--------|
| Version | W.11 |
| Mode | `HYBRID_MODE=production` |
| Health | `status=ok`, `phase=W.11`, `app_release=W.11` |
| Key | PRESENT (value not recorded) |
| Anthropic | 0.125.0 |
| Workers | 1 (`127.0.0.1:8001`) |
| `HYBRID_PER_CALL_TIMEOUT_S` | 120 |
| `HYBRID_MAX_RETRIES` | 1 |
| `HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS` | 250 |
| `HYBRID_EVIDENCE_TIMEOUT_SECONDS` | 120 |
| `HYBRID_MAX_WALL_S` | 0 (per-call still bounded) |
| `HYBRID_MAX_LIVE_CALLS` | 0 (count unlimited; each call bounded) |

## Rollback

1. `HYBRID_MODE=off` in `/etc/steel-beam-estimator-v10.env` and `systemctl restart steel-beam-estimator-v10` (tested).
2. File rollback from `/opt/steel-beam-estimation/backups/w11_predeploy_20260826T102128Z`.
3. Do not delete 8.9.x on `:8000`.

Restore Hybrid by setting `HYBRID_MODE=production` and restarting (tested).

## Canonical runs

| Run | Role |
|-----|------|
| `20260826_084708_f74912b8` | Stuck-run forensic (143 beams, completed) |
| `20260826_102310_1a616a17` | W.11 controlled First Set smoke |

Nothing committed in this phase unless requested.
