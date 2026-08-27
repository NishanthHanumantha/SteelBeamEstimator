# Phase W.13 — Production Acceptance Report

Public: `http://13.127.104.99/`  
Phase: **W.13**  
`HYBRID_MODE=production`  
Workers: **1** (master + worker)  
Anthropic: **0.125.0**  
Backup: `/opt/steel-beam-estimation/backups/w13_predeploy_20260827T060216Z`

## A. Hybrid — controlled 18-beam SampleBeam run

`run_id=20260827_055526_cad8ac77`

| Lifecycle stage | Count |
|---|---:|
| Eligible | 18 |
| Evidence generated | 18 |
| Claude attempted | 18 |
| Claude API success | 0 |
| Parse valid | 0 |
| Schema valid | 0 |
| E.2 accepted | 0 |
| D.2 resolved | 0 |
| R13 patch applied | 0 |
| Deterministic fallback | 18 |

Every beam: `VISION_FAILED_WITH_REASON` / `VISION_API_ERROR`.  
Persisted provider error: workspace API usage limit until **2026-09-01 00:00 UTC**.  
Retries: `attempts=2` on all 18 (retry path proven). Subsequent deploys skip further retries for this non-retryable 400.

Excel still completed: 1,424.397 kg, 92 bars, 19,560-byte XLSX.

A 143-beam live replay was **not** repeated. The W.12 failure stage is identified from artifacts plus this live confirmation of the provider message. Full 143 replay cannot succeed until the workspace cap resets.

## B. Deterministic engineering

Live run `20260827_055526_cad8ac77`:

    cut_length_overwrites = 0
    geometry_overwrites = 0
    stirrup_quantity_overwrites = 0

Same zeros on W.11, W.12, and the Galera user run.

## C. Result delivery

| Check | Result |
|---|---|
| Estimation completes | yes (live + recovered Galera run) |
| Success view | yes |
| Actual browser Download Excel click | yes, valid XLSX |
| Repeated download | yes |
| Refresh then download | yes |
| `?run=` restore then download | yes |
| Survives Gunicorn restart | yes |
| Download failure keeps success UI | unit-tested (404 workbook missing) |

Galera user run `20260826_141507_88aff694` (the incident): click now downloads 46,613 bytes `PK`.

## Rollback

`HYBRID_MODE=off` → health `mode=off enabled=false` → restored `HYBRID_MODE=production`.

## Residual limitation

Anthropic workspace usage limit until 2026-09-01 00:00 UTC. Hybrid will fallback deterministically until then. This is explained per beam, not opaque.
