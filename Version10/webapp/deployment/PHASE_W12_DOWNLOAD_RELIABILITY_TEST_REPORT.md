# PHASE W.12 — DOWNLOAD RELIABILITY TEST REPORT

Saved: 2026-08-26

Local stub suite: `Version10/webapp/tests/test_w12_result_delivery.py`  
Flask/W.2/W.5/W.6: 33 tests OK in 30.2 s  
W.6 authority + W.10 monitor + W.11 reliability (PYTHONPATH=`Version10/src`): 37 tests OK in 17.0 s

---

## TEST-DL / TEST-W12 matrix

| ID | Case | Result | Evidence |
|----|------|--------|----------|
| TEST-DL-01 / W12-01 | Completed run Excel exists | PASS | Stub + production restore `webapp/outputs/Estimation_Output_{run_id}.xlsx` |
| TEST-DL-02 / W12-01 | Registered to run_id | PASS | Manifest `DOWNLOAD_READY`; status `result_registered=true` |
| TEST-DL-03 / W12-02 | Download HTTP success | PASS | 200 local and public |
| TEST-DL-04 | Content-Disposition attachment filename | PASS | `attachment; filename=Estimation_Output_<run_id>.xlsx` |
| TEST-DL-05 | Correct workbook bytes | PASS | Repeated downloads identical; openpyxl sheets |
| TEST-DL-06 / W12-03 | PK / XLSX ZIP | PASS | `b'PK'` + `xl/` members |
| TEST-DL-07 / W12-14 | Workbook opens | PASS | openpyxl `load_workbook` on restored Sixth Set |
| TEST-DL-08 | Non-zero size | PASS | Restore 85,800 bytes; stub > 32 bytes |
| TEST-DL-09 / W12-04 | Repeated download | PASS | Local + public restore identical |
| TEST-DL-10 / W12-05 | Refresh / UI state | PASS | `?run=` restore; Playwright success view survives click |
| TEST-DL-11 | Network miss after success | PASS | Frontend keeps success + retry copy (unit of JS contract; poll misses after `completed`) |
| TEST-DL-12 / W12-06 | Missing file explicit error | PASS | 404 `RESULT_UNAVAILABLE`; status still `success` |
| TEST-DL-13 / W12-07 | Invalid run_id | PASS | 404 `INVALID_RUN` |
| TEST-DL-14 | No arbitrary path | PASS | Regex + `OUTPUT_ROOT` bound; `../` not served as xlsx |
| TEST-DL-15 / W12-09 | Retention | PASS | Download does not delete workbook or staging |
| TEST-DL-16 / W12-10 | Worker/process restart | PASS | Clear `_JOBS` locally; production W.12 + rollback restarts still serve `20260826_084708_f74912b8` |
| TEST-W12-08 | Hybrid fail → Excel still downloadable | PASS | Stub `HYBRID_MODE=production` without key |
| TEST-W12-15 | Authority protection regression | PASS | W.6 `test_w6_05_engineering_fields_untouched` + W.10 overwrite counters = 0 |

---

## Public UI (Playwright)

Target: `http://13.127.104.99/?run=20260826_084708_f74912b8`  
This is the Sixth Set workbook from the W.11 run that users could not download.

| Check | Result |
|-------|--------|
| Success view shown | YES — workbook name `Estimation_Output_20260826_084708_f74912b8.xlsx` |
| Click **Download Excel** | YES |
| Suggested filename | `Estimation_Output_20260826_084708_f74912b8.xlsx` |
| Bytes / PK | 85800 / `PK` |
| Download error hidden | YES |
| Success view remained | YES |

---

## Live Sixth Set pipeline under W.12

New Hybrid production run: **`20260826_111142_32321cb4`**.

| Check | Result |
|-------|--------|
| Duration | 4469.49 s |
| Beams / steel | 143 / 25579.013 kg |
| First download | HTTP 200, 86121 bytes, PK, openpyxl OK |
| Repeated download | HTTP 200, identical |
| Restore URL | `/?run=20260826_111142_32321cb4` |

---

## Failures / notes

- `GET /api/download/../../../etc/passwd` was reset by the proxy (not an xlsx). Invalid `run_id` is 404 JSON.
- No secrets in `/health`.
