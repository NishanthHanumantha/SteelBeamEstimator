# Phase W.13 — Repair and Validation Report

## Hybrid repairs (only after the failure stage was identified)

| Change | Why |
|---|---|
| Persist `api_success`, `api_error`, `error_type`, `parse_status`, `schema_valid`, `semantic_usable` on each beam row | W.12 lost the provider error; 117 beams were only `API_FAILED` |
| Write `hybrid_resolution_trace.json` with per-beam stop stage and reason | Completeness means every eligible beam is explainable |
| `max_api_attempts=vision_attempts` instead of hardcoded `1` | W.11 hardening disabled SDK retries and the outer live loop |
| Rate-limit backoff using `Retry-After` / 15–45 s | Transient 429 must wait; SDK `max_retries=0` remains |
| Do not retry workspace usage-limit / auth 400s | Live error is a hard cap until 2026-09-01; extra attempts waste time |
| One 30 s cooldown after 3 consecutive rate-limit failures | Intra-run TPM recovery without unbounded waits |

Not done (not justified): weaken D.2, accept invalid Vision, overwrite `cut_length` / geometry / stirrup quantity, restore SDK retries, require 143/143 resolve.

## Download repairs

| Change | Why |
|---|---|
| `?v=W.13` on `app.js` / `app.css` | New URL bypasses 7-day cache |
| Native `<a href="/api/download/<run_id>">` | Click works even if fetch JS is stale or blocked |
| Delayed `revokeObjectURL` | Avoid cancelled blob downloads |
| nginx no-cache for js/css | Future unversioned requests still refresh |

## Tests

Engine: W.5 / W.6 / W.11 unit tests **39 OK**.  
Webapp: W.12 + W.13 + W.5/W.6 Flask tests **31 OK** (plus focused re-runs after usage-limit handling).

Coverage mapped to the requested set:

| ID | Coverage |
|---|---|
| TEST-W13-01 / 03 | Historical W.11 vs W.12 stage separation |
| TEST-W13-02 / 04 / 05 | Per-beam trace + reason codes |
| TEST-W13-06 | Failed Vision does not become `HYBRID_RESOLVED` |
| TEST-W13-07 | Hybrid failure still yields Excel (stub + live) |
| TEST-W13-08–13 | Browser click, repeat, refresh, `?run=`, worker restart, failed download keeps success |
| TEST-W13-14 | Deterministic protection keys still in handoff |
| TEST-W13-15 | Controlled production 18-beam run |

## Production safety

- `HYBRID_MODE=production` (rollback to `off` tested, then restored)
- `HYBRID_MODE=authoritative` still forbidden
- workers=1
- `anthropic==0.125.0` (`>=0.49.0,<1`)
- API key not printed, not in git, remains in `/etc/steel-beam-estimator-v10.env` mode 600
- Nginx config preserved except js/css cache headers
