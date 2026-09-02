# Production Truth

**Consult this file first** before modifying Steel Beam Estimation production behaviour.

Phase 1 baseline: `REPOSITORY_FORENSICS_REPORT.md`  
Phase 2 boundary: `PRODUCTION_BOUNDARY_MANIFEST.md`  
Mixed-package files: `PRODUCTION_MODULE_INDEX.md`  
Runners: `RUNNER_MANIFEST.md`

---

## CURRENT STATUS

**Version10 Hybrid — Production**

## CURRENT RELEASE

**W.19.1** (`Version10/webapp/config.py` `APP_RELEASE`)

## CURRENT WEB ENTRY

`Version10/webapp/wsgi.py` → Flask `app:app`

Live Lightsail: Gunicorn `wsgi:app` bind **`127.0.0.1:8001`**, **1 worker**, overlay root `Version10/`.  
Public: Nginx → `http://13.127.104.99/`

`HYBRID_MODE=production` is set by the **server environment overlay**, not by the systemd unit default (`HYBRID_MODE=off` in the unit file is stale relative to live overlay).

## CURRENT PIPELINE

**14 stages** in `Version10/webapp/config.py` `PRODUCTION_STAGES`, ending in **W.6 (HYBRID) + VB.1**.

1. VROOT1  
2. R1  
3. T1  
4. R2A  
5. R21B  
6. R21C  
7. R21D  
8. L.2.2  
9. R3  
10. R.3.1  
11. R.1.2A  
12. R.1.3  
13. W.6 (HYBRID)  
14. VB.1  

## CURRENT HYBRID

**W.5 / W.8 → Claude Vision → D.2 → W.6 handoff**

```
DXF
 → VROOT1 discovery
 → Deterministic CAD / geometry (through R.1.3)
 → T.1 stirrup evidence
 → W.8 context/detail evidence
 → Claude Vision (C.5 / P.253 / E.2)
 → D.2 semantic hybrid resolution
 → W.6 production handoff
 → R.1.3 artefacts remain the engineering source for VB.1
 → VB.1 steel / BBS / Excel
```

## CURRENT ENGINEERING AUTHORITY

**R.1.3 / deterministic engineering → VB.1**

VISION determines **WHAT** reinforcement exists (semantic interpretation).

DETERMINISTIC ENGINE determines **HOW** it is engineered and quantified:

- Geometry  
- Spacers / cover (M.2)  
- Engineering lengths  
- Development Length  
- Anchorage  
- Hooks / bends  
- Cut lengths  
- Stirrup **quantity**  
- Piece generation  
- Unit weight  
- Steel quantity  
- BBS  
- Excel  

W.6 `handoff.py` may patch count / diameter / role. It **protects** cut length, stirrup quantity, geometry, spacers, kg, BBS.

## CURRENT OUTPUT

Steel Quantity → BBS → Excel (`Production_Output/Estimation_Output.xlsx`)

---

## DO NOT USE AS CURRENT PRODUCTION ARCHITECTURE

These exist in the tree and **must not** be treated as the live system:

- **Version1–Version9** historical engines and UIs  
- **`Steel-Beam-Estimation/`** 8.9.5 packaging and `Production_Architecture_8.9.5.md`  
- Root README historical Version6 “active development” section (corrected in Phase 2 to point here; Version6 remains an archive tree)  
- Stale **8.9.5 / frozen V8** pipeline descriptions  
- Experimental benchmark orchestration (`PhaseP2610E*`, `PhaseQA*`, `PhaseVA.2`, `PhaseVTEST*`, `PhaseVRUN.1`)  
- Old deployment recipes (`pack_w3.py` … earlier than `pack_w191.py`; Gunicorn `:8000` 8.9.x comments)  
- `run_phase_l2_engineering_reinforcement_interpretation.py` (L.2 is **not** a web stage; web uses **L.2.2**)  
- `run_phase_r13_reinforcement_piece_generation.py` as a web stage (pieces load **inside R.1.3**)  
- 91 non-web `Run_PY` runners as if they were `PRODUCTION_STAGES`

**Benchmark-named packages may contain production modules.**  
Do not archive based on package name alone. See `PRODUCTION_MODULE_INDEX.md`.

---

## VERSION8 RUNTIME GATE (CLOSED)

**Closed:** 2026-08-31 (Phase 3)

Live web **R.2A** and **R.2.1B** now execute **Version10** source:

- `Version10/Run_PY/run_phase_r2a_engineering_context.py` → `Version10/src/PhaseR.2A_engineering_context/` with `engine_root=Version10`
- `Version10/Run_PY/run_phase_r21b_semantic_interpreter.py` → `Version10/src/PhaseR2.1B_engineering_semantic_interpreter/` with `engine_root=Version10`

GN discovery (Version10 factory, production contract):

1. `STEEL_RUN_ROOT/general_notes/*.dxf` (uploaded run GN — authoritative)
2. Version10 `beam_registry.json` pointer
3. `Version10/data/Benchmark_Set_2/general_notes/`

**VERSION8 ARCHIVE STATUS = CLOSED for live R.2A / R.2.1B runtime.**  
**VROOT1 Version8 filesystem coupling closed:** 2026-09-02 (Phase 5a) — no write to `Version8/data/output/`, no CLI default under `Version8/data/Benchmark_Set_*`. Web still passes the upload folder. Canonical VROOT1 artefacts remain run-scoped (`STEEL_OUTPUT_ROOT`).

Do **not** delete or move `Version8/` until Phase 5b (archive) is explicitly requested. Historical CLI runners, YAML, and Lightsail `:8000` rollback docs may still name Version8. Archive decision remains **CONDITIONAL_GO**.

Validation: syntax/import of both runners; W.16; W.19.1; W.2 smoke; W.6 Flask + W.6 unit tests; W.18B spacer. No live Claude estimate.

---

## Cursor modification rules

- Production entry: `Version10/webapp/` + 14 `PRODUCTION_STAGES` only.  
- Hybrid: `PhaseW5_*` / `PhaseW6_*` / `PhaseW8_*` plus listed Vision files in mixed packages.  
- Live R.2A / R.2.1B load Version10 source. Do not reintroduce Version8 into those runners.  
- Do not consume Claude API credits for casual validation.
