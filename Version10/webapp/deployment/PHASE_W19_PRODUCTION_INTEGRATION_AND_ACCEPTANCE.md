# PHASE W.19 — PRODUCTION INTEGRATION AND ACCEPTANCE

Date: 2026-08-29  
Public: `http://13.127.104.99/`  
Classification: **W19_PRODUCTION_VALIDATION_PASS_WITH_OBSERVATIONS**

This phase deployed already-validated W.16 + W.18B. No stirrup, longitudinal, negative Dvlp.L, or role-mapping corrections were implemented.

Workstation force-shutdown interrupted the local Inizio poll while production continued. Recovery (2026-08-29 ~09:03 UTC): service still `W.19` / `HYBRID_MODE=production`; Inizio run `20260829_073647_c0df30a7` still processing (beam 135/143); poll reattached; run completed `DOWNLOAD_READY` without resubmit.

---

## 1. Starting commit

Local `main` at W.19 start:

- `3b159bff` — `docs(Version10): add W.17 Galera B1/B10/B23 BBS calculation audit`
- Production Lightsail before overlay: W.14 runtime (`HYBRID_MODE=production`, 1 worker, Anthropic `0.125.0`). Server git HEAD remained `bc2277a` (historical checkout). W.19 is an overlay of selected Version10 files, not a `git pull`.

Unrelated working-tree files were left unstaged, including `Version1/docs/Estimator_ReadingDrawings&Calculations.docx`.

---

## 2. W.16 commit integrated

`d9081f73ebe0684d66db30066efe437f5383d048`

`fix(Version10): recover GN metadata, B27 aggregation, and drawing frame identity`

Already on local `main` before W.19. Not previously deployed. Included in the W.19 runtime tarball (R.2A parsers/factory/loader, VB.1 Excel/steel aggregation, VROOT.1 floor discovery, hybrid diameter normalize, W.16 tests/docs).

W.16 unit tests: `python -m unittest Version10.webapp.tests.test_w16_metadata_aggregation` → **16 OK**.

---

## 3. W.18B changes integrated

Local commit (also the overlay source):

- `f3df2450b23a9f59af789081609682e629b691c3`
- `W19 integrate W16 metadata and W18B spacer correction`

Intended files only (27 files). Spacer engine MODEL_VERSION `9.2.0`. Additional required preservation: R.1.2B consolidator whitelist for `piece_start_mm` / `piece_end_mm` so M.2 receives real PieceGenerator extents.

---

## 4. Tests

| Suite | Result |
| --- | --- |
| `pytest Version10/src/PhaseV9_spacer_rule/tests/test_spacer_engine.py` + `test_w18b_spacer_rule.py` | **30 passed** (29 W.18B + R.1.2B extent-preservation test) |
| Round-half-up | 1040 mm → 2; 1500 mm → 3; 2490 mm → 3; 2500 mm → 4 (not banker's rounding) |
| W.16 metadata/aggregation | **16 OK** |
| Deploy import check | `IMPORT_OK` including `spacer_quantity(1040)==2` |

If these had failed, deployment would have stopped. They passed.

---

## 5. Real Galera validation (local, before deploy)

Not reconstructed 0.25L replay.

- Script: `Version10/webapp/deployment/_w19_galera_local.py`
- Run ID: `20260829_063647_61854e96`
- `HYBRID_MODE=off`
- Reinforcement DXF: `Galera_GF_BeamReinforcementDetails_SpreadOut.dxf`
- PieceGenerator extents present after R.1.2B whitelist; `extent_fallback_rows=0`; fabrication cut not used as overlap.

Local BBS (SpreadOut, hybrid off):

| Beam | Overlap | Qty | Cut | BBS rows |
| --- | ---: | ---: | ---: | ---: |
| B1 | LEFT 1039.575 + RIGHT 1039.575 | 2+2=**4** | 140 mm | 1 |
| B10 | LEFT 664.15 + RIGHT 664.15 | 2+2=**4** | 540 mm | 1 |
| B23 | LEFT 1950.088 + RIGHT 1950.088 | 3+3=**6** | 540 mm | 1 |

Did **not** reproduce B1 `3+7+3`. Frame **GF**. Five Excel sheets present.

Local Excel Project Totals remained `UNRESOLVED` Cover 40 / Fe415 ~40d even though R.2A parsed Cover 30 / Fe550 / 50d. Documented; not fixed in W.19.

---

## 6. Production B1 (Galera run `20260829_070104_a2dda3ed`)

Drawing: W.14 medium set (`Galera_GF_BeamReinforcementDetails.dxf`, not SpreadOut). Hybrid `production`.

PieceGenerator:

- `TOP_EXTRA` `CONTINUOUS_BAR` `[0.0, 4158.3]` cut 5918.3 mm
- `TOP_MAIN` `[0.0, 4158.3]`
- No LEFT/RIGHT extra pieces

M.2 (cover 30 mm, `extent_fallback=false`):

- One TOP overlap `[0.0, 4158.3]` length **4158.3 mm**
- raw 5.1583 → round-half-up **5**
- spacer Ø25 @ 1000, cut **140 mm**
- 5918.3 / 2799.6 **not** used as overlap
- **Not** `3+7+3`

BBS:

- Frame **GF**
- `Spacer bars` Ø25 qty **5** cut 0.14 m — one W.18B row
- Additional `Spacer bars` Ø12 qty 1 cut 5.478 m — pre-existing mislabeled `SPACER_BAR` from R.1.3 (not M.2 Ø25 rule). Deferred.

Gate expected 4 assumed LEFT/RIGHT extras of 1039.575 mm. Those extras exist on SpreadOut (local pass) and were implied by the W.17 cut-length/0.25L audit. On this production DXF, PieceGenerator emits one full-span extra, so W.18B correctly emits qty 5.

---

## 7. Production B10

PieceGenerator: `TOP_EXTRA_LEFT` `[0, 664.15]` + `TOP_EXTRA_RIGHT` `[1992.45, 2656.6]`.

M.2:

- LEFT 664.15 → raw 1.664 → **2**
- RIGHT 664.15 → **2**
- Aggregated BBS qty **4**, one row, cut **540 mm**
- Hooked cut 2424.2 **not** used as overlap

Matches the W.19 gate.

---

## 8. Production B23

PieceGenerator bars: `TOP_MAIN`, `BOTTOM_MAIN`, stirrup only. **No EXTRA pieces.**

M.2: skipped spacer emission (`rows: 0`) — two MAINs, no EXTRA, no cut-length fallback.

BBS: no spacer row (not qty 5).

Gate expected 6 assumed LEFT/RIGHT extras of 1950.088 mm (present on local SpreadOut). On the W.14 production DXF those extras are absent, so W.18B correctly emits 0.

---

## 9. B27 result

Galera B27 is a different member (production Steel Summary total **54.126 kg**). The W.16 42,173 kg check is Inizio 11-18F.

Inizio production Steel Summary B27 (`20260829_073647_c0df30a7`):

| Y12 | Y16 | Y20 | Y25 | Y32 | Total |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 147.661 | 49.434 | 40.198 | 237.097 | 0 | **474.390 kg** |

BBS: Frame **11-18F**. Extra-top is **2-Y25** (cut 8.55 m), not a 252 mm diameter group. The 42,173 kg aggregation failure did **not** return.

W.16 GN-table replay expected ~**468.551 kg**. Production is ~5.8 kg higher, consistent with VB.1 using IS456 ~40d bar lengths (Excel header UNRESOLVED) rather than the Inizio TABLE 1 ~38d replay. Not the 42 t bug. Not corrected in W.19.

---

## 10. Project metadata result

### Engine (production Galera R.2A)

- Cover **30 mm**, beam concrete M30
- Primary steel **Fe550**, Ld factor **50**
- M.2 `cover_mm_used=30.0`, `cover_fallback=false`

### Excel Project Totals (production Galera workbook)

- Cover: `UNRESOLVED (IS456 fallback 40 mm)`
- Development Length: `UNRESOLVED (IS456 fallback Fe415, ~40d)`
- Frame on BBS: **GF** (W.16 drawing identity survived)

### Engine (production Inizio R.2A)

- Cover **30 mm**, beam concrete M30
- Parsed primary steel **Fe550**, Ld factor **50** (W.16 live Inizio GN tests expected Fe415 / ~38d). Documented; not fixed.
- M.2 `cover_mm_used=30.0`, `extent_fallback_rows=0`, MODEL_VERSION 9.2.0

### Excel Project Totals (production Inizio workbook)

- Cover: `UNRESOLVED (IS456 fallback 40 mm)`
- Development Length: `UNRESOLVED (IS456 fallback Fe415, ~40d)`
- Frame on every BBS row inspected: **11-18F** (not TF)
- Project steel **25,402.296 kg** (W.16 replay was 25,386.482 kg)

VB.1 Excel header did not attach the R.2A loader summary on either live production path. Not corrected in W.19.

---

## 11. Production deployment commit

Overlay source: **`f3df2450b23a9f59af789081609682e629b691c3`**

Method: `pack_w19.py` → `/tmp/w19_runtime.tar.gz` + `_w19_deploy.sh` (CRLF stripped on server). Backup: `/opt/steel-beam-estimation/backups/w19_predeploy_20260829T065800Z`.

Server `git log -1` still `bc2277a`. Runtime files overlaid to W.19 (`APP_RELEASE=W.19`, spacer MODEL_VERSION 9.2.0).

---

## 12. Production health

After restart:

| Check | Result |
| --- | --- |
| `steel-beam-estimator-v10` | active |
| Public `/health` | HTTP 200, `status=ok`, `phase=W.19`, `app_release=W.19` |
| `HYBRID_MODE` | `production` (unchanged) |
| Workers | `--workers 1` |
| Anthropic SDK | `0.125.0` (unchanged) |
| API key | `PRESENT` (value not printed) |
| Import | `IMPORT_OK` |
| UI | `app.js?v=W.19` |
| After Inizio | `busy=false`, `active_run_id=null`, `status=ok` |

No startup/import errors. Hybrid authority remains semantic-only.

---

## 13. Production run IDs

| Drawing | Run ID | Result URL |
| --- | --- | --- |
| Galera GF medium | `20260829_070104_a2dda3ed` | http://13.127.104.99/?run=20260829_070104_a2dda3ed |
| Inizio 11-18F large | `20260829_073647_c0df30a7` | http://13.127.104.99/?run=20260829_073647_c0df30a7 |

Galera: 65 beams, `duration_s=1363.87`, hybrid `HYBRID_SUCCESS`, Claude 64/64 success, 1 deterministic fallback (`fallback_used=false` at run level), `identity_ok=true`. Workbook `Estimation_Output_20260829_070104_a2dda3ed.xlsx`.

Inizio: 143 beams, `duration_s=5535.74` (~92 min), hybrid `HYBRID_SUCCESS`, Claude **143/143** success, `fallback_used=false`, `unresolved=0`, `identity_ok=true`. Workbook `Estimation_Output_20260829_073647_c0df30a7.xlsx`. No unexpected hybrid fallback to W.14-era spend-limit behavior.

---

## 14. XLSX download validation

Galera — two GETs of `/api/download/20260829_070104_a2dda3ed`:

- HTTP 200, `PK` ZIP, openpyxl OK, 44632 bytes both times
- Disposition matches current run ID
- Five expected sheets
- Local copy: `Version10/Downloaded_Output/W19_Galera_GF_Estimation_Output.xlsx`

Inizio — two GETs of `/api/download/20260829_073647_c0df30a7`:

- HTTP 200, `PK` ZIP, openpyxl OK, **81331** bytes both times (not Galera’s 44632; not a stale cached Galera workbook)
- Disposition: `Estimation_Output_20260829_073647_c0df30a7.xlsx`
- Five expected sheets; Project Totals, Steel Summary, and BBS populated
- Local copy: `Version10/Downloaded_Output/W19_Inizio_11-18F_Estimation_Output.xlsx`

---

## 15. Known deferred issues (document only — no W.19 code change)

1. Varying-spacing stirrups (W.17 / Monday).
2. Longitudinal span + 2Ld / length corrections (W.17 / Monday).
3. Negative spacer `Dvlp.L` (B1 production −4.018 m) — formula `cut − span`.
4. B1 Ø12 `Spacer bars` row (mislabeled R.1.3 `SPACER_BAR`, not M.2).
5. Excel Project Totals Cover/Ld UNRESOLVED on both production workbooks despite R.2A Cover 30.
6. Production W.14 DXF B1 extra is CONTINUOUS full-span (qty 5) and B23 has no extras (qty 0). Numeric gate 4/6 is the SpreadOut geometry, confirmed locally with hybrid off. Do not treat cut-length reconstruction as the production overlap source.
7. L.2 bucket/role swaps observed on Galera B1 (`top_main_bars` holding a BOTTOM_MAIN id). Deferred role-mapping.
8. Inizio R.2A parsed Fe550 / 50d; W.16 live GN tests expected Fe415 / ~38d. Cover 30 and Frame 11-18F survived.
9. Inizio B27 474.390 kg vs W.16 replay 468.551 kg (40d fallback vs 38d table). Negative spacer Dvlp.L on Inizio B27 (−6.41 m) same class as Galera B1.

---

## 16. Production mutation status

**MUTATED.** W.16 + W.18B overlay is live on Lightsail. Configuration preserved: `HYBRID_MODE=production`, 1 gunicorn worker, Anthropic `0.125.0`. Pre-deploy file backup retained. Rollback: restore backup tree and restart `steel-beam-estimator-v10`.

---

## Classification rationale

Not `W19_VALIDATION_FAILED`: real Galera ran; W.18B tests passed; B1 did not reproduce `3+7+3`; B23 did not remain qty 5; fabrication cut was not used as overlap; workbook downloaded; service healthy.

Not a clean `W19_PRODUCTION_VALIDATION_PASS`: production W.14 DXF B1/B23 numeric gate (4 and 6) was not reproduced because PieceGenerator extras differ from SpreadOut / W.17 reconstructed zones; Excel Cover/Ld still UNRESOLVED; Inizio B27 is 474.390 kg not 468.551 kg.

**W19_PRODUCTION_VALIDATION_PASS_WITH_OBSERVATIONS**
