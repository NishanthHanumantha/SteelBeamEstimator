# PHASE W.16 — PROJECT METADATA + AGGREGATION INTEGRITY RECOVERY

Date: 2026-08-28  
Classification: **W16_PASS_WITH_LIMITATIONS**  
Recommendation: **READY FOR ESTIMATOR VALIDATION**  
Steel totals label: **PIPELINE_CORRECTED_NOT_ESTIMATOR_ACCEPTED**  
Production mutated: **NO**

Inspected production workbooks (pre-correction):

- Galera GF: `Version10/Downloaded_Output/2ndSet_Estimation_Output_20260828_053831_d9520a43.xlsx`
- Inizio 11-18F: `Version10/Downloaded_Output/6thSet_Estimation_Output_20260827_110320_4e330c37.xlsx` (run `20260827_110320_4e330c37`)

Replay workbooks (VB.1 on cached L.2 + parsed GN DXFs, Vision not re-run):

- `Version10/Downloaded_Output/W16_Galera_GF_Estimation_Output.xlsx`
- `Version10/Downloaded_Output/W16_Inizio_11-18F_Estimation_Output.xlsx`

Investigation: `Version10/webapp/deployment/W16_INVESTIGATION.md`

---

## 1. Scope

Exactly three issues:

A. Project-specific General Notes metadata: Development Length and Cover.  
B. Beam-weight aggregation integrity, specifically Inizio B27 (~42,173 kg).  
C. Drawing-specific Frame/Floor identifier (Galera → GF, Inizio → 11-18F; TF must not be universal).

Out of scope: remaining bar-role / quantity estimation inaccuracies.

---

## 2. Root Cause A — General Notes

Development Length is a **TABLE 1 rule grid** (steel grade × diameter × concrete), not a single scalar. Excel Project Totals shows a representative Ld/d for dia=12. Cover is TABLE 2 beam-in-superstructure.

### Cover

| Stage | Finding |
| --- | --- |
| DXF SOURCE | GN TABLE 2 title `TABLE 2` + row `BEAM IN SUPERSTRUCTURE`. Galera: cover **30 mm**, M30, Fe550 at (~1612, ~615). Inizio: cover **30 mm** (TOP/BOTTOM 30); no Fe/M grade on that row. |
| RAW EXTRACTION | `CoverParser.parse()` → `CoverRule.cover_mm`. |
| NORMALIZED VALUE | `EngineeringContextLoader.get_cover("BEAM")` → `cover_beam_mm`. |
| FALLBACK | IS 456 / parser fallback 30 mm beam, labelled `FALLBACK_IS456` / `UNRESOLVED` in Excel when GN is not loaded. |
| CALCULATION CONSUMERS | `SteelWeightCompletion._cover_mm()` (spacers, stirrup perimeter). |
| EXCEL OUTPUT SOURCE | `estimator_excel_generator._ws_project_totals` from `loader_summary`. |
| PREVIOUS BEHAVIOR | Loader often `None` because factory ignored `STEEL_RUN_ROOT/general_notes`. Excel then printed **Cover = 40** and labelled it as if GN were present. `find_anchor(r"TABLE\s+2")` also matched notes *mentioning* TABLE 2, so Galera TABLE 2 itself was missed. |
| CORRECTED BEHAVIOR | Discover run-scoped GN first. Bind TABLE 2 to the short title `TABLE 2`. Galera Cover **30 mm** / `GN_DXF_TABLE_2`. Inizio Cover **30 mm** / `GN_DXF_TABLE_2`. |
| CALCULATION IMPACT | Cover 30 mm (not 40) enters stirrup/spacer geometry when the loader is present. |
| EXCEL IMPACT | Numeric 30 mm when sourced from TABLE 2; `UNRESOLVED (IS456 fallback …)` when not. |

### Development Length

| Stage | Finding |
| --- | --- |
| DXF SOURCE | `LD FOR FY-415/500/550` tables (TABLE 1). |
| RAW / NORMALIZED | `development_length_table[(steel, dia, conc)]`; `get_development_length_factor()` = Ld/d at dia=12. |
| FALLBACK | Factor 40 × diameter, labelled UNRESOLVED when the table is not loaded. |
| CALCULATION CONSUMERS | `SteelWeightCompletion._development_length_mm()` for longitudinal cut = span + 2×Ld. |
| PREVIOUS BEHAVIOR | Empty loader → Excel `GN table (Fe415, ~40d)` even though no table was used. Ld parser also scanned only Galera X=1540–1680, missing Inizio headers at x≈1508. |
| CORRECTED BEHAVIOR | Galera: **Fe550, ~50d** from TABLE 1. Inizio: **Fe415, ~38d** from TABLE 1 (TABLE 2 beam row has no steel grade; primary grade is the first LD header). |
| CALCULATION IMPACT | Cut lengths use the project table (or IS 456 computed entries), not a silent universal 40d, when the loader is present. |
| EXCEL IMPACT | `GN table (Fe550, ~50d)` / `GN table (Fe415, ~38d)` when sourced; UNRESOLVED when not. |

Precedence:

1. Run-scoped uploaded GN DXF (`STEEL_RUN_ROOT/general_notes`)
2. `beam_registry.json` pointer
3. Parsed TABLE 1 / TABLE 2
4. Documented IS 456 fallback, labelled UNRESOLVED

---

## 3. Root Cause B — B27

### Origin of ~42,173 kg

L.2 records for B27 extra-top bars:

- `bar_label = "2-Y252-Y25"`
- `diameter_mm = 252`
- quantity = 2, span = 6.55 m

Hyphen/space stripping plus `Y(\d+)` produced **252**. 252 is not an IS column size. Ld = 40 × 252 mm = 20.16 m, cut = 26.71 m, weight **20,915.324 kg each**. Two such BBS rows:

`2 × 20,915.324 + 342.605 = 42,173.253 kg`

Steel Summary Y8–Y32 omitted 252 kg, so visible diameter subtotal stayed 342.605 while `total_weight_kg` included the 252 mm bars.

Same class, smaller: B137 `2-Y28` / dia 28 (no Y28 column) contributed **47.222 kg** to the beam total only. After W.16 that bar is skipped with an explicit `[VB.1] SKIP unsupported diameter` diagnostic (not mapped to Y25).

### Why previous logic allowed it

Unsupported diameters were treated as real φ for Ld, cut, and beam total. Diameter columns only emit Y8–Y32. No beam-total vs diameter-subtotal invariant.

### Corrected aggregation

252 → longest supported prefix **25**. Extra-top groups recomputed as 2-Y25 using the Inizio GN Ld table (not 40d). Beam total = sum of supported diameter weights. Workbook validator fails diagnosably on mismatch (does not overwrite cells).

Replay of Inizio cached L.2 + parsed Inizio GN (Fe415 table, cover 30 mm):

| Field | kg |
| --- | ---: |
| PREVIOUS_B27_TOTAL | 42173.254 |
| PREVIOUS_DIAMETER_SUBTOTAL | 342.605 |
| PREVIOUS_DIFFERENCE | 41830.649 |
| CORRECTED_B27_TOTAL | 468.551 |
| CORRECTED_DIAMETER_SUBTOTAL | 468.551 |
| CORRECTED_DIFFERENCE | 0.000 |

342.605 is **not** the repaired total: it omitted the extra-top groups. Those groups are real 2-Y25 after parse repair. GN Ld/cover also slightly changes the previously valid Y12/Y16/Y20/Y25 rows, so corrected B27 is not `342.605 + 2×40d Y25`.

Corrected extra-top contributions in the replay: **65.122 kg + 65.122 kg** (Y25).

Inizio project steel: **67,506.849 kg → 25,386.482 kg** (PIPELINE_CORRECTED_NOT_ESTIMATOR_ACCEPTED). Every Steel Summary beam in the replay workbook reconciles; project total = sum of beam totals = sum of diameter totals.

---

## 4. Root Cause C — Frame

| Item | Finding |
| --- | --- |
| Previous TF source | Hardcoded `_FRAME_TYPE = "TF"` in `bbs_completion_engine.py` and SI.1 `frame_type="TF"`. **TF = Typical Floor**, a real 3rd-set Galera identifier, reused as a universal BBS default. |
| Galera authoritative source | Drawing filenames `Galera_GF_FramingPlan.dxf` / `Galera_GF_BeamReinforcementDetails*.dxf`. Token **GF** (underscore-delimited; `\bGF\b` misses `_GF_`). → **GF**. Not a Galera hardcode. |
| Inizio authoritative source | `11-18TH_FLOOR.dxf_FRAMINIG.dxf` and `(11-18)` / `11-18` range **before** TYPICAL FLOOR. → **11-18F**. |
| Normalized path | `project_discovery._infer_floor()` → `project_manifest.floor` → `PhaseVB1Orchestrator._resolve_frame_identifier()` → `BBSCompletionEngine(frame_type=…)` → every BBS row (SI.1 rows overwritten). |
| Unresolved | Empty / `UNKNOWN_FLOOR` → BBS **UNRESOLVED**, never silent TF. |

W.15 manifests stored `floor=UNKNOWN_FLOOR` because the old patterns missed `_GF_` and range-before-TF. New discovery plus VB.1 filename fallback on `run_root` resolve GF / 11-18F on new runs and on VB.1 replay of existing staging dirs.

---

## 5. Test Results

`python -m unittest Version10.webapp.tests.test_w16_metadata_aggregation Version10.webapp.tests.test_w14_hybrid_recovery -v`

| Suite | Result |
| --- | --- |
| W.16 metadata / frame / B27 / live GN | **16 passed** (14 always-on + 2 live GN when DXFs are staged under `%TEMP%\w16_gn`) |
| W.14 hybrid recovery | **3 passed** |
| **Total** | **19 passed, 0 failed** |

---

## 6. Regression Results

W.14 provider classification, download path, and health-phase tests passed. Hybrid routing, Anthropic version, and worker count were not changed. W.15 large-scale Vision behavior was not re-executed; VB.1 was replayed on the W.15 Inizio L.2 and the W.14/W.16 Galera L.2.

---

## 7. Production Mutation

**production mutated = NO**

Repo corrections are local only. Public production remains frozen at phase W.14, `HYBRID_MODE=production`, 1 worker, Anthropic 0.125.0. Estimator-facing workbooks on Lightsail will not change until a later deploy.

---

## 8. Final Classification

**W16_PASS_WITH_LIMITATIONS**

**READY_FOR_ESTIMATOR_VALIDATION**

Justification: the three inspection blockers are corrected upstream and demonstrated on the actual project GN DXFs and cached L.2 models. Limitations (not hidden):

1. Production is not deployed; live downloads still show TF / Cover 40 / B27 42,173 kg.
2. B137 `2-Y28` is excluded from totals (no Y28 column); skip is logged, not silently stuffed into Y25.
3. Inizio TABLE 2 beam row has no steel/concrete grade; Fe415 comes from the first LD table header.
4. Fresh workbooks are VB.1 replays of cached L.2, not a new 143-beam Vision run.
5. Remaining bar-specific estimation issues are explicitly out of scope.
6. Corrected project totals are **PIPELINE_CORRECTED_NOT_ESTIMATOR_ACCEPTED**.
