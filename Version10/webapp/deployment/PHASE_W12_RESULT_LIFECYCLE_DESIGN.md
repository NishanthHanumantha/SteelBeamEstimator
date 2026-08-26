# PHASE W.12 — RESULT LIFECYCLE DESIGN

Saved: 2026-08-26

Authority model is unchanged: Vision decides **what** reinforcement exists; the deterministic engine decides **how** it is engineered and quantified.

---

## States (mapped onto existing architecture)

No new database or job queue. Disk is the source of truth after the worker process is gone.

| Conceptual state | How it is represented |
|------------------|------------------------|
| PROCESSING | In-memory job `running` + `result_manifest.json` `lifecycle=PROCESSING` |
| HYBRID_RUNNING | Same, with `/api/status` overlay from `hybrid_progress.json` (W.11) |
| EXCEL_GENERATED | Workbook copied to `webapp/outputs/Estimation_Output_{run_id}.xlsx`; manifest not yet `DOWNLOAD_READY` |
| RESULT_REGISTERED / DOWNLOAD_READY | Manifest `lifecycle=DOWNLOAD_READY` **and** workbook exists |
| DOWNLOAD_IN_PROGRESS | Client-only (fetch+blob); server records `download_attempts` |
| DOWNLOAD_FAILED / RESULT_UNAVAILABLE | Workbook missing after registration; status stays completed; download returns explicit JSON |
| FAILED | Manifest `lifecycle=FAILED`; no fake Download Excel |
| PROCESSING_INTERRUPTED | Manifest PROCESSING but worker memory gone (restart mid-run) |
| EXPIRED | Not auto-expired. Retention = until operator cleanup |

**EXCEL_GENERATED is not treated as DOWNLOAD_READY.** Registration requires the durable copy to exist, then writes `DOWNLOAD_READY`.

---

## Durable artefacts (run-isolated)

1. **Workbook copy** — `webapp/outputs/Estimation_Output_{run_id}.xlsx`  
   Download always opens this path derived from `run_id`, never a client-supplied filesystem path.

2. **Manifest** — `data/web_runs/<run_id>/result_manifest.json`  
   Schema `w12_result_manifest_v1`. Stores lifecycle, workbook basename, sizes, summary, hybrid summary, download attempt counters. **No absolute paths in public JSON. No secrets.**

3. **Legacy recovery** — if the xlsx copy exists and memory/manifest is missing (pre-W.12 runs, worker restart), status/download reconstruct `DOWNLOAD_READY`.

---

## API contracts

### Status

- Valid `run_id` only: `^[0-9]{8}_[0-9]{6}_[0-9a-f]{8}$`
- Hydrates from disk when `_JOBS` is empty
- Adds: `result_lifecycle`, `excel_generated`, `excel_exists`, `result_registered`, `download_ready`
- Does **not** return `workbook_path`

### Download

- Resolves file solely as `OUTPUT_ROOT / Estimation_Output_{run_id}.xlsx` under `OUTPUT_ROOT.resolve()`
- HTTP 200 + `Content-Disposition: attachment` + xlsx MIME on success
- Invalid run → 404 `INVALID_RUN`
- Not ready → 400 `WORKBOOK_NOT_READY`
- Registered but missing file → 404 `RESULT_UNAVAILABLE` (does not delete anything)
- Failed download does **not** remove the workbook
- Retry is always allowed while the file remains

### Health

`phase=W.12`, `result_delivery.durable_registry=true`. No API keys.

---

## Frontend

- Download is a **button**, not a navigation `<a href>`.
- Fetch blob → object URL → `a.download`. JSON errors stay on the success view with a visible retry message.
- `?run=<run_id>` and `sessionStorage` persist the run. Refresh restores completion if the result is still on disk.
- After `status=success`, later 404/network misses **do not** hide the success view.

---

## Cleanup / retention

- Upload copies under `webapp/uploads/<run_id>` are still removed after the pipeline (temp only).
- Staging `web_runs/<run_id>` is retained (existing behaviour).
- `webapp/outputs/Estimation_Output_{run_id}.xlsx` is **never** deleted by download or by a failed download.
- No automatic expiry job in W.12.

---

## Worker restart

| Situation | Behaviour |
|-----------|-----------|
| Restart after DOWNLOAD_READY | Status/download reconstruct from disk |
| Restart during PROCESSING | Explicit interrupted error; no fake Excel |
| Restart after Excel copy but before manifest | Legacy file recovery registers DOWNLOAD_READY |

---

## Safety

- `HYBRID_MODE=authoritative` remains forbidden
- One Gunicorn worker
- No parallel Claude
- Path traversal rejected by `run_id` regex + `relative_to(OUTPUT_ROOT)`
