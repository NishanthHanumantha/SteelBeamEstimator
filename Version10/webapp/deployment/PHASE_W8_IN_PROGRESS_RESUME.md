# PHASE W.8 — IN-PROGRESS RESUME

Saved 2026-08-25 before laptop sleep. **Lightsail was not touched.** Public remains W.7 Hybrid production.

## Status

About 60% complete. Investigation done. Adapter code written. Tests, reports, and deployment not started.

## Already on disk

New:

- `Version10/src/PhaseW8_production_vision_evidence/`
  - `__init__.py`
  - `config.py`
  - `generator.py` — B.1 context/detail render + C1C2 select + C3 gate
  - `package.py` — run-isolated `hybrid_evidence/<beam_id>/` manifests

Wired:

- `PhaseW6_hybrid_production_authority/visuals.py` — `ensure_visuals` calls W.8; W.6 envelope is explicit fallback (`render_w6_envelope_crop`)
- `PhaseW6_hybrid_production_authority/coverage.py` — P2.6.10 primary crop class + coverage identity fields
- `PhaseW6_hybrid_production_authority/orchestrator.py` — extra coverage keys
- `PhaseW5_production_hybrid_shadow/visual_sources.py` — prefer W.8 packages, then T1, then W.6
- `PhaseW5_production_hybrid_shadow/live_invoke.py` — separate context/detail paths and sources
- `PhaseW5_production_hybrid_shadow/adapter.py` — pass both images into E.2
- `PhaseP2610E2_.../live_caller.py` — optional `context_path` / `detail_path`
- `webapp/config.py` `APP_RELEASE = "W.8"`
- `webapp/routes.py` `phase: W.8`
- `webapp/tests/test_w5_hybrid_shadow.py` and `test_w6_hybrid_authority.py` health asserts updated to W.8
- `webapp/deployment/steel-beam-estimator-v10.service` comment W.8

## Not done

- `PhaseW8_production_vision_evidence/unit_tests.py`
- TEST-W8-01 through TEST-W8-14
- `PHASE_W8_P2610_CROP_PIPELINE_INVENTORY.md`
- `PHASE_W8_CURRENT_VS_TARGET_CROP_PATH.md`
- `PHASE_W8_EVIDENCE_COVERAGE_REPORT.md`
- `PHASE_W8_VALIDATION_REPORT.md`
- `PHASE_W8_CHECKPOINT.md`
- Lightsail deploy (must stay blocked until local E2E passes)

## Resume prompt

Continue Phase W.8 from tests: write unit tests, run TEST-W8 locally, bounded live Claude (`HYBRID_MAX_LIVE_CALLS=1`), then reports. Do not mutate Lightsail until local gates pass.

## Production reminder

Public `http://13.127.104.99/` is still W.7 (`phase=W.7`, `HYBRID_MODE=production`). Local label W.8 is source-only until deploy.
