# PHASE W.11 — TIMEOUT HARDENING REPORT

Saved: 2026-08-26  
SDK on production: **anthropic==0.125.0**

---

## Architecture

Hybrid remains sequential (one Gunicorn worker, one Claude call at a time). Timeouts wrap existing W.5/W.6/E.2/C.5 call chain. No parallel Vision. No engineering formula changes.

```
per beam evidence  →  HYBRID_EVIDENCE_TIMEOUT_SECONDS (120)
        ↓ timeout → UNAVAILABLE / DETERMINISTIC_FALLBACK, continue

per Claude HTTP    →  Anthropic(timeout=HYBRID_PER_CALL_TIMEOUT_S, max_retries=0)
        ↓ retry    →  HYBRID_MAX_RETRIES application attempts (1 retry = 2 tries)
        ↓ backstop →  HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS (250) via SIGALRM on Linux
        ↓ timeout/error → no fabricated Vision; deterministic R13 for that beam; continue
```

---

## SDK configuration (0.125.0)

| Layer | Before | After |
|-------|--------|--------|
| `Anthropic(...)` | `timeout=ClaudeConfig.TIMEOUT_SECONDS` (120), **SDK max_retries default 2** | `timeout=120`, **`max_retries=0`** |
| `messages.create` | no per-request timeout | `timeout=HYBRID_PER_CALL_TIMEOUT_S` (120) |
| `ClaudeClient.generate_vision_response` | always `MAX_RETRIES=3` | Hybrid passes `max_attempts = max_retries+1` |
| E.2 `MAX_API_ATTEMPTS` | 2 extra wrappers | Hybrid sets `max_api_attempts=1`; timeouts are not retried |
| `HYBRID_PER_CALL_TIMEOUT_S` | loaded but unused by the client | wired through C.5 / E.2 / W.5 |

Worst-case wait for **one beam's Claude path**: 2 × 120 s = 240 s, capped by **250 s** total beam budget. A hung socket is interrupted by SIGALRM on Linux (ThreadPoolExecutor backstop on Windows tests).

---

## Environment (names only)

Already present on production, now honoured:

- `HYBRID_PER_CALL_TIMEOUT_S=120`
- `HYBRID_MAX_LIVE_CALLS=0` (unlimited count; each call still bounded)
- `HYBRID_MAX_WALL_S=0` (no additional Claude-loop wall; subprocess 7200 s remains the stage backstop)

Added:

- `HYBRID_MAX_RETRIES=1`
- `HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS=250`
- `HYBRID_EVIDENCE_TIMEOUT_SECONDS=120`

Chosen from measured production: Vision avg **10.8–12.4 s**, P2.6.10 render ~**25 s**/beam on the large drawing. 120 s evidence is ~5× that render; 120 s Vision is ~10× measured calls.

---

## Per-beam behaviour

1. Progress heartbeat: `hybrid_progress.json` (beam_id, index, total, phase, label). Never secrets.
2. Evidence timeout → `EVIDENCE_TIMEOUT`, explicit unavailable, **do not fabricate crops**, continue.
3. Vision timeout → `VISION_TIMEOUT` / `HYBRID_UNAVAILABLE`, deterministic semantics, continue.
4. API error → existing `HYBRID_ERROR` / unusable path; no Vision fabrication.
5. Remaining beams continue. VB.1 and Excel still run.

---

## Observability

| Artefact | Role |
|----------|------|
| `hybrid_progress.json` | Live “which beam, how long” for `/api/status` |
| `hybrid_lifecycle.json` | Start/end, evidence duration, Claude counts, timeout_count |
| Existing W.6 observability + W.10 monitor | Unchanged; timeout_count now populated from adapter |

`/health` publishes timeout settings (not keys). `/health` `sk-ant-` count remains 0.

---

## UI / stale run

- Status overlay replaces the static Hybrid label while `hybrid_progress.json` exists.
- Elapsed time shown on the processing view.
- 404 (worker restart) → clear failure, not an infinite spinner.
- Polling retries 5 network misses before giving up.
- Single-flight `GUARD` is in-memory: process restart clears busy. No new job queue.

---

## Safety guarantees

- Hybrid semantic authority unchanged (Vision WHAT; VB.1 HOW).
- No Vision result invented on timeout.
- One failed beam cannot block Excel indefinitely.
- `HYBRID_MODE=off` still skips Claude.
- Monitoring/progress writes are fail-safe.
