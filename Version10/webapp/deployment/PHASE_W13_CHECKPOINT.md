# Phase W.13 Checkpoint

## Status

`W13_PASS_WITH_LIMITATIONS`

## Production

- Public health phase: **W.13**
- `HYBRID_MODE=production`
- Workers: 1
- Anthropic: 0.125.0
- Rollback: `off` tested, production restored
- Backup: `/opt/steel-beam-estimation/backups/w13_predeploy_20260827T060216Z`

## Findings

1. Hybrid 143/26/117 on W.12 is a **real API-failure cliff**, not a counting change. W.11 had 143/143 D.2 resolutions. Provider error recovered on W.13 live: **workspace API usage limit until 2026-09-01**.
2. Download incident `20260826_141507_88aff694`: workbook existed; `/api/download` never hit; stale cached `app.js` + button without href. Repaired with cache-bust + native `<a href>`. Browser click proven.

## Do not treat as done

- Raising the Anthropic workspace usage cap (operator / account action)
- Re-running 143 live Vision calls before 2026-09-01 (will still fail closed)

## Architecture unchanged

Vision decides what exists. VB.1 decides how it is engineered. `HYBRID_MODE=authoritative` forbidden.
