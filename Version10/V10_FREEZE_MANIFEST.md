# Version10 Freeze Manifest

**Phase:** V11.0  
**Freeze date:** 2026-09-11  
**Status:** FROZEN PRODUCTION / DEMO BASELINE  
**Do not modify Version10 production code during Version11 development.**

---

## Git freeze state

| Field | Value |
|---|---|
| Branch | `main` (tracks `origin/main`) |
| HEAD commit | `59330bda4fc62919ef8e3b1371a5afc377b20161` |
| Subject | `docs: add architecture code map with Claude call path` |
| Date | 2026-09-10 18:23:59 +0530 |
| `git describe` | `v8.9.5-56-g59330bda` |
| Annotated production tag | none for W.19.1 (nearest historical tag is `v8.9.5`) |

No freeze tag was created in this phase. No commit was created in this phase.

### Uncommitted repository state (not discarded, not silently committed)

Untracked at freeze time (not Version10 production Python / runtime logic):

- `Version10/V10_Report_Docs/StructuralTeamDiscussion.docx`
- `Version10/V10_Report_Docs/StructuralTeamDiscussion.pdf`
- `Version10/data/output/PhaseP2610B1_population_generalization/detail/B32 - Copy.png`
- `Version10/data/output/PhaseP2610B1_population_generalization/detail/B33 - Copy.png`
- this freeze document (`Version10/V10_FREEZE_MANIFEST.md`)
- the new `Version11/` tree

`git diff` against HEAD for Version10 production Python, runners, webapp services, hybrid packages, prompts, Excel generators, and deployment overlays: **empty**.

Freeze is **not ambiguous**. Untracked files are report/docs copies and accidental PNG duplicates, plus the V11.0 documentation/tree created by this phase.

---

## Production release

| Field | Value |
|---|---|
| `APP_RELEASE` | `W.19.1` (`Version10/webapp/config.py`) |
| `ENGINE_LABEL` | `Version10` |
| `ENGINE_DISPLAY` | `Version10 production pipeline` |
| Web entry | `Version10/webapp/wsgi.py` → Flask `app:app` |
| Live deployment | Lightsail Gunicorn `wsgi:app` bind `127.0.0.1:8001`, 1 worker, overlay root `Version10/` |
| Public path | Nginx → `http://13.127.104.99/` |
| Live hybrid | `HYBRID_MODE=production` via **server environment overlay** (systemd unit default `HYBRID_MODE=off` is stale relative to live overlay) |

Engineering `MODEL_VERSION` is **not a single global constant**. Stage packages keep their own versions. Production hybrid authority (`PhaseW6`) uses `MODEL_VERSION = "10.0.0"`. The latest recorded GT hybrid accuracy snapshot uses report `model_version = "10.11.24"` (P2.6.10-E.3). VB.1 Excel builder still labels `6.6.0` / `7.8.0` internally. Do not collapse these into one number.

---

## Production pipeline (14 stages)

Authoritative list: `Version10/webapp/config.py` `PRODUCTION_STAGES`.

1. VROOT1 — `Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py`
2. R1 — `Run_PY/run_phase_r1_generalized_reinforcement_discovery.py`
3. T1 — `Run_PY/run_phase_t1_geometric_stirrup_evidence.py`
4. R2A — `Run_PY/run_phase_r2a_engineering_context.py`
5. R21B — `Run_PY/run_phase_r21b_semantic_interpreter.py`
6. R21C — `Run_PY/run_phase_r21c_engineering_fact_normalization.py`
7. R21D — `Run_PY/run_phase_r21d_evidence_hypothesis_engine.py`
8. L22 — `Run_PY/run_phase_l2_2_geometry_recovery.py`
9. R3 — `Run_PY/run_phase_r3_geometry_context_engine.py`
10. R31 — `Run_PY/run_phase_r31_engineering_relationship_engine.py`
11. R12A — `Run_PY/run_phase_r12a_geometry_accuracy.py`
12. R13 — `Run_PY/run_phase_r13_pipeline_integration.py`
13. HYBRID / W.6 — `Run_PY/run_phase_w6_hybrid_production_authority.py`
14. VB1 — `Run_PY/run_phase_vb1_production_output_completion.py`

Live architecture:

DXF Upload → VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → HYBRID / W.6 → VB1 → Steel Quantity → BBS → `Estimation_Output.xlsx`

---

## Production output contract

- Canonical Excel: `data/output/Production_Output/Estimation_Output.xlsx` (run-scoped under `data/web_runs/<run_id>/` for web jobs)
- Downloadable workbook name: `Estimation_Output_<run_id>.xlsx`
- Contents: Steel Quantity + BBS + project/engineering metadata (W.19.1 binding)
- W.6 may patch count / diameter / role only
- Deterministic engineering remains quantity authority (geometry, spacers/cover, lengths, DL, anchorage, hooks/bends, cut lengths, stirrup quantity, pieces, unit weight, steel kg, BBS, Excel)

---

## Important runtime configuration

- `STEEL_ENGINE_ROOT` = Version10 tree
- `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT` = web run staging
- `STEEL_WEB_PIPELINE_MODE` = `live` (production) or `stub` (W.2 tests)
- `HYBRID_MODE` = `production` on live overlay; `off` skips Vision
- YAML under `Version10/config/`
- Vision contracts/prompts inside C.5 / P.253 packages (not a separate top-level `prompts/` tree)
- GN discovery (production): uploaded run `general_notes/*.dxf`, then Version10 `beam_registry.json` pointer, then `Version10/data/Benchmark_Set_2/general_notes/`

---

## Critical production packages

Deterministic: VROOT.1, R.1, T.1, T.16, R.2A, R.2.1B–D, L.2.2, R3, R.3.1, R.1.2A, R.1.3, R.1.2B–D, piece generation, M.2 / V.9 spacer, SI.1 stirrup, VB.1, `src/config`, `src/llm`.

Hybrid / Vision (traced production path): W.5, W.6, W.8, W.10 (fail-safe monitor), W.11, P.253 client, C.5 call/prompt/contract, C.3 `encode_png`, D.1–D.4 production modules, E.1 `hybrid_runner_adapter`, E.2 `live_caller`, P.2610A/B/B2/C1C2 production modules, M.1 renderer, P.269 extractor (handoff), P.26 `role_family` (imported by P.269 `layer_role.py`).

See `PRODUCTION_TRUTH.md` and `V10_Organize/PRODUCTION_MODULE_INDEX.md`.

---

## Relevant tests

- `Version10/webapp/tests/test_w2_smoke.py`
- `Version10/webapp/tests/test_w16_metadata_aggregation.py`
- `Version10/webapp/tests/test_w191_excel_metadata_binding.py`
- `Version10/webapp/tests/test_w6_hybrid_authority.py`
- `Version10/src/PhaseW6_hybrid_production_authority/unit_tests.py`
- `Version10/src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py`

---

## Benchmark sets

Factory / GN path used by production: `Version10/data/Benchmark_Set_2/` (Galera GF framing + reinforcement DXFs, plus general notes DXF when present).

GT accuracy population for the latest in-repo hybrid report: Second–Sixth drawing sets vs estimator Excel (P2.6.10-E.3). First set excluded. Estimator ground-truth workbooks were **not** modified.

---

## Known accuracy baseline

Authoritative latest in-repo **live** GT snapshot:

`Version10/data/output/PhaseP2610E3_second_to_sixth_full_population_live_vision_hybrid_accuracy_benchmark/report_data.json`

- Phase `P2.6.10-E.3`, mode `LIVE_BENCHMARK`, decision `PASS_WITH_LIMITATIONS`, report `model_version` `10.11.24`
- This is **not** a production accuracy promotion
- Pooled: beam ID **85.12%** (515/605), bar ID **48.17%** (2008/4169), correct-of-detected **36.5%** (733/2008), diameter **77.84%** (1563/2008), steel/weight **60.64%** (90,305 kg vs 148,911 kg GT), overall **57.61%**
- Vision coverage: HYBRID 486 (91.7%), FALLBACK 44 (8.3%)
- Error taxonomy (pooled): MISSING 2161, WRONG_QUANTITY 593, WRONG_DIAMETER 445, EXTRA 183, WRONG_ROLE 134, PARTIAL_MATCH 103, ACCEPTABLE_EXTRA 89

A smaller published PDF fixture exists under `_report_fixture/` (offline/partial sample, overall 51.37% on 25 beams). That fixture is **not** the latest full-population live number. E.1/E.2 `accuracy_report_data.json` fixtures with values of `1` are stubs and must not be used.

---

## Known limitations

- Missing bars dominate quantity error (model under-counts kg)
- Ownership / matching / extra bars remain material
- Diameter mismatches remain material on detected bars
- Some GT beams are not detected (90 unmatched GT beams in the E.3 pool)
- Mixed packages still contain experimental orchestrators beside production modules
- Live systemd unit `HYBRID_MODE=off` is stale vs overlay `production`
- Version8 remains on Lightsail `:8000` unused (`ACTIVE_BUT_UNUSED`); archive is a separate hold

---

## Explicit freeze rule

**Version10 is the immutable demonstrated W.19.1 Hybrid baseline.**

Do not edit Version10 production Python, prompts, Vision contracts, hybrid logic, engineering rules, Excel generation, production configuration, systemd/nginx, `APP_RELEASE`, `PRODUCTION_STAGES`, or the live `:8001` deployment as part of Version11 development.

All accuracy work happens in `Version11/`.
