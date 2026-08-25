# PHASE W.5 — CHECKPOINT

Saved: 2026-08-25  
Classification: **W5_PASS_SHADOW_READY**

## Implementation state

Hybrid shadow adapter is in `Version10/src/PhaseW5_production_hybrid_shadow/`.  
Web wrapper: `Version10/webapp/services/hybrid_shadow_service.py`.  
Excel path still `PRODUCTION_STAGES` only. Shadow runs after Excel success.  
`HYBRID_MODE=authoritative` is refused.

Local tests: PhaseW5 unit tests 12/12 PASS; Flask W.5 + W.2 15/15 PASS.

## Deployment state

| Item | State |
|------|--------|
| Public URL | http://13.127.104.99/ |
| `/health` | `phase=W.5`, `app_release=W.5`, `status=ok` |
| Gunicorn | `127.0.0.1:8001`, `steel-beam-estimator-v10` active+enabled |
| Hybrid mode | **off** |
| API key in systemd env | **ABSENT** |
| `/etc/steel-beam-estimator-v10.env` | present, `HYBRID_MODE=off`, no key lines |
| Old 8.9.x | still on `127.0.0.1:8000`, service active |
| Nginx | unchanged (still Version10 :8001) |
| W.3 rollback copies | `/opt/steel-beam-estimation/rollback-w3/` present |
| Instance size | still 2 GB; not resized |

## Hybrid mode

**off** on public production. Shadow code is loaded but does not call Claude.

## Configuration status

- systemd unit updated to `Environment=HYBRID_MODE=off` and `EnvironmentFile=-/etc/steel-beam-estimator-v10.env`
- Example: `Version10/webapp/deployment/steel-beam-estimator-v10.env.example`
- Do not put keys in git or `webapp/.env`

## Validation status

| Gate | Status |
|------|--------|
| Local TEST 1–5 | PASS (TEST 2 = mock client) |
| Production HYBRID_MODE=off | PASS |
| Production live shadow | NOT ENABLED |
| Live Anthropic from this phase | NONE |

## Exact rollback procedure

**A. Return public app to W.3 behaviour without removing W.5 files**

Keep Nginx on :8001. Set `/etc/steel-beam-estimator-v10.env` to `HYBRID_MODE=off` (already). Restart is optional if already off.

**B. Nginx rollback to 8.9.x (unchanged from W.3)**

```bash
sudo cp /opt/steel-beam-estimation/rollback-w3/steel-beam-estimator.conf \
        /etc/nginx/sites-available/steel-beam-estimator.conf
sudo nginx -t && sudo systemctl reload nginx
```

Do not delete Version 8.9.x or the Version10 tree.

**C. Restore previous v10 unit (if needed)**

The previous unit lacked `/etc/steel-beam-estimator-v10.env` and `HYBRID_MODE`. Copy from git history of `steel-beam-estimator-v10.service` if required, then `daemon-reload` + restart.

## Next safe action

1. Keep public `HYBRID_MODE=off`.
2. If live shadow evidence is wanted: add the key only to `/etc/steel-beam-estimator-v10.env`, leave Gunicorn mode **off**, and run the post-hoc module on one existing `web_runs/<run_id>` with `HYBRID_MAX_LIVE_CALLS=3`.
3. Do not set `HYBRID_MODE=shadow` on the systemd service until that post-hoc sample is reviewed.

See `PHASE_W5_HYBRID_SHADOW_VALIDATION_REPORT.md`.
