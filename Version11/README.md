# Version11 — Active Accuracy Development Tree

**Do not edit Version10.** Version10 is the frozen W.19.1 Hybrid production/demo baseline.

This tree is a controlled fork of the Version10 production boundary. It is **not** a live deployment and must not be copied over the Lightsail `:8001` estimator until a later authorized phase.

| Item | Value |
|---|---|
| Source baseline | Version10 W.19.1 |
| `APP_RELEASE` | `W.19.1` (unchanged; this is a zero-change fork) |
| `ENGINE_LABEL` | `Version11` |
| Production stages | same 14 as Version10 |
| Accuracy work | not started in V11.0 |

Start here:

- `V11_DEVELOPMENT_RULES.md` — permanent rules
- `V11_BASELINE_MANIFEST.md` — what was copied
- `V11_DEPENDENCY_CLASSIFICATION.md` — MUST_COPY / EXCLUDED / …
- `V11_VS_V10_BASELINE_REPORT.md` — zero-change comparison
- `PHASE_V11_0_COMPLETION_REPORT.md` — phase status

Local web entry: `Version11/webapp/` (`wsgi.py` / `app.py`). `ENGINE_ROOT` is this `Version11/` folder.
