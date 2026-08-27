# PHASE W.14 — PRE-FLIGHT AND API RECOVERY REPORT

Date: 2026-08-27  
Production host: `http://13.127.104.99/`  
Classification after the Galera run: **W14_PASS_HYBRID_API_RECOVERED**

## Current baseline preserved

Production at W.14 start was W.13:

- Gunicorn: 1 worker on `127.0.0.1:8001`
- `HYBRID_MODE=production`
- Anthropic SDK: `0.125.0` (not upgraded to 1.x)
- API key: configured (`PRESENT`); value not printed or copied
- Authority: Vision decides WHAT exists; VB.1 decides HOW it is engineered
- Download: durable result registry, `/api/download/<run_id>`, native `<a href>` fallback, `app.js?v=` cache-bust

W.11/W.12/W.13 protections were not redesigned: evidence timeout hardening, fail-safe deterministic continuation, result registry, Hybrid lifecycle tracing, and deterministic field protection remain in place.

## Previous $20 workspace-limit incident

W.12 Sixth Set (`20260826_111142_32321cb4`):

| Metric | Count |
| --- | ---: |
| Eligible | 143 |
| Evidence generated | 143 |
| Claude attempted | 143 |
| Claude API success | 26 |
| API failures | 117 |
| Parse/schema failures after successful API | 0 |

Provider reason persisted in W.13:

```
invalid_request_error
"You have reached your specified workspace API usage limits.
 You will regain access on 2026-09-01 at 00:00 UTC."
```

The Anthropic Strategy workspace monthly spend limit was increased from $20 to $50 (usage at increase approximately $20.15). W.14 tests whether Hybrid Vision API operation recovered beyond the previous 26-call cliff.

## Validation objective

W.14 is a measurement phase. It does not redesign P2.6.10 crops, change Hybrid semantic authority, weaken deterministic protections, parallelize Claude, or upgrade Anthropic to 1.x.

Telemetry added for this phase only:

- Normalized provider categories (`WORKSPACE_SPEND_LIMIT`, `RATE_LIMIT`, `VISION_TIMEOUT`, etc.)
- API recovery checkpoint (1st / 26th / 27th / final success)
- ESTIMATED cost summary on `hybrid_resolution_trace.json`
- Health/release label `phase=W.14`

## Input drawing identity

Primary W.14 validation drawing: Galera GF (2nd Set). First Set was not substituted.

| Slot | Exact local path | Bytes |
| --- | --- | ---: |
| General Notes | `C:\Users\nishanth.h\SteelBeamEstimator\Test_Input\2nd Set Drawings-Galera_GF\general_notes\SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf` | 2,535,801 |
| Beam Framing Plan | `C:\Users\nishanth.h\SteelBeamEstimator\Test_Input\2nd Set Drawings-Galera_GF\framing\Galera_GF_FramingPlan.dxf` | 705,021 |
| Beam Reinforcement Plan | `C:\Users\nishanth.h\SteelBeamEstimator\Test_Input\2nd Set Drawings-Galera_GF\reinforcement\Galera_GF_BeamReinforcementDetails.dxf` | 1,840,825 |

Actual production beam count, measured by the pipeline: **65** (not assumed 68–70).

The Windows public multipart POST was reset (`WinError 10054`) while sending the GN filename that contains `&`. The same three DXF files were then submitted to production Gunicorn at `127.0.0.1:8001` with the original filenames. The application stored the GN name as `SE-100-R0-SH-01SH-02GENERAL_NOTES.dxf` after filename sanitization.

## Production Anthropic configuration (no secrets)

Verified after W.14 deploy:

- `HYBRID_MODE=production`
- `ANTHROPIC_API_KEY` present in `/etc/steel-beam-estimator-v10.env` (value not printed)
- `anthropic==0.125.0`
- Worker count: 1
- Authoritative mode remains forbidden
