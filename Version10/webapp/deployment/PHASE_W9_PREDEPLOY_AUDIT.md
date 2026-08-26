# PHASE W.9 — PRE-DEPLOYMENT AUDIT

Inspected: 2026-08-26 06:44 UTC via SSH to `ubuntu@13.127.104.99`.  
Local HEAD: `751d2c720943b99112d167311c92865731cd6c16` (`feat(Version10): add Hybrid production authority and W.8 P2.6.10 evidence path`).  
Secrets were not printed. Lightsail was not mutated during this inspect.

## TEST-W9-01 — local repository

| Item | Observed |
|------|----------|
| Local commit | `751d2c72` (matches the W.8 implementation commit named in the phase brief) |
| Working tree | dirty with research copy-PNGs / PDF fixtures / web_run artefacts only; W.8 runtime is committed |
| W.8 local classification | `W8_LOCAL_PASS_PRODUCTION_NOT_DEPLOYED` |
| Pack | `C:\Users\nishanth.h\AppData\Local\Temp\w9_runtime.tar.gz` (51 files + 3 production `__init__` stubs, 58558 bytes) |

Local focused tests before copy (PYTHONPATH=`Version10/src`):

- `PhaseW8_production_vision_evidence.unit_tests` PASS
- `PhaseW6_hybrid_production_authority.unit_tests` PASS
- Combined: **26 tests, 23.953 s, OK**

## TEST-W9-01 — Lightsail W.7 state (before mutation)

| Item | Observed |
|------|----------|
| Host | `ip-172-26-15-118`, kernel 6.17.0-1010-aws |
| RAM | 1907 MB total; ~1356 MB available; **0 swap** |
| Disk | 58G, 4.7G used, 53G free (9%) |
| Public | http://13.127.104.99/ `/health` HTTP 200 |
| `/health` phase | **W.7** |
| `app_release` | **W.7** |
| Hybrid mode | **production** (`HYBRID_MODE=production` in `/etc/steel-beam-estimator-v10.env`) |
| API key status | **PRESENT** (line count 1; value not printed) |
| Env file | `/etc/steel-beam-estimator-v10.env` mode `600` `root:root` |
| Env names | `HYBRID_MODE`, `ANTHROPIC_API_KEY`, `HYBRID_MAX_LIVE_CALLS`, `HYBRID_MAX_WALL_S`, `HYBRID_PER_CALL_TIMEOUT_S` |
| `anthropic` | **0.125.0** (satisfies `>=0.49.0,<1`; **not** 1.x — proceed) |
| Requirements pin | `anthropic>=0.49.0,<1` |
| systemd | `steel-beam-estimator-v10.service` **active**, NRestarts=0, started 2026-08-26 06:09:36 UTC |
| Gunicorn | **1 worker**, bind `127.0.0.1:8001`, timeout 3600s |
| Nginx | **active** (not changed) |
| Instance git | `bc2277aba68a1cca31858b6c91b473780174d33f` (older than local `751d2c72`; file-copy deploy, not `git pull`) |
| W.8 adapter | **W8_ABSENT** |
| W.6 `visuals.py` | no `PhaseW8_production_vision_evidence` import (W.7 crop path) |
| W.5 `live_invoke.py` | **no `detail_path`** (W.7 duplicated-envelope caller) |
| P2.6.10 A/B/C1/C3 | **PRESENT** on disk (research tree already on instance) |
| M.1 renderer | **PRESENT** |
| C.5 `claude_call.py` | **PRESENT** |
| First Set DXF | `/home/ubuntu/w3_smoke/smoke/1st Set Drawings-Galera_OHT&STP` present |
| W.7 canonical run | `20260825_113725_9a8d6014` present |

Old 8.9.x Gunicorn remains on `127.0.0.1:8000` (not public). Do not delete.

## Current W.7 evidence path (to replace)

W.7 production Hybrid uses the older crop/evidence path:

1. Prefer T1 OpenCV crop if present (First Set historically had **0**).
2. Else generate a W.6 T1.5 envelope + M.1 PNG.
3. Send that **same PNG twice** to C.5 / E.2 as context and detail.

W.9 must replace this with the W.8 adapter: P2.6.10-B.1 context + detail, C1/C2 selection, C3 gate, explicit W.6/T1 fallback only.

## Safety gates (pre-copy)

| Gate | Result |
|------|--------|
| `anthropic` 1.x | **NO** — 0.125.0, continue |
| Deploy local `.env` | **NO** — forbidden |
| Change API key location | **NO** |
| Change worker count | **NO** — keep 1 |
| Change Nginx | **NO** |
| `HYBRID_MODE` | keep `production` except temporary rollback test |

## Rollback inventory preserved on inspect

Primary rollback remains: set `HYBRID_MODE=off` in `/etc/steel-beam-estimator-v10.env` and restart `steel-beam-estimator-v10`. No code deletion, no API key removal.

File-level rollback: restore the W.7 copies of the files in the W.9 tarball (to be snapshotted into `/opt/steel-beam-estimation/backups/w9_predeploy_*` immediately before extract).
