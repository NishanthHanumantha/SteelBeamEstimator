# PHASE W.12 — RESULT DELIVERY FORENSIC REPORT

Saved: 2026-08-26  
Public: http://13.127.104.99/  
Affected user symptom: processing reached a completed result, **Download Excel** was clicked, then the result/download opportunity disappeared.

---

## Sixth Set identity (canonical)

Do not guess. Sources: `Test_Input/6th Set Drawings-Inizio_11-18F`, Phase P2.6.10-E.3 population manifest, and the W.11 143-beam production run.

| Item | Value |
|------|--------|
| Source folder | `Test_Input/6th Set Drawings-Inizio_11-18F` |
| Drawing set | Sixth Set Drawings / Inizio 11–18F typical floor |
| General notes | `SE-100_GENRAL NOTE_(SH-01 &SH-02)_R0 1.dxf` (8,129,155 bytes) |
| Framing | `11-18TH FLOOR.dxf FRAMINIG.dxf` (2,223,169 bytes) |
| Reinforcement | `479_SE-228_TYPICAL FLOOR BEAM REINFORCEMENT DETAILS(11-18)_R0_(SH-01 TO SH-03).dxf` (11,408,702 bytes) |
| Model beam count | **143** (E.3 `discovered_model_beam_count`; W.11 production run) |
| Estimator truth workbook | `Estimator_Output_6thSet/Estimator_Output_11-18TH FLOOR.xlsx` (145 estimator beams, 139 matched) |
| Prior web run | `qa2_Sixth_Set_Drawings_20260806_171449` |
| W.11 production run of this drawing | `20260826_084708_f74912b8` (Excel 85,800 bytes at 10:18 UTC) |

The W.11 “stuck” 143-beam typical-floor DXF **is** the Sixth Set. W.12 uses that same canonical input.

---

## Lifecycle trace (pre-W.12)

### A. Run creation

`POST /api/estimate` → `start_estimation` generates `run_id` as `%Y%m%d_%H%M%S_` + 8 hex chars, stages under `data/web_runs/<run_id>/`, copies uploads, stores `JobState` in process memory `_JOBS`.

### B. Pipeline

Background daemon thread runs Hybrid production then VB.1. Excel is written under the run tree `data/output/Production_Output/Estimation_Output.xlsx`, then copied to `webapp/outputs/Estimation_Output_{run_id}.xlsx`.

### C. Excel output

Production `webapp/outputs/` retained the Sixth Set workbook:

- `Estimation_Output_20260826_084708_f74912b8.xlsx`
- 85,800 bytes
- mtime 2026-08-26 10:18 UTC
- Valid XLSX (PK / openpyxl: Beam Summary, Bar Bending Schedule, Steel Summary)

Staging tree also retained. Upload copies under `webapp/uploads/<run_id>` are deleted in `finally`. **Cleanup did not delete the workbook.**

### D. Result registration (pre-W.12)

**None on disk.** Completion lived only in `_JOBS`. `get_job()` read memory only.

### E. Status API

`GET /api/status/<run_id>` returned **404 Unknown run id** if `_JOBS` missed the run, even when Excel existed.

### F. Frontend

- Download control was `<a id="btn-download" href="#">` later set to `/api/download/<run_id>`.
- Click navigated the **entire page** to the download URL.
- If the response was JSON 404/400, the SPA was replaced and the success view vanished.
- W.11 poll: HTTP 404 after completion (worker restart) switched to the error view: “This estimation is no longer available…”
- Five consecutive network misses also hid success.
- No `?run=` / sessionStorage restore.

### G. Download endpoint

Required in-memory `job.status == success` and `job.workbook_path`. Path-traversal check against `OUTPUT_ROOT` was already present. Missing job → JSON 404.

### H. Process model

Gunicorn **1 sync worker**, `timeout=3600`, systemd `Restart=on-failure`. W.11 deploy/rollback **restarts the worker** and wipes `_JOBS`. `PrivateTmp=true` does not affect `webapp/outputs`.

---

## Timeline that destroyed the user download

| UTC | Event |
|-----|--------|
| 08:47:08 | Sixth Set estimate `20260826_084708_f74912b8` started |
| ~10:18 | Excel written to `webapp/outputs/` (85,800 bytes) |
| ~10:19 | In-memory job `success`; UI could show Download Excel |
| 10:21:28 | W.11 deploy restart (`w11_predeploy_20260826T102128Z`) **cleared `_JOBS`** |
| after | Status/download 404 although Excel still on disk |
| UI | Poll 404 and/or `<a href>` navigation to JSON 404 → result disappeared |

This matches the estimator report: completion appeared, Download Excel was clicked, then the result vanished. **Server-side Excel generation succeeded. User delivery failed.**

---

## Root cause classification

**MULTIPLE_CONTRIBUTING_CAUSES**

Primary: **WORKER_RESTART_STATE_LOSS** — download/status depended on in-memory `_JOBS`.

Secondary: **FRONTEND_STATE_LOSS** / **BROWSER_NAVIGATION_OR_UI_FAILURE** — `<a href>` full-page navigation; 404 poll hid success; no durable `run_id` in the URL.

Contributing: **DOWNLOAD_ROUTE_FAILURE** — endpoint refused disk-backed workbooks when memory was empty.

Not the cause: Excel cleanup race (file survived), Hybrid hang (W.11 already disproved), Nginx (proxy timeouts 3600s; download of 86 KB succeeded after W.12).

---

## Post-fix evidence (same Sixth Set artefact)

After W.12 deploy and Hybrid rollback restarts:

- `GET /api/status/20260826_084708_f74912b8` → `success`, `download_ready=true`, `result_lifecycle=DOWNLOAD_READY`
- `GET /api/download/20260826_084708_f74912b8` → HTTP 200, `Content-Disposition: attachment; filename=Estimation_Output_20260826_084708_f74912b8.xlsx`, 85,800 bytes, PK signature
- Repeated download identical
- Playwright: open `/?run=20260826_084708_f74912b8`, success view, **click Download Excel**, file saved, success view remained

---

## What was not the authority model

Vision vs deterministic engineering was not involved in the disappeared download. Hybrid completed; VB.1 Excel existed.
