# Phase W.13 — Download Forensic Report

Date: 2026-08-27  
Affected user run: `20260826_141507_88aff694`

## What the user saw

Estimation completed. Download Excel was shown. Clicking it did not download a workbook.

## Affected run — server side

| Item | Evidence |
|---|---|
| run_id | `20260826_141507_88aff694` |
| Files | `SE-100-R0-SH-01SH-02GENERAL_NOTES.dxf`, `Galera_GF_FramingPlan.dxf`, `Galera_GF_BeamReinforcementDetails.dxf` |
| Completed | 2026-08-26 14:28:37 UTC (809.89 s, 65 beams) |
| Workbook on disk | `webapp/outputs/Estimation_Output_20260826_141507_88aff694.xlsx` **46,613 bytes**, valid XLSX |
| Manifest | `DOWNLOAD_READY` |
| `download_attempts` | **0** |
| `last_download_ok` | null |

`GET /api/download/<run_id>` was never invoked for this run. The workbook was present and the status endpoint would have returned `download_ready=true`. This is a **client-side click path** failure, not a missing file.

W.12 automated tests (including Playwright on a **fresh** browser) passed. They could not see a long-lived cached `app.js`.

## Browser / UI path

W.12 changed the control from `<a href="/api/download/...">` to `<button>` plus `fetch`+blob in `app.js`.

Production nginx:

```
location /static/ { expires 7d; }
```

Public HTML loaded `/static/js/app.js` **without a cache-buster**. After W.12 deploy (2026-08-26 11:07 UTC), `Cache-Control: max-age=604800` was confirmed.

A user who had visited the site before W.12 kept cached pre-W.12 `app.js` (no `downloadExcel` fetch handler) while receiving new HTML (`<button>` with no `href`). Click therefore did nothing. `download_attempts` stayed 0.

Secondary risk (not this incident): W.12 revoked the object URL immediately after `a.click()`, which can cancel the download in some browsers. That path would still increment `download_attempts`.

## Root cause

Stale cached `app.js` + unversioned static URL + nginx 7-day cache + download control that is not a native `<a href>`.

## Repair

1. Cache-bust: `app.js?v=W.13` and `app.css?v=W.13`.
2. Restore `<a id="btn-download" class="btn" href="...">` and set `href=/api/download/<run_id>` on success.
3. Keep fetch+blob as enhancement; delay `revokeObjectURL` by 60 s.
4. nginx: `Cache-Control: no-cache` for `/static/js/` and `/static/css/`.
5. On failure: explicit `#download-error`, success view remains, retry allowed.

## Proof (actual UI click)

Target: `http://13.127.104.99/?run=20260826_141507_88aff694` (Playwright Chromium).

| Check | Result |
|---|---|
| Cache-bust in HTML | `app.js?v=W.13` present |
| Native href after restore | `/api/download/20260826_141507_88aff694` |
| First click | 46,613 bytes, `PK` signature |
| Repeated click | 46,613 bytes, `PK` |
| Refresh then click | 46,613 bytes, `PK` |
| Success view remains | yes |
| Download error hidden | yes |
| Worker restart then click | same PASS |
| XLSX zip (`xl/` entries) | valid |

Controlled W.13 run `20260827_055526_cad8ac77` also downloaded 19,560 bytes `PK` on first click, repeat, and refresh.
