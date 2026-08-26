# PHASE W.12 — SIXTH SET USER ACCEPTANCE REPORT

Saved: 2026-08-26  
Public: http://13.127.104.99/

---

## Drawing identity

| Item | Value |
|------|--------|
| Set | Sixth Set Drawings / Inizio 11–18F typical floor |
| Folder | `Test_Input/6th Set Drawings-Inizio_11-18F` |
| General notes | `SE-100_GENRAL NOTE_(SH-01 &SH-02)_R0 1.dxf` |
| Framing | `11-18TH FLOOR.dxf FRAMINIG.dxf` |
| Reinforcement | `479_SE-228_TYPICAL FLOOR BEAM REINFORCEMENT DETAILS(11-18)_R0_(SH-01 TO SH-03).dxf` |
| Beam count | **143** |

This is the same drawing as W.11 run `20260826_084708_f74912b8`.

---

## W.12 live Hybrid production run

| Item | Value |
|------|--------|
| run_id | `20260826_111142_32321cb4` |
| Result URL | http://13.127.104.99/?run=20260826_111142_32321cb4 |
| Pipeline | completed |
| Wall / duration_s | ~81 min / **4469.49 s** |
| Beams / bars / steel | 143 / 743 / **25579.013 kg** |
| Hybrid | `HYBRID_SUCCESS`, mode production, semantic_only |
| Claude attempted / success / failure | 143 / 26 / 117 |
| Timeouts | 0 |
| Evidence | eligible 143, P2.6.10 primary 127, compatibility fallback 16, unavailable 0, unexplained 0 |
| Authority | cut_length_overwrites **0**, geometry_overwrites **0**, stirrup_quantity_overwrites **0** |
| Excel | `Estimation_Output_20260826_111142_32321cb4.xlsx`, **86121** bytes, PK valid, openpyxl opened (Beam Summary, BBS, Steel Summary, Diameter Summary, Project Totals) |
| Result registered | YES — `DOWNLOAD_READY` |
| First download HTTP | **200** attachment |
| Repeated download | **200**, identical 86121 bytes |
| Manifest download_attempts | 2, last_download_ok true |

**SERVER_PIPELINE_SUCCESS:** PASS  
**USER_RESULT_DELIVERY_SUCCESS:** PASS (HTTP download + workbook parse; public `?run=` restore)

Public UI **button click** was verified on the live W.12 run `20260826_111142_32321cb4` (Playwright: success view, click Download Excel, 86121 bytes, PK, success view remained). The prior Sixth Set artefact `20260826_084708_f74912b8` was also restored and clicked after worker restart.

---

## User workflow

| Stage | Result |
|-------|--------|
| Upload | PASS |
| Processing | PASS (progress showed evidence beam N of 143) |
| Completion state | PASS (`success`, `DOWNLOAD_READY`) |
| Result registered | PASS |
| Download ready | PASS |
| Download Excel | PASS |
| Repeated download | PASS |
| Valid XLSX | PASS |
| Workbook opens | PASS |

---

## Distinguishing W.11 vs W.12 on this drawing

W.11 generated Excel for `20260826_084708_f74912b8` but the user could not retrieve it after worker restart.  
W.12 reconstructed that same file after deploy/rollback restarts **and** delivered a new Sixth Set workbook `20260826_111142_32321cb4`.
