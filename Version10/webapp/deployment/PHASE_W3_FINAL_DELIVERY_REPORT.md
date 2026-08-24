# PHASE W.3 — FINAL DELIVERY REPORT

## 1. Deployment Status

**GO WITH KNOWN LIMITATIONS**

Public URL http://13.127.104.99/ now serves Version10 (release W.3). The previous 8.9.5/Version8 application remains running on loopback `:8000` as a rollback target. A Lightsail disk snapshot was not created (no AWS CLI/credentials on the deployment workstation).

## 2. Lightsail Baseline

Inspected 2026-08-24 before any Version10 copy:

| Item | Observed |
|------|----------|
| Instance | Steel-Beam-Estimator (`ip-172-26-15-118`), Ubuntu 24.04, kernel 6.17.0-1010-aws |
| Public IP | 13.127.104.99 (unchanged) |
| Size | 2 vCPU, **1907 MB RAM**, 0 swap, 58G disk (~3.9G used / 54G free at baseline; **4.6G used / 53G free / 8%** after deploy) |
| Python | **3.12.3** (`python3` and `python3.12`) |
| Old application directory | `/opt/steel-beam-estimation/SteelBeamEstimator/Steel-Beam-Estimation/current_model` |
| Old engine | `/opt/steel-beam-estimation/SteelBeamEstimator/Version8` |
| Old venv | `current_model/.venv` |
| Old systemd | `steel-beam-estimator.service` (Gunicorn bind `127.0.0.1:8000`, workers=1, timeout 3600) |
| Old Nginx | `/etc/nginx/sites-enabled/steel-beam-estimator.conf` — `client_max_body_size 256M`, `proxy_read_timeout`/`proxy_send_timeout` 3600s, upstream `127.0.0.1:8000` |
| Old public `/health` | `engine_root=.../Version8`, `model_version=8.9.4`, `phase=D.4.2` |

The live old application identified itself as **8.9.4 / Version8**, not the 8.9.5 label used in planning docs. It was left unmodified.

## 3. Rollback Protection

| Item | Status |
|------|--------|
| Lightsail snapshot | **Not created.** AWS CLI is not installed and `~/.aws` is absent. No snapshot was claimed. |
| Old deployment directory | Intact: `.../Steel-Beam-Estimation/current_model` |
| Old service | `steel-beam-estimator.service` still **active** on `127.0.0.1:8000` |
| Config copies | `/opt/steel-beam-estimation/rollback-w3/steel-beam-estimator.service` and `steel-beam-estimator.conf` |

Console action still recommended (not blocking now that traffic is switched via Nginx only):

Lightsail → Instances → Steel-Beam-Estimator → Snapshots → Create snapshot

## 4. Version10 Deployment Architecture

Browser
→ Nginx (`13.127.104.99:80`, `client_max_body_size 256M`, proxy timeouts 3600s)
→ Version10 Gunicorn (`127.0.0.1:8001`, workers=1, timeout=3600)
→ Flask (`wsgi:app`)
→ Version10 adapter (`start_estimation` / single-flight)
→ Run_PY production stages under RunContext
→ T1
→ remaining production stages
→ VB.1 Excel
→ downloadable workbook

Canonical stages (unchanged): VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → VB1

T16CHAIN is not on this path. Hybrid D/E is not invoked.

## 5. Deployment Paths

| Role | Path / value |
|------|----------------|
| Version10 root | `/opt/steel-beam-estimation/SteelBeamEstimator/Version10` |
| Webapp | `.../Version10/webapp` |
| venv | `.../Version10/webapp/.venv` (Python 3.12.3) |
| systemd | `steel-beam-estimator-v10.service` (enabled, active) |
| Gunicorn bind | `127.0.0.1:8001` (not public) |
| Gunicorn config | `.../webapp/deployment/gunicorn.w3.conf.py` |
| Nginx upstream | `127.0.0.1:8001` |
| Web runs | `.../Version10/data/web_runs/<run_id>/` |
| Old Gunicorn (rollback) | `127.0.0.1:8000` |

## 6. Dependency Validation

Python **3.12.3**. Installed from `Version10/requirements.txt` then `Version10/webapp/requirements.txt` with no undeclared extras.

| Package | Version on instance |
|---------|---------------------|
| Flask | 3.1.3 |
| gunicorn | 26.1.0 |
| ezdxf | 1.4.4 |
| pandas | 3.0.5 |
| numpy | 2.5.2 |
| openpyxl | 3.1.5 |
| shapely | 2.1.2 |
| pydantic | 2.13.4 |
| PyYAML | 6.0.3 |
| matplotlib | 3.11.1 |
| Pillow | 12.3.0 |
| opencv-python-headless | 5.0.0.93 (`cv2` 5.0.0) |

`from wsgi import app` loaded successfully. T1-critical imports succeeded.

## 7. Gunicorn Validation

Command (systemd):

```
.../webapp/.venv/bin/gunicorn \
  --config .../deployment/gunicorn.w3.conf.py \
  --workers 1 --timeout 3600 --bind 127.0.0.1:8001 \
  wsgi:app
```

| Check | Result |
|-------|--------|
| Worker count | **1** worker process (master 152912 + worker 152913) |
| Timeout | 3600 |
| Bind | 127.0.0.1:8001 only |
| Health | `status=ok`, `engine_label=Version10`, `engine_root=.../Version10`, `t1_included=true`, stages include T1 and VB1 |
| systemd | `active (running)`, `enabled`, Type=notify |

Gunicorn logged `Using worker: gthread` because `threads=4`. That is still **one** worker process.

## 8. Small Smoke Test

First Set (`1st Set Drawings-Galera_OHT&STP`), loopback `:8001`.

| Field | Value |
|-------|--------|
| run_id | `20260824_120944_1498af3a` |
| stages | VROOT1, R1, T1, R2A, R21B, R21C, R21D, L22, R3, R31, R12A, R13, VB1 |
| runtime | 24.58 s |
| T1 | 12.53 s, `t1_executed=true`, artefact present |
| beams / bars / kg | 18 / 92 / 1424.397 |
| Excel | HTTP 200, PK zip, 19561 bytes, `Estimation_Output_20260824_120944_1498af3a.xlsx` |
| Sequential second run | `20260824_121014_8338f856` accepted after first completed (22.92 s) |

## 9. Production-Scale Validation

Fifth Set Drawings, loopback `:8001` (not fabricated).

| Field | Value |
|-------|--------|
| test set | Fifth Set Drawings |
| DXF size | 26.11 MB |
| run_id | `20260824_124732_f0dfc013` |
| beam count | 143 |
| bars | 818 |
| steel | 36271.834 kg |
| runtime | **373.98 s** |
| T1 duration | **328.86 s** (~88%) |
| Excel | 91188 bytes on disk (`Estimation_Output_20260824_124732_f0dfc013.xlsx`) |
| T1 artefact | present under that run tree |

## 10. Resource Monitoring

Observed during Fifth Set T1 (20 s samples, 2 GB instance, 8.9.5 also resident):

| Observation | Value |
|-------------|--------|
| Peak Mem used | **957 MB** |
| Min Mem available | **950 MB** of 1907 MB |
| Swap | 0 (none configured) |
| After success | used 553 MB, available 1354 MB |
| Disk | 4.6G / 58G (8%) |
| OOM | none observed; process completed |

**Conclusion: 2 GB PASS WITH MODERATE RISK**

Headroom during T1 was about 950 MB available, but there is no swap and 8.9.5 is still loaded. A larger drawing or overlap with OS cache pressure could OOM. A 4 GB upgrade remains the safer production size; 2 GB worked for this Fifth Set.

## 11. Public URL Validation

http://13.127.104.99/ **now serves Version10**.

Verified from this workstation after the Nginx reload:

- `/health`: `engine_label=Version10`, `engine_root=.../Version10`, `app_release=W.3`, `phase=W.3`, `t1_included=true`
- `/`: HTTP 200, badges **Version10 production pipeline** and **Release W.3**
- No 8.9.5 / Version8 label on the public homepage
- Old app still answers only on `127.0.0.1:8000`

## 12. Single-Flight Validation

On deployed Linux, during First Set run `20260824_120944_1498af3a`:

HTTP **409**, body:

`{"code":"BUSY","error":"An estimation is currently running. Please wait and try again.","ok":false}`

After completion, a new estimate was accepted (`20260824_121014_8338f856`). No parallel pipeline execution was attempted.

## 13. Rollback Instructions

Old service stays running. Rollback is Nginx-only:

```bash
sudo cp /opt/steel-beam-estimation/rollback-w3/steel-beam-estimator.conf \
        /etc/nginx/sites-available/steel-beam-estimator.conf
sudo nginx -t && sudo systemctl reload nginx
curl -sS http://127.0.0.1/health
curl -sS http://13.127.104.99/health
```

Expected after rollback: `engine_root` contains `Version8`, `model_version` 8.9.4.

Do not delete Version10 or stop `steel-beam-estimator-v10` unless reversing the deploy entirely.

| | Old 8.9.5 | Version10 |
|--|-----------|-----------|
| service | `steel-beam-estimator.service` | `steel-beam-estimator-v10.service` |
| directory | `.../Steel-Beam-Estimation/current_model` | `.../Version10` |
| port | 127.0.0.1:8000 | 127.0.0.1:8001 |

## 14. Files Created / Modified

Deployment-only (engineering pipeline not edited):

- `Version10/webapp/config.py` — `APP_RELEASE = "W.3"`
- `Version10/webapp/routes.py` — health `phase: W.3`
- `Version10/webapp/deployment/gunicorn.w3.conf.py`
- `Version10/webapp/deployment/steel-beam-estimator-v10.service`
- `Version10/webapp/deployment/nginx-v10.conf`
- `Version10/webapp/deployment/nginx-v8-rollback.conf`
- `Version10/webapp/deployment/ROLLBACK_W3.txt`
- `Version10/webapp/deployment/pack_w3.py`
- `Version10/webapp/deployment/install_venv_w3.sh`
- `Version10/webapp/deployment/import_check_w3.py`
- `Version10/webapp/deployment/smoke_w3.py`
- `Version10/webapp/deployment/fifth_w3.py`
- `Version10/webapp/deployment/PHASE_W3_CHECKPOINT.md`
- `Version10/webapp/deployment/PHASE_W3_FINAL_DELIVERY_REPORT.md`

On the instance (not git): Version10 tree, venv, systemd unit, Nginx site, rollback copies, smoke DXFs under `/home/ubuntu/w3_smoke/`.

## 15. Files Intentionally Not Modified

Engineering modules were not changed:

- Version10 `Run_PY` production runners
- T1 / VB.1 source
- Hybrid D.1–D.4 and E.*
- benchmark truth data
- `MODEL_VERSION`
- calculation / stage implementations

## 16. Test Matrix

| ID | Result | Evidence |
|----|--------|----------|
| TEST-W3-01 Existing Lightsail baseline inspected | **PASS** | SSH inspect: Ubuntu, 2 GB, Python 3.12.3, `steel-beam-estimator.service`, Nginx, Version8 `/health` |
| TEST-W3-02 Rollback point / snapshot status confirmed | **PASS** | Snapshot **not** created (no AWS CLI). Config copies in `/opt/steel-beam-estimation/rollback-w3/`. Old dir/service retained. |
| TEST-W3-03 Version10 deployment copied separately | **PASS** | `/opt/.../Version10` beside Version8; old `current_model` untouched |
| TEST-W3-04 Python environment created | **PASS** | `python3.12 -m venv .../webapp/.venv` |
| TEST-W3-05 Declared dependencies installed | **PASS** | both requirements files; `PIP_OK` |
| TEST-W3-06 Critical T1 dependencies import successfully | **PASS** | matplotlib, Pillow, opencv 5.0.0, ezdxf, shapely, `wsgi:app` |
| TEST-W3-07 Gunicorn starts on Ubuntu | **PASS** | first nohup, then systemd on `:8001` |
| TEST-W3-08 Gunicorn uses exactly one worker | **PASS** | `--workers 1`; master+one worker PIDs |
| TEST-W3-09 Local server /health passes | **PASS** | Version10, T1 included, W.3 |
| TEST-W3-10 Nginx configuration validates | **PASS** | `nginx -t` successful before and after switch |
| TEST-W3-11 Small DXF upload passes | **PASS** | First Set three DXFs accepted |
| TEST-W3-12 Real Version10 pipeline executes | **PASS** | logs `engine_root=.../Version10`; all 13 stages |
| TEST-W3-13 T1 executes successfully | **PASS** | First Set 12.53 s; Fifth Set 328.86 s |
| TEST-W3-14 VB.1 Excel generated | **PASS** | workbook names and PK zip |
| TEST-W3-15 Excel download works | **PASS** | First Set HTTP 200 / 19561 bytes PK; Fifth Set 91188 bytes on disk |
| TEST-W3-16 Run isolation confirmed | **PASS** | `.../Version10/data/web_runs/<run_id>/`; not Version8 |
| TEST-W3-17 Single-flight BUSY behavior confirmed | **PASS** | HTTP 409 BUSY on Linux |
| TEST-W3-18 Production-scale run attempted and documented | **PASS** | Fifth Set 143 beams, 373.98 s |
| TEST-W3-19 RAM monitored during T1 | **PASS** | peak used 957 MB, min available 950 MB |
| TEST-W3-20 Disk usage acceptable | **PASS** | 8% of 58G |
| TEST-W3-21 Public Version10 UI loads | **PASS** | http://13.127.104.99/ HTTP 200, Version10 badges |
| TEST-W3-22 Public health check passes | **PASS** | public `/health` Version10 / W.3 |
| TEST-W3-23 Rollback path documented | **PASS** | Nginx restore commands above; old service still live |
| TEST-W3-24 Engineering regression check | **PASS** | no Run_PY / T1 / VB.1 / hybrid / truth edits; only web metadata + deploy files |

## 17. Known Limitations

- Single-flight architecture; concurrent estimates return 409
- Exactly one Gunicorn worker (in-process job store + shared GN pointer)
- Long T1 runtime (Fifth Set T1 ~329 s)
- 2 GB RAM: PASS WITH MODERATE RISK; no swap; 8.9.5 still resident
- Lightsail snapshot not created
- Job state is in-process: systemd restart drops in-memory `/api/status` for finished runs (files remain on disk)
- Gunicorn uses gthread internally because `threads=4`; worker **count** remains 1
- Old 8.9.5 is still installed and running until later explicit removal approval

## 18. GO / NO-GO

**GO WITH KNOWN LIMITATIONS**

Public http://13.127.104.99/ was verified serving Version10 W.3. Fifth Set T1/VB.1 succeeded on the 2 GB instance. Rollback to 8.9.5 is Nginx restore plus the still-running old service. Remaining risks: no Lightsail snapshot, moderate 2 GB T1 memory headroom, single-flight / one worker.
