# PHASE W.7 — PRE-DEPLOYMENT CHECKPOINT

Inspected: 2026-08-25 11:21 UTC via SSH to `ubuntu@13.127.104.99`.  
No files were changed on Lightsail during this checkpoint. Secrets were not printed.

## TEST-W7-01 — live production state

| Item | Observed |
|------|----------|
| Host | `ip-172-26-15-118`, Ubuntu 24.04, kernel 6.17.0-1010-aws |
| Instance RAM | **1907 MB** total; ~571 MB used / **1336 MB available** at inspect |
| Swap | **none** |
| Disk | 58G, 4.7G used, 53G free (9%) |
| Public URL | http://13.127.104.99/ HTTP **200** |
| Public `/health` | `status=ok`, `phase=W.5`, `app_release=W.5` |
| Engine | Version10 at `/opt/steel-beam-estimation/SteelBeamEstimator/Version10` |
| Hybrid mode | **off** |
| API key configured | **false** (`api_key_status=ABSENT`) |
| Production stages | `VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → VB1` (no HYBRID stage) |
| Busy | false |

## systemd / Gunicorn

| Item | Observed |
|------|----------|
| Unit | `steel-beam-estimator-v10.service` **active + enabled** |
| Fragment | `/etc/systemd/system/steel-beam-estimator-v10.service` (comments still say Phase W.5) |
| WorkingDirectory | `/opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp` |
| User | ubuntu |
| Bind | `127.0.0.1:8001` |
| Workers | **1** (`--workers 1 --timeout 3600`) |
| Config | `webapp/deployment/gunicorn.w3.conf.py` |
| Unit `Environment=` | `HYBRID_MODE=off` |
| EnvironmentFile | `/etc/steel-beam-estimator-v10.env` (ignore_errors=yes) |
| Optional dotenv | `webapp/.env` **absent** |
| NRestarts | 0 |
| Started | 2026-08-25 08:56:43 UTC |

Processes: master PID 157982 + one worker PID 157984.

## Nginx

| Item | Observed |
|------|----------|
| Service | **active + enabled** |
| Site | `/etc/nginx/sites-available/steel-beam-estimator.conf` labelled Phase W.3 |
| Upstream | `steel_beam_estimator_app` → `127.0.0.1:8001` |
| Listen | `0.0.0.0:80` and `[::]:80` |

Nginx was **not** changed for this checkpoint.

## Environment file (no secret values)

`/etc/steel-beam-estimator-v10.env`: present, `root:root`, mode `600`, 91 bytes.

Variable names present: `HYBRID_MODE`, `HYBRID_MAX_LIVE_CALLS`, `HYBRID_MAX_WALL_S`, `HYBRID_PER_CALL_TIMEOUT_S`.

- `HYBRID_MODE=off`
- `ANTHROPIC_API_KEY` line count: **0**
- Shadow-era caps still present: `HYBRID_MAX_LIVE_CALLS=6`, `HYBRID_MAX_WALL_S=90`

## W.6 code on disk

| Path | State |
|------|--------|
| `src/PhaseW6_hybrid_production_authority/` | **ABSENT** |
| `Run_PY/run_phase_w6_hybrid_production_authority.py` | **ABSENT** |
| `src/PhaseW5_production_hybrid_shadow/` | present (W.5, dated Aug 25 07:58 UTC) |
| `src/PhaseM.1_engineering_vision_dataset/` | present (needed for W.6 crop fallback) |
| `webapp/config.py` `APP_RELEASE` | `"W.5"` |

Confirmed: Lightsail has **not** received the W.6 Hybrid production-authority implementation.

## Rollback targets (intact)

| Target | State |
|------|--------|
| Old 8.9.x Gunicorn | **active** on `127.0.0.1:8000`, 1 master + 1 worker |
| Old `/health` | `status=ok`, `phase=D.4.2`, `model_version=8.9.4`, engine Version8 |
| W.3 Nginx copy | `/opt/steel-beam-estimation/rollback-w3/steel-beam-estimator.conf` present |
| W.3 unit copy | `/opt/steel-beam-estimation/rollback-w3/steel-beam-estimator.service` present |
| Old tree | `/opt/steel-beam-estimation/SteelBeamEstimator/Steel-Beam-Estimation/current_model` running |

Hybrid-off rollback for Version10 does **not** require an Nginx switch. Nginx rollback to 8.9.x remains available via the W.3 copy.

## Smoke DXFs already on instance

First Set (preferred for W.7 E2E):

- `/home/ubuntu/w3_smoke/smoke/1st Set Drawings-Galera_OHT&STP/general_note/SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf`
- `.../framing/SampleBeam_FramingPlan_DXF.dxf`
- `.../reinforcement/SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf`

Fifth Set is also present; W.7 will not start with it.

## Health of public deterministic app

Public Version10 answers `/health` and the home page. No active estimation. Memory headroom is adequate for a controlled First Set run. Rollback paths exist.

**TEST-W7-01: PASS.** Safe to deploy W.6 files with `HYBRID_MODE=off`.
