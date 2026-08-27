# PHASE W.14 — PRODUCTION CHECKPOINT

Date: 2026-08-27  
Final classification: **W14_PASS_HYBRID_API_RECOVERED**

## Classification rationale

1. Galera GF production run `20260827_093245_a32541a7` completed.
2. Claude API success continued to 64/64 attempted calls (beyond the previous 26-call cliff). Cliff classification: `PREVIOUS_26_CALL_CLIFF_NOT_REPRODUCED`.
3. Hybrid lifecycle accounting reconciles: 65 = 64 resolved + 1 evidence-unavailable fallback. Unexplained = 0.
4. The only non-resolved beam (`B35`) is explicitly `NO_USABLE_EVIDENCE` / render failed — not an unexplained API failure.
5. Deterministic overwrite counts are all 0.
6. Excel generated; automated HTTP and Playwright download/repeat/refresh/`?run` restoration passed.
7. Production remains `HYBRID_MODE=production`.

This is not estimator user acceptance.

## Production health after W.14

| Item | Value |
| --- | --- |
| Public health | `status=ok`, `phase=W.14` |
| `HYBRID_MODE` | `production` |
| API key | PRESENT (not printed) |
| Anthropic SDK | 0.125.0 |
| Gunicorn workers | 1 |
| Authoritative mode | forbidden / disabled |
| Backup | `/opt/steel-beam-estimation/backups/w14_predeploy_20260827T092841Z` |
| Nginx | unchanged (existing W.13 js/css no-cache retained) |

## Rollback

Verified `HYBRID_MODE=off` then restored `HYBRID_MODE=production` before the Galera run. Production was not left disabled.

## Remaining limitations

- One Galera beam (`B35`) had no usable evidence (`render_failed`). Deterministic engineering continued.
- 3 Hybrid-resolved beams received no R13 field patch (no matching semantic fields). Not an API failure.
- 14 W.6 envelope fallbacks use same-SHA context/detail by design. Vision still resolved them. Crops were not redesigned in W.14.
- USD cost is ESTIMATED from list rates. Anthropic billed spend change was not independently read from the provider console.
- Public multipart upload from this Windows workstation reset on the GN filename containing `&`. Server-side production submit and browser download succeeded. Estimator browser upload was not the W.14 submit path.
- A 143-beam Sixth Set production test was **not** started.

## Recommended next step

Decide a controlled 143-beam production test using the measured W.14 baseline (~$0.022 ESTIMATED per successful Vision beam, ~10.9 s Vision per beam, download path proven). Do not start that run automatically from W.14.
