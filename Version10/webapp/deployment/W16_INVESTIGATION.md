# W.16 Investigation (read-only)

Date: 2026-08-28  
Datasets: Galera GF workbook `2ndSet_Estimation_Output_20260828_053831_d9520a43.xlsx`; Inizio 143-beam workbook `6thSet_Estimation_Output_20260827_110320_4e330c37.xlsx`.

No production logic was changed before this note.

---

## A. Cover / Development Length

Issue class: **mixed — discovery/propagation + Excel presentation** (not an Excel-only cell patch).

### Source map — COVER

| Stage | Finding |
| --- | --- |
| DXF SOURCE | General Notes TABLE 2 (`CLEAR COVER` / `BEAM IN SUPERSTRUCTURE`). Parser: `PhaseR.2A_engineering_context/cover_parser.py`. |
| RAW EXTRACTION | `CoverParser.parse()` → `CoverRule.cover_mm`. Spatial window is **absolute Galera coordinates** (`x=1540–1680`). |
| NORMALIZED VALUE | `EngineeringContextLoader.get_cover("BEAM")` → `cover_beam_mm` in `loader.summary()`. |
| FALLBACK | If no matching rule: `fallback_cover_mm` or IS 456 **40 mm**. Cover-parser table-miss fallback rules use **30 mm** for beams. |
| CALCULATION CONSUMERS | `SteelWeightCompletion._cover_mm()` (spacers, stirrup perimeter). |
| EXCEL OUTPUT SOURCE | `estimator_excel_generator._ws_project_totals`: `ls.get("cover_beam_mm", 40)`. |
| CURRENT ROOT CAUSE | Both inspected workbooks show **Cover = 40** and **Fe415 ~40d**. That pair is the **loader-absent Excel default**, not TABLE 2. `EngineeringContextFactory._discover_gn_path()` looks at engine-root `beam_registry.json` and `data/Benchmark_Set_2/general_notes` (empty in Version10). It does **not** read `STEEL_RUN_ROOT/general_notes/*.dxf`. Webapp writes a GN pointer, but VB.1 re-discovers via this factory; when discovery fails, `_loader` is None and Excel silently prints 40 / Fe415 / 40d. |

### Source map — DEVELOPMENT LENGTH

| Stage | Finding |
| --- | --- |
| DXF SOURCE | GN TABLE 1 Ld grid (grade × diameter × concrete). Parser: `development_length_parser.py`. This is a **table/rule**, not a single scalar. |
| RAW / NORMALIZED | `development_length_table[(steel, dia, conc)]`; `get_development_length_factor()` is Ld/d for a representative dia=12. |
| FALLBACK | Factor 40 × diameter (IS 456). |
| CALCULATION CONSUMERS | `SteelWeightCompletion._development_length_mm()` for longitudinal cut = span + 2×Ld. |
| EXCEL | `f"GN table ({sg}, ~{dl_factor}d)"` with defaults `sg=Fe415`, `dl_factor=40` when `loader_summary` is empty. The label says “GN table” even when no GN was loaded. |
| CURRENT ROOT CAUSE | Same as Cover: missing run-scoped GN discovery + silent Excel defaults. Display incorrectly implies a parsed GN table. |

Precedence to implement:

1. Run-scoped uploaded General Notes DXF (`STEEL_RUN_ROOT/general_notes`)
2. Existing `beam_registry.json` `general_notes_dxf` pointer
3. Parsed TABLE 1 / TABLE 2 values
4. Documented IS 456 fallback, **labelled UNRESOLVED** in Project Totals

---

## B. B27 aggregation (~42,173 kg)

Issue class: **mixed — incorrect numeric diameter + aggregation that does not reconcile**

### Observed workbook facts (Inizio B27)

| Item | Value |
| --- | ---: |
| PREVIOUS_B27_TOTAL | 42173.254 kg |
| PREVIOUS_DIAMETER_SUBTOTAL (Y12+Y16+Y20+Y25) | 342.605 kg |
| PREVIOUS_DIFFERENCE | 41830.649 kg |
| Two BBS “Top bars - Extra” rows | **20915.324 kg each** |

Those two rows: **Dia = 252 mm**, qty = 2, Dvlp.L = 20.16 m (= 2 × 40 × 252 / 1000), Cut = 26.71 m (= 6.55 + 20.16). Formula is internally consistent **for a 252 mm bar**. 252 is not an IS bar size.

Steel Summary diameter columns only emit Y8–Y32, so 252 kg is **omitted from diameter cells** but **included in `BeamSteelWeight.total_weight_kg`**. Hence beam total ≠ visible diameter subtotal.

`2 * 20915.324 + 342.605 = 42173.253` — the entire anomaly is those two records.

252 is the digit string **Y25 + trailing 2** after hyphen/space stripping (`normalize_spec` / `Y(\d+)` on `Y252`), or an unvalidated diameter flowing into VB.1. It is **not** `str(2)+str(25)` (=225). Longest supported prefix of 252 is **25**.

342.605 is the sum of the **valid** Y12/Y16/Y20/Y25 rows already on B27. It is **not** the correct beam total if the extra-top bars are real 2-Y25 bars. Repairing 252 → 25 recomputes those two groups at Y25 + 40d and **adds** that weight to Y25. Dropping the rows would under-count extra top steel.

Proposed aggregation invariants (fail diagnosably):

- per beam: `total_weight_kg == sum(weight_by_diameter for supported dias)`
- per project: `project_total == sum(beam totals) == sum(diameter totals)`
- unsupported diameters must not enter `total_weight_kg` silently

---

## C. Frame = TF

Issue class: **Excel presentation of a hardcoded constant** (VROOT.1 already discovers floor; BBS ignores it)

| Item | Finding |
| --- | --- |
| Previous TF source | `PhaseVB.1_production_output_completion/bbs_completion_engine.py` `_FRAME_TYPE = "TF"` and SI.1 `frame_type="TF"`. **TF = Typical Floor**, a real Galera 3rd-set identifier (`Galera_TF_FramingPlan.dxf`), reused as a universal BBS default. |
| VROOT.1 | `project_discovery._infer_floor()` already maps `\bGF\b` / GROUND FLOOR → **GF**. It does **not** emit `11-18F` (pattern `\d+TH FL` captures **18** only; `TYPICAL FLOOR` is not ordered vs ranges). Result is stored as `project_manifest.floor` and **never passed to BBS**. |
| Galera authoritative source | Drawing/file identity already used by VROOT.1: `Galera_GF_FramingPlan.dxf` / `Galera_GF_BeamReinforcementDetails.dxf` → **GF**. Not a Galera hardcode. |
| Inizio authoritative source | Framing `11-18TH FLOOR…` and reinforcement `(11-18)` → **11-18F**. Must match range **before** TYPICAL FLOOR → TF. |
| Unresolved | Must not silently print TF. Use documented UNRESOLVED (or legitimate TF only when typical-floor evidence exists, e.g. 3rd Set). |

---

## Proposed minimal files

| File | Change |
| --- | --- |
| `engineering_context_factory.py` | Discover GN under `STEEL_RUN_ROOT/general_notes` first |
| `cover_parser.py` | TABLE 2 region relative to the TABLE 2 anchor (keep old bounds as fallback) |
| `engineering_context_loader.py` | `cover_source` / `dev_length_source` on `summary()` |
| `estimator_excel_generator.py` | Project Totals show resolved GN values or labelled fallback |
| `steel_weight_completion.py` | Canonicalize unsupported diameters; reconcile beam/project totals |
| `bbs_completion_engine.py` + SI.1 | `frame_type` from resolved identifier |
| `phase_vb1_orchestrator.py` | Load `project_manifest.floor`; pass frame into BBS |
| `project_discovery.py` | Floor-range `11-18F` before TF / single-floor patterns |
| `workbook_validator.py` | Beam vs diameter vs project reconciliation |
| `normalize.py` (`parse_diameter`) | Do not accept Y252 as diameter 252 |

Out of scope: remaining bar-role / qty inaccuracies unrelated to B27 252 / metadata / frame.

Implementation (2026-08-28): the files above were changed as proposed. Live parse of production GN DXFs and VB.1 replay of cached L.2 confirmed Galera Cover 30 / Fe550 ~50d / Frame GF and Inizio Cover 30 / Fe415 ~38d / Frame 11-18F / B27 468.551 kg. See `PHASE_W16_METADATA_AND_AGGREGATION_REPORT.md`.


---

## Explicit statement per issue

| Issue | Extraction | Normalization | Propagation | Calculation | Aggregation | Excel presentation |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| A Cover / Ld | GN parsers exist; run GN often never reached | IS 456 40 defaults | loader_summary empty | Ld/cover used only if loader present | — | Silent 40 / “GN table Fe415 ~40d” |
| B B27 | Possible bad dia parse | 252 treated as real dia | — | 40d × 252 mm | total includes unsupported dia; columns do not | Shows both 42173 and 342.605 |
| C Frame | VROOT.1 floor exists | Range 11-18 missing | floor not passed to BBS | — | — | Hardcoded TF |
