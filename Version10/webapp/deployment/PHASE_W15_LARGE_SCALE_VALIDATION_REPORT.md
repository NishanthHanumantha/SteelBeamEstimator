# Phase W.15 Status

Date: 2026-08-28  
Production: `http://13.127.104.99/` (Release W.14, no production-logic change)  
Run ID: **`20260827_110320_4e330c37`**  
Origin: **manual browser upload** (not curl/API bypass)

## A. FINAL CLASSIFICATION

**W15_PASS_WITH_LIMITATIONS**

The large-scale Sixth Set drawing completed end-to-end in production: 143/143 Hybrid Vision API success, Excel generated, automated and manual download succeeded, and the result survived refresh, `?run=` restore, repeated download, and an idle worker restart. Limitations are the frozen W.14 UI (elapsed + beam index/total, no percentage bar, no ETA) and that the human user confirmed download, not independent opening of the workbook.

## B. INPUT DRAWING

| Slot | Browser filename | Stored name | Bytes |
| --- | --- | --- | ---: |
| General Notes | `SE-100_GENERAL NOTE_(SH-01 & SH-02)_R01.dxf` | `SE-100_GENRAL_NOTE_SH-01_SH-02_R0_1.dxf` | 8,129,155 |
| Framing | `11-18TH FLOOR.dxf FRAMING.dxf` | `11-18TH_FLOOR.dxf_FRAMINIG.dxf` | 2,223,169 |
| Reinforcement | `479_SE-228_TYPICAL FLOOR BEAM REINFORCEMENT DETAILS(11-18)_R0_(SH-01 TO SH-03).dxf` | `479_SE-228_TYPICAL_FLOOR_BEAM_REINFORCEMENT_DETAILS11-18_R0_SH-01_TO_SH-03.dxf` | 11,408,702 |

- Run ID: `20260827_110320_4e330c37`
- Measured beam count: **143**
- Drawing classification: **Sixth Set 11–18F / large-scale typical floor**
- Result: [http://13.127.104.99/?run=20260827_110320_4e330c37](http://13.127.104.99/?run=20260827_110320_4e330c37)
- Download: [http://13.127.104.99/api/download/20260827_110320_4e330c37](http://13.127.104.99/api/download/20260827_110320_4e330c37)
- Workbook: `Estimation_Output_20260827_110320_4e330c37.xlsx`

## C. END-TO-END USER WORKFLOW

| Stage | Result |
| --- | --- |
| Upload (actual browser UI) | **PASS** — three DXF slots submitted by the human user |
| Processing | **PASS** — `status=success`, wall 5527.75 s |
| Progress | **PASS** with limitation — elapsed + `beam id (index of total)` updated; UI did not freeze |
| Completion | **PASS** — `result_lifecycle=DOWNLOAD_READY`, `hybrid_status=HYBRID_SUCCESS` |
| Download | **PASS** — automated HTTP + Playwright; user reported manual browser download |
| Open | **PASS (automated)** — openpyxl read-only load, five expected sheets. User opening of the downloaded file was not independently re-confirmed on resume |

## D. PROGRESS BAR & ETA VALIDATION

Frozen W.14 frontend (`app.js` / `index.html`):

- Spinner + `#process-message` + `#process-detail`
- Elapsed time from `elapsed_s`
- Beam progress text: `beam {beam_id} ({index} of {total})` when progress exists
- **No percentage bar**
- **No ETA** (not computed; not invented)

Observed during the live run: progress continued through evidence and Vision; no UI freeze. Final progress snapshot after completion: `phase=HYBRID_COMPLETE`, label `Completing deterministic engineering...`.

This is a W.14 UI limitation, not a W.15 production-logic defect.

## E. HYBRID COMPLETENESS

Forensic reconstruction of `hybrid_resolution_trace.json` for this run (`identity_ok=true`, `fallback_identity_ok=true`).

| Metric | Count |
| --- | ---: |
| Total beams | 143 |
| Hybrid eligible | 143 |
| Evidence generated | 143 |
| Evidence unavailable | 0 |
| Claude attempted | 143 |
| Claude API success | 143 |
| Claude API failure | 0 |
| Claude timeout | 0 |
| Parse valid | 143 |
| Parse invalid | 0 |
| Schema valid | 143 |
| Schema rejected | 0 |
| E.2 accepted | 143 |
| E.2 rejected | 0 |
| D.2 resolved | 143 |
| D.2 unresolved | 0 |
| R13 patch eligible | 143 |
| R13 patches applied | 140 |
| R13 patch rejected | 3 |
| Deterministic fallback | 0 |
| Unexplained | 0 |
| Unresolved beams | 0 |

Accounting identity:

```
Eligible 143
  = D.2 resolved 143
  + deterministic fallback 0
  + unexplained 0
```

API success rate: **143/143 (100%)**  
D.2 resolution rate: **143/143 (100%)**  
Deterministic fallback count: **0**

R13: 3 Hybrid-resolved beams had no matching semantic fields to patch. That is an explicit patch-not-applied count, not an unexplained beam state.

Evidence sources (inspect only; no crop redesign):

| Source | Count |
| --- | ---: |
| P2.6.10 primary (`P2610B1_ADAPTIVE_CONTEXT_DETAIL`) | 127 |
| W.8 mixed / T1 compatibility (`W8_SELECTED_MIXED`) | 13 |
| W.6 envelope fallback (`W6_ENVELOPE_RENDER`) | 3 |
| Same-SHA context/detail | 3 |
| Distinct context/detail | 140 |

The 3 same-SHA pairs match the 3 `W6_ENVELOPE_RENDER` envelopes. Status-API `w6_compatibility_path=16` is the 13 mixed + 3 envelope paths grouped together (127 + 16 = 143).

Steel output (pipeline, not estimator-accepted): **67506.849 kg**, 743 bars, 143 beams, `IS_456_DETERMINISTIC`.

## F. API FAILURE FORENSICS

No API failures. Provider category counts: `OK=143`. Reason counts: `OK=143`. `first_api_failure=null`.

| Checkpoint | Value |
| --- | --- |
| First API success | attempt 1, beam `B1` |
| 26th API success | attempt 26, beam `B121` |
| 27th API success | attempt 27, beam `B122` |
| Final successful API call number | 143 |
| First API failure | none |

**PREVIOUS_26_CALL_CLIFF_NOT_REPRODUCED**

Claude API success continued through 143/143 attempted Vision calls, well beyond the previous W.12/W.13 failure cliff of 26 successful calls.

## G. COST BASELINE

Do not treat USD figures as billed spend. Anthropic console invoice delta was not observed.

| Quantity | Label | Source |
| --- | --- | --- |
| Input / output / total tokens | **ACTUAL_OBSERVED_TOKENS** | Hybrid shadow telemetry |
| USD cost | **ESTIMATED_USD** | Public list rates ($3.00 / MTok input, $15.00 / MTok output) |
| Anthropic billed spend change | **NOT OBSERVED** | Console not queried |

W.15 measured result (`20260827_110320_4e330c37`):

| Metric | Value | Label |
| --- | ---: | --- |
| Vision calls attempted / successful / failed | 143 / 143 / 0 | ACTUAL_OBSERVED |
| Input tokens | 551,364 | ACTUAL_OBSERVED_TOKENS |
| Output tokens | 98,997 | ACTUAL_OBSERVED_TOKENS |
| Total tokens | 650,361 | ACTUAL_OBSERVED_TOKENS |
| Estimated application-side cost | **$3.139047** | ESTIMATED_USD |
| Cost per successful Vision beam | **$0.021951** | ESTIMATED_USD |
| Per-success tokens min / mean / max | 2,793 / 4,548.0 / 5,368 | ACTUAL_OBSERVED_TOKENS |

### OBSERVED COMPARISON vs W.14 Galera (`20260827_093245_a32541a7`, 64 successful calls)

| Metric | W.14 Galera | W.15 Sixth Set | Label |
| --- | ---: | ---: | --- |
| Successful Vision calls | 64 | 143 | ACTUAL_OBSERVED |
| Total tokens | 290,156 | 650,361 | ACTUAL_OBSERVED_TOKENS |
| Mean tokens / success | 4,533.7 | 4,548.0 | ACTUAL_OBSERVED_TOKENS |
| ESTIMATED USD / success | $0.021764 | $0.021951 | ESTIMATED_USD |
| ESTIMATED drawing USD | $1.392888 | $3.139047 | ESTIMATED_USD |
| W.14 143-beam projection | $3.112234 | observed $3.139047 | PROJECTION vs OBSERVED |

Per-beam ESTIMATED cost and mean tokens are within ~1% of the W.14 Galera baseline. The W.14 143-beam projection ($3.112234) vs this observed run ($3.139047) differs by about $0.027.

## H. PERFORMANCE

ACTUAL_OBSERVED timestamps (UTC) on 2026-08-27:

| Interval | Seconds |
| --- | ---: |
| Total wall (`duration_s`) | 5527.75 (~92 min) |
| Preprocessing before visual evidence (`created_at` 11:03:20 → evidence start 11:07:26) | ~246 |
| Evidence generation (11:07:26 → Hybrid start 12:09:36) | ~3730 |
| Average evidence generation per beam (~3730 / 143) | ~26.1 |
| Hybrid / Vision (`hybrid_latency_s`) | 1541.821 |
| Average Vision time per successful call (1541.821 / 143) | ~10.78 |
| Excel / result finalization (Hybrid end 12:35:18.9 → workbook Last-Modified 12:35:24; wall to 12:35:27.75) | ~6–9 |

Main bottleneck: **sequential P2.6.10 evidence generation**, then sequential single-worker Vision. Workers were not increased.

Historical same-class reference (W.11 Sixth Set): evidence ~3707 s, Vision ~1543 s, Claude 143/143. W.15 timings match that successful-call profile. This is not claimed as a performance improvement.

## I. EXCEL DELIVERY

Workbook: `Estimation_Output_20260827_110320_4e330c37.xlsx`  
Server file: **85802 bytes**, `PK` signature.

### AUTOMATED_DOWNLOAD_STATUS: **PASS**

| Check | Result |
| --- | --- |
| HTTP GET `/api/download/<run_id>` #1 | 200, 85802, `PK`, `Content-Disposition` attachment |
| HTTP GET #2 | 200, 85802, `PK`, identical bytes |
| Playwright `?run=` click 1 | 85802, `PK` |
| Playwright click 2 (repeat) | 85802, `PK` |
| Playwright after page refresh | 85802, `PK` |
| openpyxl | **PASS** — sheets: Beam Summary, Bar Bending Schedule, Steel Summary, Diameter Summary, Project Totals |
| ZIP `xl/` members | PASS |
| `#download-error` | remained hidden |

### MANUAL_USER_DOWNLOAD_STATUS: **PASS (download reported)**

The human user stated they manually downloaded Excel from the public result page before pausing. Automated openpyxl confirmed the workbook is a valid XLSX with the five expected sheets. Independent confirmation that the user opened that downloaded file and inspected sheet names was **not** captured on resume.

## J. RESULT DURABILITY

| Check | Result |
| --- | --- |
| Browser reload of result page | success view remains (`#view-success`) |
| `?run=20260827_110320_4e330c37` restore | restored workbook name and native `<a href=/api/download/20260827_110320_4e330c37>` |
| Repeated download | identical 85802-byte `PK` XLSX |
| Worker restart | **performed while idle** (`busy=false`). Service returned `active`. Post-restart: `/health` ok, `status=success` / `DOWNLOAD_READY`, HTTP download 85802 `PK`, Playwright restore+click PASS |

`app.js?v=W.14` cache-bust remained present. Durable registry served the completed result after process restart.

## K. DETERMINISTIC PROTECTION

Pre/post Hybrid R13 overwrite check:

- `cut_length_overwrites = 0`
- `geometry_overwrites = 0`
- `stirrup_quantity_overwrites = 0`
- `deterministic_engineering_overwrite_count = 0`
- pre-Hybrid and post-Hybrid artefacts present

## L. PRODUCTION STATUS

Verified 2026-08-28 after idle worker restart:

- Current phase / `app_release`: **W.14** (W.15 is validation-only; no APP_RELEASE bump)
- `HYBRID_MODE`: **production**
- Authoritative enabled: **false**
- Production authority: `semantic_only`
- Worker count: **1** (Gunicorn `--workers 1 --bind 127.0.0.1:8001`)
- Anthropic SDK: **0.125.0** (not 1.x)
- API key: **PRESENT** (value not printed)
- Production health: `status=ok`, `busy=false`, `engine_ready=true`
- Backup (non-disruptive, taken before W.15 validate): `/opt/steel-beam-estimation/backups/w15_prevalidate_20260827T163512Z`

No production logic was changed in W.15.

## M. GIT STATUS

- Production logic: **unchanged** (W.14 freeze `b90d08c95c4563dbbc0871609484f3cbe0c2df13` remains an ancestor)
- Checkpoint already on `main`: `cabd1eb7` `docs(Version10): checkpoint W.15 large-scale browser upload run`
- This report is a docs-only addition under `Version10/webapp/deployment/`
- Secrets, `.env`, downloaded workbooks, crop artefacts, forensic JSON, and temporary logs are **not** committed

## N. REMAINING LIMITATIONS

1. Processing UI shows elapsed time and beam index/total only. There is no percentage bar and no ETA.
2. Manual user confirmation covers browser download, not an independently witnessed workbook-open of that downloaded file (automated open passed).
3. Steel quantities are pipeline output. Estimator engineering acceptance of 67506.849 kg was not part of this phase.
4. Single-worker sequential evidence + Vision remains the throughput limit (~92 minutes for 143 beams).
5. Filename sanitization still rewrites browser names (spaces, `&`, parentheses). Upload succeeded despite that.

## O. FINAL RECOMMENDATION

**A. READY FOR ESTIMATOR VALIDATION**

The large-scale browser path completed, Hybrid Vision recovered through 143 calls, deterministic overwrite invariants held, and Excel delivery is durable. An estimator can now review the workbook for engineering correctness. Do not start another 143-beam production run unless the estimator requests it.
