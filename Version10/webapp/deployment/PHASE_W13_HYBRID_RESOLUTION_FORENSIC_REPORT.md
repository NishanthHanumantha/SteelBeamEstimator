# Phase W.13 — Hybrid Resolution Forensic Report

Date: 2026-08-27  
Production: `http://13.127.104.99/`  
Backup: `/opt/steel-beam-estimation/backups/w13_predeploy_20260827T060216Z`

## Lifecycle definitions

These stages are counted separately. They are not interchangeable.

| Stage | Meaning |
|---|---|
| Eligible | Beam is in the deterministic registry and Hybrid is on |
| Evidence generated | Context and detail PNGs selected for the beam |
| Claude attempted | A live Vision request was issued (`called=true`) |
| Claude API success | Anthropic returned a usable response (`audit.success` / tokens > 0) |
| Parse valid | Response text parsed |
| Schema valid | C.5 schema accepted |
| E.2 accepted | Semantic payload usable (`semantic_usable`) |
| D.2 resolved | Hybrid semantic object produced (`hybrid_status=OBSERVED`) |
| R13 patch applied | Canonical handoff patched at least one Vision-owned field |
| Deterministic fallback | Beam did not reach `HYBRID_RESOLVED`; engineering continues |

`hybrid_resolution_trace.json` records one final status and one reason code per beam. Opaque `UNRESOLVED` is no longer the only label.

## W.11 vs W.12 (Sixth Set, 143 beams)

| | W.11 `20260826_084708_f74912b8` | W.12 `20260826_111142_32321cb4` |
|---|---:|---:|
| Eligible | 143 | 143 |
| Evidence generated | 143 | 143 |
| Claude attempted | 143 | 143 |
| Claude API success | 143 | 26 |
| Parse / schema / E.2 / D.2 | 143 | 26 |
| R13 patch applied | 140 | 26 |
| R13 patch not applied (D.2 resolved, no matching fields) | 3 | 0 |
| Deterministic fallback | 0 | 117 |
| Timeouts | 0 | 0 |
| Sequence | all `OBSERVED` | 26 `OBSERVED`, then 117 `API_FAILED` |

W.11 **did** complete 143/143 Claude API successes and 143/143 D.2 resolutions. Three beams were Hybrid-resolved but not R13-patched (`PATCH_NOT_APPLIED` / no matched Vision fields). That is not the same as “Claude request completed”.

W.12 is a **real behavioural difference**, not a counting change. Coverage still maps `OBSERVED` → `claude_success`. The 117 “unresolved” beams are specifically `failure_category=API_FAILED` after a successful HTTP-sized round trip of ~1.6–3.1 s with **zero tokens**. They are not parse, schema, E.2, D.2, or R13 failures.

W.11 ran **before** timeout-hardening (`anthropic max_retries=0`, `max_api_attempts=1`). W.12 used that hardening. That made transient/quota API failures fail closed immediately and **did not persist** `audit.error` on the beam row, so W.12 artifacts could not name the provider error.

## W.12 unresolved category (117)

All 117 share:

- evidence: PRIMARY context+detail present
- Claude attempted: yes
- timeout: no
- `retry_count=0`, `attempts=1` (live_caller `max_api_attempts` was hardcoded to `1`)
- `error_type` not persisted on the row
- reason reconstructed as `VISION_API_ERROR` / existing code `API_FAILED`

Historical W.12 rows still lack the provider message. The W.13 live run persisted it (below).

## User post-W.12 run

`20260826_141507_88aff694` (Galera GF, 65 beams):

- 64 `VISION_API_ERROR`
- 1 `EVIDENCE_UNAVAILABLE` (`NO_USABLE_EVIDENCE`)
- Excel 46,613 bytes generated (`DOWNLOAD_READY`)
- `download_attempts=0` — `/api/download` was never hit

## W.13 live confirmation of the API error

Controlled 18-beam run `20260827_055526_cad8ac77` persisted:

- `error_type=ClaudeAPIError` on all 18 attempted beams
- `attempts=2`, `retry_count=1` (retry plumbing now works)
- `api_error`: HTTP 400 `invalid_request_error`  
  **“You have reached your specified workspace API usage limits. You will regain access on 2026-09-01 at 00:00 UTC.”**

This is a **workspace usage cap**, not RPM backoff, not crop quality, not schema, not D.2. It matches the W.12 cliff (26 successes then hard fail) and the later 0/64 Galera run the same day.

Retries cannot recover a monthly/workspace cap. W.13 therefore:

- persists sanitized `api_error` / `error_type`
- writes `hybrid_resolution_trace.json`
- retries transient API failures
- does **not** retry non-retryable usage-limit / auth errors

## Root cause

1. **Provider:** Anthropic workspace API usage limit (regains 2026-09-01 00:00 UTC).  
2. **Observability gap:** W.12 discarded `audit.error`, collapsing everything to `API_FAILED`.  
3. **Retry gap:** W.11 timeout hardening set SDK `max_retries=0` and adapter `max_api_attempts=1`, so even retryable 429s would not wait. The W.12 cliff is consistent with quota exhaustion mid-run, not with parse/D.2 regression.

No Hybrid architecture change. No P2.6.10 crop rewrite. Engineering overwrite counts remained 0 on all forensic runs.
