# PHASE W.9 — RUNTIME DEPLOYMENT INVENTORY

Built from actual W.8 imports (`generator.py`, `visuals.py`, `live_invoke.py`, `adapter.py`, `live_caller.py`, C.5 `claude_call.py`) plus the production web wiring.  
Local commit: `751d2c72`. Production before copy: W.7 (`bc2277ab` on instance).

Classification key:

- **A. REQUIRED RUNTIME** — copy
- **B. EXISTING PRODUCTION FILE — UPDATED** — overwrite with W.8 wiring
- **C. TEST ONLY — DO NOT DEPLOY**
- **D. RESEARCH ONLY — DO NOT DEPLOY**
- **E. REPORT / DOCUMENTATION**

## A. REQUIRED RUNTIME (new on production)

| Path | Why |
|------|-----|
| `src/PhaseW8_production_vision_evidence/__init__.py` | Package |
| `src/PhaseW8_production_vision_evidence/config.py` | Classes, evidence layout |
| `src/PhaseW8_production_vision_evidence/generator.py` | B.1 pair + C1/C2 + C3 + explicit fallback |
| `src/PhaseW8_production_vision_evidence/package.py` | Run-isolated `prepare_production_evidence()` |

Production `__init__` stubs (tarball overlay; do **not** import research orchestrators):

| Path | Why |
|------|-----|
| `src/PhaseP2610C1C2_evidence_inventory_candidate_selection/__init__.py` | Stub so `selector` import does not load C1C2 orchestrator |
| `src/PhaseP2610B2_render_quality_directional_recovery/__init__.py` | Stub so `quality` import does not load B.2 orchestrator |
| `src/PhaseP2610C3_visual_completeness_claude_shadow/__init__.py` | Stub so C3 gate import does not load C.3 orchestrator |

## B. EXISTING PRODUCTION FILE — UPDATED

Hybrid wiring (W.7 already deployed these; W.8 content replaces W.7 crop/duplication behavior):

| Path | Change |
|------|--------|
| `src/PhaseW6_hybrid_production_authority/visuals.py` | Call W.8 first; W.6 envelope is explicit fallback |
| `src/PhaseW6_hybrid_production_authority/coverage.py` | P2.6.10 primary vs compatibility identity |
| `src/PhaseW6_hybrid_production_authority/orchestrator.py` | Coverage fields |
| `src/PhaseW6_hybrid_production_authority/{config,handoff,observability,__init__,__main__}.py` | Keep in pack for a consistent W.6 tree |
| `src/PhaseW5_production_hybrid_shadow/live_invoke.py` | Separate `context_path` / `detail_path` |
| `src/PhaseW5_production_hybrid_shadow/visual_sources.py` | Prefer W.8 packages |
| `src/PhaseW5_production_hybrid_shadow/adapter.py` | Pass both images into E.2 |
| `src/PhaseP2610E2_.../live_caller.py` | Optional context/detail paths |
| `webapp/config.py` | `APP_RELEASE = "W.9"` |
| `webapp/routes.py` | `/health` `phase=W.9` |
| `webapp/deployment/steel-beam-estimator-v10.service` | Comment only; **still `--workers 1`** |

P2.6.10 **functions** reused by `generator.py` (already present on Lightsail; re-copy runtime modules only):

| Path | Role |
|------|------|
| `PhaseP2610A_.../{config,title_localizer,region_builder,cropper}.py` | Title localize + M.1 render |
| `PhaseP2610B_.../{config,envelope,evidence,completeness}.py` | Adaptive extents |
| `PhaseP2610B2_.../{config,geometry,quality}.py` | Render quality |
| `PhaseP2610C1C2_.../{config,inventory,selector}.py` | Candidate select |
| `PhaseP2610C3_.../{config,evidence_model,target_anchor_validator,visual_completeness_gate}.py` | Completeness gate |

Already on production from W.7 and **not re-copied** (no W.8 delta required):

- `Run_PY/run_phase_w6_hybrid_production_authority.py`
- `PhaseP2610C5_.../claude_call.py` (hardcodes `n_images: 2`)
- `PhaseP253_.../claude_vision_client.py`
- `PhaseM.1_.../dxf_renderer.py`
- `PhaseT1_.../geometry_envelope.py`
- `webapp/services/{estimation_service,version10_adapter,hybrid_shadow_service}.py`
- `webapp/.venv` and `anthropic==0.125.0`

## C. TEST ONLY — DO NOT DEPLOY

- `src/PhaseW8_production_vision_evidence/unit_tests.py`
- `src/PhaseW6_hybrid_production_authority/unit_tests.py`
- `src/PhaseW5_production_hybrid_shadow/unit_tests.py`
- `webapp/tests/test_w5_hybrid_shadow.py` (label-only change; not required on server)
- `webapp/tests/test_w6_hybrid_authority.py`
- `webapp/tests/run_w8_live_verify.py`
- `webapp/deployment/smoke_w9.py` (copied to `/tmp` for the controlled go-live run only, not into the engine tree)

## D. RESEARCH ONLY — DO NOT DEPLOY

- `phase_p2610c1c2_orchestrator.py` / C.3 / C.4 / C.5 benchmark orchestrators
- B.2 / B.3 recovery experiment loops
- Fourth-set sampling workflows
- `data/output/PhaseP2610C*` review trees
- `_pdf_fixture`, `_anti_tmp`, `_report_fixture`
- Historical `data/web_runs` (except using existing First Set smoke DXFs)

## E. REPORT / DOCUMENTATION

- `webapp/deployment/PHASE_W9_*.md` (this set)
- `webapp/deployment/PHASE_W8_*.md` (already local; not required to copy for runtime)

## Explicitly not deployed

- Workstation `.env`
- `/etc/steel-beam-estimator-v10.env` (must remain the only key location)
- venv, `__pycache__`, Nginx site, Gunicorn worker count

## Deploy method

1. Snapshot overlapping production files to `/opt/steel-beam-estimation/backups/w9_predeploy_*`.
2. `scp` `w9_runtime.tar.gz` → `/tmp/w9_runtime.tar.gz`.
3. Extract into `/opt/steel-beam-estimation/SteelBeamEstimator/`.
4. `compileall` + import check **before** restart.
5. Install systemd unit from the extracted copy (comment-only) and `systemctl restart steel-beam-estimator-v10`.
6. Confirm `/health` `phase=W.9`, `hybrid.mode=production`, `anthropic==0.125.0`, 1 worker.
