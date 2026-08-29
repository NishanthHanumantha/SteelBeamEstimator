# PHASE W.19.1 — EXCEL PROJECT METADATA BINDING HOTFIX

Date: 2026-08-29  
Public: `http://13.127.104.99/`  
Classification: **W19_1_EXCEL_METADATA_BINDING_PASS**

This hotfix binds already-resolved R.2A project engineering metadata into the VB.1 Excel Project Totals sheet. It does not change R.2A parsing, M.2, spacer, stirrup, longitudinal, B27 aggregation, frame discovery, hybrid logic, worker count, Anthropic version, or `HYBRID_MODE`.

---

## 1. Root cause

R.2A correctly writes resolved Cover / steel grade / Ld factor into run artefacts:

- `data/output/PhaseR.2A_engineering_context/engineering_context_summary.json`
- `data/output/PhaseR.2A_engineering_context/engineering_context.json`

VB.1 Excel generation did not consume those artefacts.

`EstimatorExcelGenerator._ws_project_totals` uses `loader_summary`. When that dict is missing or empty it prints exactly the W.19 production strings:

- Cover: `UNRESOLVED (IS456 fallback 40 mm)`
- Development Length: `UNRESOLVED (IS456 fallback Fe415, ~40d)`

`PhaseVB1Orchestrator._step_excel_generation` previously did:

```python
loader_summary = self._loader.summary() if self._loader else None
```

`self._loader` is `None` on the production path because VB.1’s in-process R.2A bootstrap fails silently (`_R2A_AVAILABLE = False`). The bootstrap resolves `PhaseR.2A_engineering_context` as `Version10/PhaseR.2A_engineering_context` (two parents up from `src/PhaseVB.1_...`), which does not exist. The real package lives at `Version10/src/PhaseR.2A_engineering_context`. The first load (`__init__.py`) raises `FileNotFoundError`; the exception is swallowed.

The R.2A **stage** still runs as its own process and writes artefacts. Those values were present at the VB.1 boundary and unused. This is **present but not passed**, not a GN parse failure.

W.19.1 does **not** repair the bootstrap path (that would re-parse GN inside VB.1). It maps the already-written artefacts into the existing `loader_summary` keys Excel already understands.

---

## 2. Exact file / function changed

| File | Change |
| --- | --- |
| `Version10/src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py` | Capture `_R2A_BOOTSTRAP_ERROR`. Add `loader_summary_from_r2a_artefacts()`. `_step_excel_generation` prefers artefact summary for Excel only. |
| `Version10/webapp/config.py` | `APP_RELEASE = "W.19.1"` |
| `Version10/webapp/routes.py` | `/health` `phase` = `W.19.1` |
| `Version10/webapp/tests/test_w191_excel_metadata_binding.py` | New focused binding tests |
| `Version10/webapp/tests/test_w5_hybrid_shadow.py` (and W.6 / W.12 / W.13 / W.14 phase assertions) | Expect `W.19.1` |
| `Version10/webapp/deployment/pack_w191.py` | Narrow hotfix tarball |
| `Version10/webapp/deployment/_w191_deploy.sh` | Overlay + import check (`loader_summary_from_r2a_artefacts`, `spacer_quantity(1040)==2`) |

Not modified: R.2A parsers, `spacer_engine.py`, stirrup/longitudinal/hybrid, steel-weight `_loader`, Excel generator fallback branches.

---

## 3. Data path before fix

```
R.2A stage → engineering_context_summary.json (cover_beam_mm=30, Fe550, 50d)
                ↓
            unused by VB.1 Excel
                ↓
PhaseVB1Orchestrator._step_excel_generation
    _loader is None → loader_summary = None
                ↓
EstimatorExcelGenerator._ws_project_totals
    empty ls → UNRESOLVED (IS456 fallback 40 mm / Fe415 ~40d)
```

---

## 4. Data path after fix

```
R.2A stage → engineering_context_summary.json
          → engineering_context.json (cover_rules.source, development_length_table)
                ↓
loader_summary_from_r2a_artefacts(output_dir)
    cover_beam_mm, cover_source
    primary_steel_grade, dev_length_factor (from dev_length_factor_d)
    dev_length_source = GN_DXF_TABLE_1 when table present
                ↓
EstimatorExcelGenerator(loader_summary=artefact_summary)
                ↓
Project Totals Cover = 30 (unit mm)
Project Totals Development Length = GN table (Fe550, ~50d)
```

If artefacts are missing, `loader_summary` stays `None` and the existing UNRESOLVED / IS456 fallback remains.

Key mapping (canonical R.2A names → existing Excel `loader_summary` keys):

| R.2A artefact | Excel loader_summary |
| --- | --- |
| `cover_beam_mm` | `cover_beam_mm` |
| cover rule `source` (BEAM row) | `cover_source` |
| `primary_steel_grade` | `primary_steel_grade` |
| `dev_length_factor_d` | `dev_length_factor` |
| `development_length_table` present | `dev_length_source` = `GN_DXF_TABLE_1` |
| `steel_density_kg_m3` | `steel_density` |

No second metadata representation. No project-specific `if Galera` / `if Inizio` branches. No Ld recalculation inside Excel.

---

## 5. Galera local result

Focused binding check (production W.19 Galera R.2A JSON from run `20260829_070104_a2dda3ed`, not a 143-beam Inizio replay):

- Mapped Cover **30**, Fe550, 50d, sources `GN_DXF_TABLE_2` / `GN_DXF_TABLE_1`
- Generated Excel: Cover **30**, Development Length **`GN table (Fe550, ~50d)`**, five sheets

Unit tests in `test_w191_excel_metadata_binding.py` reproduce the same mapping with synthetic artefacts and keep UNRESOLVED when artefacts are absent.

---

## 6. Production result

Galera GF run **`20260829_103409_0a2925ba`**

- URL: http://13.127.104.99/?run=20260829_103409_0a2925ba
- Inputs: same W.14 Galera DXFs as W.19 (`Galera_GF_BeamReinforcementDetails.dxf`, not SpreadOut)
- Duration: **1365.62 s** (~22.8 min); 65 beams; `HYBRID_SUCCESS`; 64/64 Claude
- Workbook: `Estimation_Output_20260829_103409_0a2925ba.xlsx` (44,606 bytes, PK/zip/openpyxl OK, downloaded twice)
- Five sheets: Beam Summary, Bar Bending Schedule, Steel Summary, Diameter Summary, Project Totals
- Frame: **GF** on inspected BBS rows
- Steel: 11,549.917 kg (65 beams, 330 bars)
- W.18B spacers unchanged vs W.19: B10 Ø25 qty **4** cut 0.54 m; B1 Ø25 qty **5** cut 0.14 m (full-span extra on this DXF); B23 no spacer row
- M.2: `cover_mm_used=30.0`, `extent_fallback_rows=0`, MODEL_VERSION `9.2.0`

Overlay:

- Backup: `/opt/steel-beam-estimation/backups/w191_predeploy_20260829T103314Z`
- Health after restart and after the run: `status=ok`, `phase=W.19.1`, `app_release=W.19.1`, `busy=false`
- `HYBRID_MODE=production`, 1 Gunicorn worker, Anthropic `0.125.0`
- Deploy import check: `IMPORT_OK`

R.2A on this run: `cover_beam_mm=30`, Fe550, `dev_length_factor_d=50`, TABLE 2 source, Ld table present.

Note: `gn_dxf` in the artefact still points at Version8 `Benchmark_Set_2/general_notes/...` rather than the uploaded run GN. That is the existing Inizio Fe550/Fe415 discovery issue. Not changed in W.19.1.

---

## 7. Cover result

| Surface | Cover |
| --- | --- |
| Production R.2A | **30 mm** (TABLE 2) |
| Production Excel Project Totals | **30** (unit mm) |
| W.19 Excel (before hotfix) | `UNRESOLVED (IS456 fallback 40 mm)` |

Missing-artefact unit test still prints `UNRESOLVED (IS456 fallback …)`.

---

## 8. Development Length result

| Surface | Development Length |
| --- | --- |
| Production R.2A | Fe550, factor 50d, Ld table present |
| Production Excel Project Totals | **`GN table (Fe550, ~50d)`** |
| W.19 Excel (before hotfix) | `UNRESOLVED (IS456 fallback Fe415, ~40d)` |

Excel did not independently calculate 40d / 38d / 50d. It displayed the R.2A artefact summary.

---

## 9. W.16 test result

```
python -m unittest Version10.webapp.tests.test_w16_metadata_aggregation
python -m unittest Version10.webapp.tests.test_w191_excel_metadata_binding
```

**20 OK** (16 W.16 + 4 W.19.1).

---

## 10. W.18B test result

```
pytest Version10/src/PhaseV9_spacer_rule/tests/test_spacer_engine.py
pytest Version10/src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py
```

**30 passed**. Spacer engine not in the overlay.

---

## 11. Production mutation

Narrow overlay of 9 files from `pack_w191.py` (orchestrator, release label, W.19.1 tests). Not a `git pull`. Server git HEAD remains historical.

Preserved: `HYBRID_MODE=production`, `--workers 1`, Anthropic `0.125.0`.

---

## 12. Commit hash

`ad3dbaf5dfb88c45b855eeeb630bf614171c5d4d`

`W19.1 bind R2A project metadata into Excel Project Totals`

---

## 13. Remaining Inizio Fe550 / Fe415 discrepancy

**Not fixed in W.19.1.** Production Inizio R.2A still reports Fe550 / 50d; W.16 expected/replayed Fe415 / ~38d. That is a GN discovery / parse issue. Excel now displays whatever the current R.2A artefacts say. Do not change R.2A interpretation to match the historical W.16 Excel expectation.

---

## Acceptance checklist

- [x] R.2A metadata confirmed available in artefacts
- [x] Excel consumes resolved metadata
- [x] Galera production Excel Cover = 30 mm
- [x] Galera production Excel Development Length is GN-derived (`GN table (Fe550, ~50d)`)
- [x] No hardcoded project-specific Cover/Ld
- [x] Missing metadata still UNRESOLVED / IS456 fallback
- [x] W.16 tests pass (16 OK)
- [x] W.18B tests pass (30 passed)
- [x] Spacer behavior unchanged vs W.19 on this DXF
- [x] No unrelated calculation files changed
- [x] Production health remains OK
- [x] Production representative workbook downloads successfully
- [x] Five expected sheets remain present
