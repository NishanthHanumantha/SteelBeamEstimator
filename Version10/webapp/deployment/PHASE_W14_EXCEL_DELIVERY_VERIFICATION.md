# PHASE W.14 — EXCEL DELIVERY VERIFICATION

Date: 2026-08-27  
Run ID: `20260827_093245_a32541a7`  
Workbook: `Estimation_Output_20260827_093245_a32541a7.xlsx`

## Implementation test result: PASS

Automated delivery checks passed. This is **not** estimator user acceptance. The human user still needs to click the public Download Excel button.

## A. Run completion

- `status=success`
- `excel_generated=true`
- `excel_exists=true`
- `result_registered=true`
- `download_ready=true`
- `result_lifecycle=DOWNLOAD_READY`
- Server workbook: 46,363 bytes, `PK` signature

## B–C. Result page and download control

Playwright opened `http://13.127.104.99/?run=20260827_093245_a32541a7`:

- `#view-success` visible
- Workbook name shown
- `#btn-download` present as an `<a>` with `href=/api/download/20260827_093245_a32541a7`
- Cache-bust present: `app.js?v=W.14`

## D–H. Browser click, HTTP, size, XLSX, repeat

| Check | Result |
| --- | --- |
| Playwright click 1 | 46,363 bytes, `PK` |
| Playwright click 2 (repeat) | 46,363 bytes, `PK` |
| HTTP GET `/api/download/<run_id>` #1 | 200, 46,363, `PK`, `Content-Disposition` attachment |
| HTTP GET #2 | 200, 46,363, `PK` |
| openpyxl | PASS — sheets: Beam Summary, Bar Bending Schedule, Steel Summary, Diameter Summary, Project Totals |
| ZIP `xl/` members | PASS |

## I–K. Refresh and `?run=` restoration

| Check | Result |
| --- | --- |
| Browser reload of result page | success view remains |
| Download after refresh | 46,363 bytes, `PK` |
| Entry via `?run=<run_id>` | restored result page |
| Download after restoration | 200 / `PK` / openpyxl PASS |

`#download-error` remained hidden. Result view stayed visible after downloads.

## L–M. Workbook structure

Validated with openpyxl read-only load. Five expected sheets present. File is a real XLSX, not an HTML error page.

## Note on public upload from this workstation

The Windows urllib multipart POST to `http://13.127.104.99/api/estimate` was reset while sending the GN filename that contains `&`. Delivery tests above used the successful production run submitted to Gunicorn with those same files. Browser download of that run is the W.14 delivery proof.
