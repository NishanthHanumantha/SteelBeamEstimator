# PHASE W.9 — PRODUCTION GO-LIVE REPORT

Saved: 2026-08-26  
Classification: **W9_PASS_PRODUCTION_GO_LIVE**

Public application: http://13.127.104.99/

## 1. Final classification

**W9_PASS_PRODUCTION_GO_LIVE**

The proven W.8 P2.6.10 Hybrid evidence path is deployed on Lightsail Version10. The controlled First Set production run used distinct context + detail images on the primary path (`n_images = 2`), invoked live Claude Vision, applied Hybrid semantic resolution into canonical R13, completed VB.1, and produced a downloadable Excel workbook. Deterministic engineering remained the authority for cut length, stirrup quantity, geometry, and steel-weight formulas.

Five beams used **explicit** W.6/compatibility fallbacks (logged, not silent). Those are crop-coverage limitations, not a failed go-live. The primary path is no longer the W.7 duplicated-envelope caller.

**GO** for estimator use on http://13.127.104.99/ with `HYBRID_MODE=production`.

## 2. Production version

| Moment | Version |
|------|---------|
| Before | W.7 (`APP_RELEASE=W.7`, `/health` `phase=W.7`, W.8 adapter **absent**) |
| After | **W.9** (`APP_RELEASE=W.9`, `/health` `phase=W.9`, W.8 adapter **present**) |
| Local implementation commit | `751d2c72` |
| Instance git (unchanged; file-copy deploy) | `bc2277ab` |
| Backup | `/opt/steel-beam-estimation/backups/w9_predeploy_20260826T064810Z` |

## 3. Hybrid / Anthropic / key

| Item | Value |
|------|--------|
| Current Hybrid mode | **production** |
| Rollback probe | `HYBRID_MODE=off` → `/health` `mode=off`, `production_may_invoke_claude=false` |
| Restored | **production** |
| Anthropic | **0.125.0** (`>=0.49.0,<1`, not 1.x) |
| API key status | **PRESENT** (value never printed) |
| Env file | `/etc/steel-beam-estimator-v10.env` mode `600` `root:root` |
| `/health` secret leak | none (`sk-ant-` count 0) |

## 4. Controlled production run

Preferred set: First Set Galera OHT&STP (`/home/ubuntu/w3_smoke`).

Canonical go-live run: **`20260826_065256_4ba41266`**

| Metric | Value |
|--------|--------|
| Status | success |
| Wall time | 340.2 s (pipeline 321.05 s; Hybrid stage 297.55 s; Claude latency 200.924 s) |
| Start | 2026-08-26 06:52:56 UTC |
| End | 2026-08-26 06:58:17 UTC |
| Model | `claude-sonnet-4-5` |
| Classification | `HYBRID_SUCCESS` |
| Beam count | 18 |
| Hybrid eligible | 18 |
| Evidence generated | 18 |
| P2.6.10 primary | **13** |
| T1 native selected | 0 |
| W.6 / compatibility fallback | **5** (B11, B15, B16, B17, B18) |
| VISION_NOT_READY as silent skip | 0 (C3 failures became explicit fallback) |
| Unavailable | 0 |
| Unexplained | **0** |
| Identity | `18 = 13 primary + 0 T1 + 5 fallback + 0 unavailable` |
| Claude attempted | 18 |
| Claude successful | 18 |
| Claude failures | 0 |
| Hybrid resolved | 18 |
| Deterministic fallback beams | 0 |
| Semantic fields applied | 284 (18 beams patched) |
| Excel | HTTP 200, ZIP/`PK`, 19539 bytes, `Estimation_Output_20260826_065256_4ba41266.xlsx` |
| Steel quantity | **1425.732 kg**, 18 beams, 92 bars, `IS_456_DETERMINISTIC` |
| Single-flight | concurrent POST → HTTP 409 |
| cut_length_overwrites | **0** |
| stirrup_quantity_overwrites | **0** |
| geometry_overwrites | **0** |

W.7 go-live on the same drawing was 1432.237 kg. Weight movement is Vision semantic identity (counts/diameters), not a VB.1 formula change.

## 5. Production evidence architecture (final)

```
DXF
  → Deterministic Geometry + Beam Registry
  → P2.6.10-A title localize + B adaptive extents + B.1 M.1 render
  → C1/C2 evidence selection
  → C3 readiness / completeness gate
  → selected context PNG + selected detail PNG
  → C.5 / E.2 Claude Vision (n_images = 2)
  → D.2 Hybrid semantic resolution
  → Canonical R13 semantic patch
  → VB.1 deterministic engineering
  → Cut length / DL / Anchorage / Hooks / Stirrup engineering
  → Pieces / Weight / BBS
  → Excel
```

Authority unchanged: Vision decides **what** reinforcement exists; VB.1 decides **how** it is engineered and quantified.

## 6. Rollback

Primary rollback remains: set `HYBRID_MODE=off` in `/etc/steel-beam-estimator-v10.env` and restart `steel-beam-estimator-v10`. No code deletion. No API key removal.

TEST-W9-12/13: off then restored to production. Final public `/health` `status=ok`, `phase=W.9`, `mode=production`. Nginx unchanged. One Gunicorn worker.

## 7. TEST-W9 results

| Test | Result |
|------|--------|
| TEST-W9-01 Pre-deploy audit | PASS (W.7 live, anthropic 0.125.0, key PRESENT) |
| TEST-W9-02 Import / startup | PASS (`IMPORT_OK`, `/health` W.9) |
| TEST-W9-03 Evidence generation | PASS (one-beam B1 PRIMARY on production venv; 18/18 in E2E) |
| TEST-W9-04 Context + detail selection | PASS |
| TEST-W9-05 Two-image contract | PASS (`n_images=2`, primary distinct) |
| TEST-W9-06 Live Claude | PASS 18/18 |
| TEST-W9-07 D.2 handoff | PASS 18 beams, 284 fields |
| TEST-W9-08 VB.1 preservation | PASS overwrites 0/0/0 |
| TEST-W9-09 Full production E2E | PASS run `20260826_065256_4ba41266` |
| TEST-W9-10 Coverage identity | PASS unexplained=0, identity_ok=true |
| TEST-W9-11 Failure isolation | PASS (local W.6/W.8 unit tests; Claude-failure Excel-safe) |
| TEST-W9-12 Rollback off | PASS |
| TEST-W9-13 Restore production | PASS |
| TEST-W9-14 Secret safety | PASS |

Local pre-copy units: 26 tests OK (`PhaseW8` + `PhaseW6`).

## 8. Remaining limitations (explicit, non-blocking)

1. First Set beams **B11, B15, B16, B17, B18** use explicit W.6/compatibility evidence instead of P2.6.10 primary. Four of those send the same envelope PNG as both context and detail **because fallback was selected and logged**.
2. Native T1 OpenCV crops remain rare on this drawing (0 selected).
3. File-copy deploy; instance `git` HEAD is still `bc2277ab`.
4. `anthropic` must stay **`<1`**.
