# PHASE W.3 — CHECKPOINT (saved 2026-08-24, laptop sleep)

Do not treat this as the final delivery report. Public traffic was NOT switched.

## Resume from here

1. Confirm Version10 Gunicorn still answers: `curl -sS http://127.0.0.1:8001/health` (SSH to 13.127.104.99).
2. If 8001 is down, restart from `/opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp`:
   `nohup .venv/bin/gunicorn --config deployment/gunicorn.w3.conf.py --workers 1 --timeout 3600 --bind 127.0.0.1:8001 wsgi:app > /tmp/v10_gunicorn.log 2>&1 &`
3. Install systemd unit `steel-beam-estimator-v10.service` (not done — auto-review blocked).
4. `nginx -t` on `deployment/nginx-v10.conf`, then switch upstream 8000 → 8001.
5. Verify `http://13.127.104.99/` and `/health` show Version10 / W.3.
6. Keep 8.9.5 running on 127.0.0.1:8000 for rollback.
7. Write PHASE W.3 FINAL DELIVERY REPORT.

## What is already done (evidence)

- SSH: `ubuntu@13.127.104.99` with `%USERPROFILE%\.ssh\LightsailDefaultKey-ap-south-1.pem`
- Old app still public on port 80 → Gunicorn 127.0.0.1:8000 (Version8 / model 8.9.4, phase D.4.2)
- Version10 extracted to `/opt/steel-beam-estimation/SteelBeamEstimator/Version10`
- venv Python 3.12.3, declared deps installed, T1 imports OK
- Version10 Gunicorn (manual nohup, 1 worker) on **127.0.0.1:8001**
- Rollback copies: `/opt/steel-beam-estimation/rollback-w3/`
- Lightsail snapshot: **NOT created** (no AWS CLI/credentials on this workstation)

### Small smoke — PASS

- run_id `20260824_120944_1498af3a`
- 18 beams / 92 bars / 1424.397 kg
- duration 24.58 s; T1 12.53 s
- Excel PK, 19561 bytes
- BUSY 409 confirmed; sequential second run `20260824_121014_8338f856` accepted

### Fifth Set — PASS (loopback, not public)

- run_id `20260824_124732_f0dfc013`
- 26.11 MB DXF; 143 beams / 818 bars / 36271.834 kg
- duration **373.98 s**; T1 **328.86 s** (~88% of runtime)
- T1 window memory: used **957 MB**, available **950 MB** of 1907 MB, no swap
- Classification from this observation: **2 GB PASS WITH MODERATE RISK**
- Public URL still 8.9.5

## Remaining ETA after resume

About **25–40 minutes** of deployment work:

| Step | ETA |
|------|-----|
| Confirm 8001 still up / restart if needed | 2–5 min |
| systemd unit enable/start | 5–10 min |
| Nginx switch + public /health + UI check | 5–10 min |
| Final W.3 report + test matrix | 10–15 min |

If 8001 died during sleep, add ~5 minutes to restart Gunicorn before the switch.

## Do not do on resume

- Do not delete 8.9.5
- Do not overwrite `/opt/.../current_model`
- Do not raise Gunicorn workers above 1
- Do not modify T1 / VB.1 / hybrid / engineering logic
