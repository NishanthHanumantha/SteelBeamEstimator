# PHASE W.12 CHECKPOINT

Saved: 2026-08-26

PHASE:  
W.12 — Production Result Delivery, Excel Download Reliability & End-to-End User Acceptance Verification

PRIMARY CLASSIFICATION:  
**W12_PASS_USER_ACCEPTED**

ROOT CAUSE:  
**MULTIPLE_CONTRIBUTING_CAUSES** — primarily **WORKER_RESTART_STATE_LOSS** (in-memory `_JOBS` only) plus **FRONTEND_STATE_LOSS** (`<a href>` navigation / 404 poll hid success). Excel on disk was never the failure.

SIXTH SET:
- drawing: Inizio 11–18F typical floor (`479_SE-228_TYPICAL FLOOR BEAM REINFORCEMENT DETAILS(11-18)_R0_(SH-01 TO SH-03).dxf`)
- run_id: `20260826_111142_32321cb4`
- beam count: 143
- Hybrid: `HYBRID_SUCCESS` (Claude 143 attempted, 26 success, 117 unresolved/fallback, 0 timeouts)
- total wall time: 4469.49 s (~81 min)

PIPELINE:
- completed
- Excel generated: YES (86121 bytes)
- Excel registered: YES (`DOWNLOAD_READY`)

DOWNLOAD:
- public UI tested: YES (Playwright click Download Excel on live run `20260826_111142_32321cb4` and restored `20260826_084708_f74912b8`)
- first download: PASS (HTTP 200)
- repeated download: PASS
- HTTP result: 200, attachment filename `Estimation_Output_20260826_111142_32321cb4.xlsx`
- workbook signature valid: YES
- workbook opens/parses: YES (openpyxl)

FINAL USER ACCEPTANCE:

| Stage | Result |
|-------|--------|
| UPLOAD | PASS |
| PROCESSING | PASS |
| COMPLETION STATE | PASS |
| RESULT REGISTERED | PASS |
| DOWNLOAD READY | PASS |
| DOWNLOAD EXCEL | PASS |
| REPEATED DOWNLOAD | PASS |
| VALID XLSX | PASS |
| WORKBOOK OPENS | PASS |

DETERMINISTIC SAFETY:
- cut_length_overwrites = 0
- geometry_overwrites = 0
- stirrup_quantity_overwrites = 0

PRODUCTION:
- /health phase: **W.12**
- HYBRID_MODE: **production**
- worker count: **1**
- Anthropic version: **0.125.0**
- rollback tested: YES (`off` then restored `production`)
- final production state: W.12, Hybrid production, durable result registry live

LIMITATIONS:
- 117 of 143 Claude calls classified failure/unresolved on this Sixth Set run; Excel still generated via deterministic path. This is Hybrid completeness, not a download blocker.
- Result URL persistence is `?run=` / sessionStorage (no account login). Refresh of that URL works while the workbook is retained.

Public result: http://13.127.104.99/?run=20260826_111142_32321cb4  
Backup: `/opt/steel-beam-estimation/backups/w12_predeploy_20260826T110729Z`
