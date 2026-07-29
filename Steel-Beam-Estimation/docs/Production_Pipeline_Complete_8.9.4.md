# Production Pipeline Complete — MODEL_VERSION 8.9.4

> **Historical Migration Record** — functional certification of upload→Excel
> on Lightsail. Stable baseline is now **MODEL_VERSION 8.9.5**
> ([Production_Architecture_8.9.5.md](Production_Architecture_8.9.5.md),
> [Phase_D.5.6_Production_Validation_Cleanup.md](Phase_D.5.6_Production_Validation_Cleanup.md)).

**Date:** 2026-07-29  
**Status:** Historical (superseded by 8.9.5 baseline)

---

## Milestone

This release marked completion of the migration from an **offline, benchmark-dependent**
engineering workflow to a **web-native, run-scoped** production pipeline.

Upload → full estimation → Excel download now executes using only:

- the uploaded DXF drawing set
- the current `RunContext` (`STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT`)
- per-run artefacts under `web_runs/<run_id>/data/output/`

No production dependency on Version7 trees, Benchmark folders, shared historical
outputs, or offline seed artefacts.

---

## Production pipeline (certified)

```text
Upload
  → VROOT1 → R1 → R2A → R.2.1B → R.2.1C → R.2.1D
  → L.2.2 → R.3 → R.3.1 → R.1.2A → R.1.3 → VB.1
  → Estimation_Output.xlsx (download)
```

Phases D.5.1–D.5.5 delivered the RunContext architecture and stage wiring.
Lightsail production validation confirmed end-to-end execution on MODEL_VERSION 8.9.4
(including the R.3.1 package-bootstrap fix for threshold constants).

---

## What changed architecturally

| Before | After |
|--------|--------|
| Offline runners / shared folders | Per-run `web_runs/<run_id>/` isolation |
| Version7 / Benchmark discovery | Explicit previous-phase artefacts only |
| Pipeline stopped mid-chain | Upload through Excel download |
| Manual workbook copy | Same-run workbook download endpoint |

Engineering calculations, reinforcement interpretation, and Excel workbook logic
were preserved throughout — only execution architecture and path resolution migrated.

---

## Related docs

- [Phase_D.5.5_Web_Pipeline_Completion.md](Phase_D.5.5_Web_Pipeline_Completion.md)
- [ReleaseNotes.md](ReleaseNotes.md)
- `Version8/PIPELINE.md`
