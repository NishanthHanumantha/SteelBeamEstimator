# Production Architecture — MODEL_VERSION 8.9.5

**Status:** Permanent architecture reference  
**Baseline:** Stable Production Ready

---

## Final production pipeline

```text
Upload DXFs (General Notes / Framing / Reinforcement)
        │
        ▼
   web_runs/<run_id>/
     general_notes/  framing/  reinforcement/
        │
        ▼
┌─────────────────── RunContext ───────────────────┐
│  STEEL_ENGINE_ROOT  = Version8/                  │
│  STEEL_RUN_ROOT     = web_runs/<run_id>/         │
│  STEEL_OUTPUT_ROOT  = <run_root>/data/output     │
└──────────────────────────────────────────────────┘
        │
        ▼
     VROOT1  →  data/output/PhaseVROOT.1_.../
        │
        ▼
       R1    →  data/output/PhaseR.1_.../
        │
        ▼
       R2A   →  data/output/PhaseR.2A_.../
        │
        ▼
     R.2.1B  →  data/output/PhaseR2.1B_.../
        │
        ▼
     R.2.1C  →  data/output/PhaseR2.1C_.../EngineeringFacts.json
        │
        ▼
     R.2.1D  →  data/output/PhaseR2.1D_.../EngineeringFacts.json
        │
        ▼
     L.2.2   →  data/output/PhaseL.2.2_.../geometry_registry.json
        │
        ▼
       R3    →  data/output/PhaseR3_.../GeometryContexts.json
        │
        ▼
      R3.1   →  data/output/PhaseR3.1_.../EngineeringDrawingRelationships.json
        │
        ▼
     R1.2A   →  data/output/PhaseR1_2A_.../validated_beam_geometry.json
        │
        ▼
      R1.3   →  data/output/PhaseR1.3_.../beam_reinforcement_models_production.json
        │
        ▼
      VB.1   →  data/output/Production_Output/
                  Estimation_Output.xlsx
                  (workbook mapping + Excel generation inside VB.1)
        │
        ▼
   Copy to webapp outputs/
   Estimation_Output_<run_id>.xlsx
        │
        ▼
   Download endpoint (same run)
```

---

## Isolation rules

1. Each phase reads **only** prior-phase artefacts from the **same** `run_root`.
2. Each phase writes **only** to its own folder under `STEEL_OUTPUT_ROOT`.
3. `engine_root` supplies `src/` packages; it is not a shared output dump for web runs.
4. Production does not search Version7, Benchmark folders, or historical shared outputs.

---

## Web applications

| App | Role |
|-----|------|
| `Steel-Beam-Estimation/current_model/webapp` | Deployed Lightsail production package |
| `Version8/webapp` | Engine-adjacent development / parity UI |

Both invoke the same `PRODUCTION_STAGES` runners under `Version8/Run_PY/`.

---

## Health contract

`GET /health` reports Production Ready status, `model_version`, engine readiness,
`engine_root`, `web_runs_root`, `upload_folder`, and RunContext path shapes.

---

## Related

- [Phase_D.5.6_Production_Validation_Cleanup.md](Phase_D.5.6_Production_Validation_Cleanup.md)
- [Technical_Debt_Register_8.9.5.md](Technical_Debt_Register_8.9.5.md)
- `Version8/PIPELINE.md`
