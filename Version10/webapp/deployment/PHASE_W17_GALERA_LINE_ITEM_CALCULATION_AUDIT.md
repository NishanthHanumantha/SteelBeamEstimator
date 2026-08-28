# PHASE W.17 — GALERA GF LINE-ITEM CALCULATION TRACE & ENGINEERING AUDIT

Date: 2026-08-28

## 1. Scope

Dataset:
2nd Set — Galera GF

Beams:
B1
B10
B23

Phase type:
READ-ONLY CALCULATION AUDIT

Production mutation:
NO

Workbook used:
`Version10/Downloaded_Output/W16_Galera_GF_Estimation_Output.xlsx` (W.16 VB.1 replay of cached L.2 + Galera GN)

L.2 used:
production `beam_reinforcement_models_production.json` for run `20260828_053831_d9520a43`

No calculation logic was changed in W.17.

---

## 2. Project Engineering Context

- Frame = **GF** (drawing filename token; BBS column)
- Cover = **30 mm**
- Cover source = **GN_DXF_TABLE_2** (Galera General Notes TABLE 2, BEAM IN SUPERSTRUCTURE)
- Steel grade = **Fe550**
- Concrete grade = **M30** (from TABLE 2 beam row)
- Development Length table source = **GN_DXF_TABLE_1** (Galera TABLE 1)
- 135° stirrup hook multiple from GN = **5** (`get_hook_multiple(135)` → 5d, not the IS 10d fallback)
- Representative Excel Project Totals display = `GN table (Fe550, ~50d)` which is Ld/d at **dia=12 only**
- Per-bar Ld actually used (Fe550, M30, TABLE 1 hit on every audited diameter):

| Diameter | Ld (mm) | Ld (m) | Ld/d | Table hit |
| ---: | ---: | ---: | ---: | :---: |
| Y8 | 400 | 0.4 | 50.0 | True |
| Y10 | 500 | 0.5 | 50.0 | True |
| Y16 | 800 | 0.8 | 50.0 | True |
| Y20 | 1000 | 1.0 | 50.0 | True |
| Y25 | 1250 | 1.25 | 50.0 | True |

On this Galera table the ratio is 50d for Y8, Y10, Y16, Y20, Y25. That is a table result, not a hardcoded 50.

Density: 7850 kg/m³ (`get_steel_density`).

---

## 3. Pipeline Calculation Map

```
Drawing evidence (framing DXF + reinforcement DXF + GN DXF)
    -> PhaseR1_2A GeometryProvider  (clear_span_mm, width_mm, depth_mm)
    -> PhaseR1.3 EngineeringBarBuilder  (L.2 bar records: label, dia, qty, optional cut_length_mm)
    -> SteelWeightCompletion._compute_beam / _compute_bar / _derive_cut_length
         STIRRUP branch -> StirrupImprover.compute_beam (loader-aware)
    -> BBSCompletionEngine.generate
         STIRRUP branch -> StirrupImprover() module singleton **without loader** (re-entry)
    -> EstimatorExcelGenerator  (Bar Bending Schedule, Steel Summary)
```

Module paths (Version10):

| Stage | Class / function |
| --- | --- |
| Geometry | `PhaseR1_2A_geometry_accuracy/geometry_provider.py` `GeometryProvider` |
| L.2 bars | `PhaseR1.3_pipeline_integration/engineering_bar_builder.py` |
| Cover / Ld / hook | `PhaseR.2A_engineering_context/engineering_context_loader.py` |
| Weight / cut | `PhaseVB.1_production_output_completion/steel_weight_completion.py` |
| Stirrup zones / qty / cut | `PhaseSI.1_stirrup_improvement` `StirrupImprover`, `StirrupQuantityEngine`, `StirrupWeightEngine` |
| BBS rows | `bbs_completion_engine.py` `BBSCompletionEngine.generate` |
| Excel | `estimator_excel_generator.py` |

Beam header row is **not** a bar calculation: Dia=1, Spacing=span_m, No. of Bars=width_mm, Dvlp.L=depth_m.

---
## 4. Beam B1

Section 200 × 750 mm. `clear_span_mm` = 4158.3 (`geometry_source` = BEAM_REGISTRY, confidence = 0.55). Emitted roles: ['SPACER', 'STIRRUP', 'TOP_EXTRA', 'TOP_MAIN']. No BOTTOM_MAIN, BOTTOM_EXTRA, or SFR rows on this beam.

### B1 — Line 1

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
2

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `2-Y16`
- L.2 key / bar_id: `top_main_bars` / `R13-B1-TOP_EXTRA-ac9cd9`
- L.2 quantity: 2 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 5918.3 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 4158.3,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 5918.3
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 5758.3
expected_from_formula_mm = 5758.3

Result:
5.758 m  (5758.3 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
2

Cut Length:
5.758 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
2 × 5.758300 = 11.516600

Result:
11.517 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
11.516600 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*5758*2*7850/1e9`)

Calculation:
recomputed = 18.177066 kg
engine = 18.177066 kg

Result:
Excel Total kg = 18.177
Excel diameter-column kg = 18.177

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 — Line 2

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
2

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `2-Y16`
- L.2 key / bar_id: `top_main_bars` / `R13-B1-TOP_EXTRA-6b9a58`
- L.2 quantity: 2 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2799.6 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 4158.3,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 2799.6
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 5758.3
expected_from_formula_mm = 5758.3

Result:
5.758 m  (5758.3 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
2

Cut Length:
5.758 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
2 × 5.758300 = 11.516600

Result:
11.517 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
11.516600 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*5758*2*7850/1e9`)

Calculation:
recomputed = 18.177066 kg
engine = 18.177066 kg

Result:
Excel Total kg = 18.177
Excel diameter-column kg = 18.177

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 — Line 3

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
2

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `2-Y16`
- L.2 key / bar_id: `top_main_bars` / `R13-B1-TOP_EXTRA-c049cb`
- L.2 quantity: 2 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2799.6 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 4158.3,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 2799.6
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 5758.3
expected_from_formula_mm = 5758.3

Result:
5.758 m  (5758.3 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
2

Cut Length:
5.758 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
2 × 5.758300 = 11.516600

Result:
11.517 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
11.516600 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*5758*2*7850/1e9`)

Calculation:
recomputed = 18.177066 kg
engine = 18.177066 kg

Result:
Excel Total kg = 18.177
Excel diameter-column kg = 18.177

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 — Line 4

Description:
Top bars - Extra

Bar type / role:
TOP_EXTRA (Top bars - Extra)

Diameter:
20 mm  (L.2 source diameter 20.0; normalized 20)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
2

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `2-Y20`
- L.2 key / bar_id: `top_extra_bars` / `R13-B1-TOP_MAIN-602fb7`
- L.2 quantity: 2 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 6358.3 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
20 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 20, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 20, M30)
table_hit = True

Final Ld:
1000 mm / 1.0 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
2.0


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 4158.3,
  "Ld_mm": 1000,
  "two_Ld_mm": 2000
}

L.2 stored cut_length_mm: 6358.3
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 6158.3
expected_from_formula_mm = 6158.3

Result:
6.158 m  (6158.3 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
2

Cut Length:
6.158 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
2 × 6.158300 = 12.316600

Result:
12.317 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
2.466150 kg/m

Total Length:
12.316600 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*20.0^2/4)*6158*2*7850/1e9`)

Calculation:
recomputed = 30.374586 kg
engine = 30.374586 kg

Result:
Excel Total kg = 30.375
Excel diameter-column kg = 30.375

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 — Line 5

Description:
Stirrups (Mid.)

Bar type / role:
STIRRUP (Stirrups (Mid.))

Diameter:
8 mm  (L.2 source diameter 8.0; normalized 8)

Spacing:
0.2

No. of Bars:
21

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `2L-Y8@200#Zone_A`
- L.2 key / bar_id: `stirrups` / `R13-B1-STIRRUP-949d3f`
- L.2 quantity: 21 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2060.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm and geometry.depth_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
stirrup Dvlp.L in Excel is hook allowance 2*N*d, not TABLE 1 Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = 2*(width-2*cover)+2*(depth-2*cover)+2*hook_multiple*d

INPUT VALUES:
{
  "width_mm": 200.0,
  "depth_mm": 750.0,
  "cover_mm": 30,
  "hook_multiple": 5,
  "hook_mm": 80.0,
  "perimeter_mm": 1660.0,
  "defaults_if_missing": "depth default 600 if None; width default 200 if None"
}

L.2 stored cut_length_mm: 2060.0
Engine cut_length_source: `SI1_zone_engine`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 1740.0
expected_from_formula_mm = 1740.0

Result:
1.740 m  (1740.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
2 × hook_multiple × d  (Steel Summary uses GN hook_multiple=5; BBS SI.1 re-entry may use default 10 — see observations)

Development length addition:
none

#### Total Length

No. of Bars:
21

Cut Length:
1.740 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
21 × 1.740000 = 36.540000

Result:
36.54 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
0.394584 kg/m

Total Length:
36.540000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `SI.1: W=(pi*8.0^2/4)*1740*21*7850/1e9`)

Calculation:
recomputed = 14.418101 kg
engine = 14.418101 kg

Result:
Excel Total kg = 14.418
Excel diameter-column kg = 14.418

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: StirrupImprover.compute_beam + StirrupWeightEngine.cut_length_mm then SteelWeightCompletion SI.1 branch
BBS: BBSCompletionEngine.generate re-invokes StirrupImprover.compute_beam per STIRRUP BarSteelWeight
Quantity: StirrupQuantityEngine.calculate (spacing-derived) or L.2 quantity for legacy

### B1 — Line 6

Description:
Spacer bars

Bar type / role:
SPACER (Spacer bars)

Diameter:
25 mm  (L.2 source diameter 25.0; normalized 25)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
3

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `SPACER 25@1000`
- L.2 key / bar_id: `spacer_bars` / `R13-B1-SPACER_BAR-eb6aef`
- L.2 quantity: 3 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 140.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
spacer uses width - 2*cover, not Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = width_mm - 2 * cover_mm  (or provided_cut_length_mm if set)

INPUT VALUES:
{
  "width_mm": 200.0,
  "cover_mm": 30,
  "provided_cut_length_mm": null
}

L.2 stored cut_length_mm: 140.0
Engine cut_length_source: `SpacerRuleEngine_M.2`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 140.0
expected_from_formula_mm = 140.0

Result:
0.140 m  (140.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
none

Development length addition:
none

#### Total Length

No. of Bars:
3

Cut Length:
0.140 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
3 × 0.140000 = 0.420000

Result:
0.42 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
3.853360 kg/m

Total Length:
0.420000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*25.0^2/4)*140*3*7850/1e9`)

Calculation:
recomputed = 1.618411 kg
engine = 1.618411 kg

Result:
Excel Total kg = 1.618
Excel diameter-column kg = 1.618

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 — Line 7

Description:
Spacer bars

Bar type / role:
SPACER (Spacer bars)

Diameter:
25 mm  (L.2 source diameter 25.0; normalized 25)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
7

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `SPACER 25@1000`
- L.2 key / bar_id: `spacer_bars` / `R13-B1-SPACER_BAR-6eda9b`
- L.2 quantity: 7 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 140.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
spacer uses width - 2*cover, not Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = width_mm - 2 * cover_mm  (or provided_cut_length_mm if set)

INPUT VALUES:
{
  "width_mm": 200.0,
  "cover_mm": 30,
  "provided_cut_length_mm": null
}

L.2 stored cut_length_mm: 140.0
Engine cut_length_source: `SpacerRuleEngine_M.2`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 140.0
expected_from_formula_mm = 140.0

Result:
0.140 m  (140.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
none

Development length addition:
none

#### Total Length

No. of Bars:
7

Cut Length:
0.140 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
7 × 0.140000 = 0.980000

Result:
0.98 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
3.853360 kg/m

Total Length:
0.980000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*25.0^2/4)*140*7*7850/1e9`)

Calculation:
recomputed = 3.776293 kg
engine = 3.776293 kg

Result:
Excel Total kg = 3.776
Excel diameter-column kg = 3.776

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 — Line 8

Description:
Spacer bars

Bar type / role:
SPACER (Spacer bars)

Diameter:
25 mm  (L.2 source diameter 25.0; normalized 25)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
3

#### Source Evidence

- Beam ID: B1
- Frame: GF
- Source bar label: `SPACER 25@1000`
- L.2 key / bar_id: `spacer_bars` / `R13-B1-SPACER_BAR-31ecd5`
- L.2 quantity: 3 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 140.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm

VALUE:
clear_span_mm = 4158.3 mm
width_mm = 200.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
spacer uses width - 2*cover, not Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = width_mm - 2 * cover_mm  (or provided_cut_length_mm if set)

INPUT VALUES:
{
  "width_mm": 200.0,
  "cover_mm": 30,
  "provided_cut_length_mm": null
}

L.2 stored cut_length_mm: 140.0
Engine cut_length_source: `SpacerRuleEngine_M.2`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 140.0
expected_from_formula_mm = 140.0

Result:
0.140 m  (140.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
none

Development length addition:
none

#### Total Length

No. of Bars:
3

Cut Length:
0.140 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
3 × 0.140000 = 0.420000

Result:
0.42 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
3.853360 kg/m

Total Length:
0.420000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*25.0^2/4)*140*3*7850/1e9`)

Calculation:
recomputed = 1.618411 kg
engine = 1.618411 kg

Result:
Excel Total kg = 1.618
Excel diameter-column kg = 1.618

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B1 Reconciliation

BEAM ID:
B1

BBS LINE TOTALS (Excel data rows, excluding header):
8 lines

SUM OF BBS ROW WEIGHTS:
106.336 kg  (BBSCompletionEngine rounded 0.001 kg per row)

SteelWeightCompletion bar-sum (Steel Summary source):
106.337 kg

STEEL SUMMARY DIAMETER TOTALS:
106.337 kg  {'16': 54.531198, '20': 30.374586, '8': 14.418101, '25': 7.013115}

STEEL SUMMARY BEAM TOTAL:
106.337 kg

DIFFERENCE (Steel Summary total − diameter sum):
0.0 kg  (within 0.05 kg rounding)

DIFFERENCE (BBS row-sum − SteelWeightCompletion):
-0.001 kg
Within 0.001 kg rounding between unrounded engine weights and 3-decimal BBS cells.

---
## 5. Beam B10

Section 600 × 750 mm. `clear_span_mm` = 2656.6 (`geometry_source` = BEAM_REGISTRY, confidence = 0.55). Emitted roles: ['SPACER', 'STIRRUP', 'TOP_MAIN']. No BOTTOM_MAIN, BOTTOM_EXTRA, or SFR rows on this beam.

### B10 — Line 1

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
20 mm  (L.2 source diameter 20.0; normalized 20)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B10
- Frame: GF
- Source bar label: `5Y20`
- L.2 key / bar_id: `top_main_bars` / `R13-B10-TOP_MAIN-03b02b`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 4856.6 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 2656.6 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
20 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 20, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 20, M30)
table_hit = True

Final Ld:
1000 mm / 1.0 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
2.0


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 2656.6,
  "Ld_mm": 1000,
  "two_Ld_mm": 2000
}

L.2 stored cut_length_mm: 4856.6
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 4656.6
expected_from_formula_mm = 4656.6

Result:
4.657 m  (4656.6 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
5

Cut Length:
4.657 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 4.656600 = 23.283000

Result:
23.283 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
2.466150 kg/m

Total Length:
23.283000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*20.0^2/4)*4657*5*7850/1e9`)

Calculation:
recomputed = 57.419376 kg
engine = 57.419376 kg

Result:
Excel Total kg = 57.419
Excel diameter-column kg = 57.419

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B10 — Line 2

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B10
- Frame: GF
- Source bar label: `5-Y16`
- L.2 key / bar_id: `top_main_bars` / `R13-B10-TOP_EXTRA-f3dada`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2424.2 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 2656.6 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 2656.6,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 2424.2
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 4256.6
expected_from_formula_mm = 4256.6

Result:
4.257 m  (4256.6 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
5

Cut Length:
4.257 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 4.256600 = 21.283000

Result:
21.283 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
21.283000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*4257*5*7850/1e9`)

Calculation:
recomputed = 33.591728 kg
engine = 33.591728 kg

Result:
Excel Total kg = 33.592
Excel diameter-column kg = 33.592

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B10 — Line 3

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B10
- Frame: GF
- Source bar label: `5-Y16`
- L.2 key / bar_id: `top_main_bars` / `R13-B10-TOP_EXTRA-2d1359`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2424.2 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 2656.6 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 2656.6,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 2424.2
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 4256.6
expected_from_formula_mm = 4256.6

Result:
4.257 m  (4256.6 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
5

Cut Length:
4.257 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 4.256600 = 21.283000

Result:
21.283 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
21.283000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*4257*5*7850/1e9`)

Calculation:
recomputed = 33.591728 kg
engine = 33.591728 kg

Result:
Excel Total kg = 33.592
Excel diameter-column kg = 33.592

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B10 — Line 4

Description:
Stirrups (Mid.)

Bar type / role:
STIRRUP (Stirrups (Mid.))

Diameter:
10 mm  (L.2 source diameter 10.0; normalized 10)

Spacing:
0.15

No. of Bars:
18

#### Source Evidence

- Beam ID: B10
- Frame: GF
- Source bar label: `4L-Y10@150#Zone_A`
- L.2 key / bar_id: `stirrups` / `R13-B10-STIRRUP-b7bcf3`
- L.2 quantity: 18 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2900.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm and geometry.depth_mm

VALUE:
clear_span_mm = 2656.6 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
stirrup Dvlp.L in Excel is hook allowance 2*N*d, not TABLE 1 Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = 2*(width-2*cover)+2*(depth-2*cover)+2*hook_multiple*d

INPUT VALUES:
{
  "width_mm": 600.0,
  "depth_mm": 750.0,
  "cover_mm": 30,
  "hook_multiple": 5,
  "hook_mm": 100.0,
  "perimeter_mm": 2460.0,
  "defaults_if_missing": "depth default 600 if None; width default 200 if None"
}

L.2 stored cut_length_mm: 2900.0
Engine cut_length_source: `SI1_zone_engine`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 2560.0
expected_from_formula_mm = 2560.0

Result:
2.560 m  (2560.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
2 × hook_multiple × d  (Steel Summary uses GN hook_multiple=5; BBS SI.1 re-entry may use default 10 — see observations)

Development length addition:
none

#### Total Length

No. of Bars:
18

Cut Length:
2.560 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
18 × 2.560000 = 46.080000

Result:
46.44 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
0.616538 kg/m

Total Length:
46.080000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `SI.1: W=(pi*10.0^2/4)*2560*18*7850/1e9`)

Calculation:
recomputed = 28.410051 kg
engine = 28.410051 kg

Result:
Excel Total kg = 28.632
Excel diameter-column kg = 28.632

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: StirrupImprover.compute_beam + StirrupWeightEngine.cut_length_mm then SteelWeightCompletion SI.1 branch
BBS: BBSCompletionEngine.generate re-invokes StirrupImprover.compute_beam per STIRRUP BarSteelWeight
Quantity: StirrupQuantityEngine.calculate (spacing-derived) or L.2 quantity for legacy

### B10 — Line 5

Description:
Spacer bars

Bar type / role:
SPACER (Spacer bars)

Diameter:
25 mm  (L.2 source diameter 25.0; normalized 25)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
4

#### Source Evidence

- Beam ID: B10
- Frame: GF
- Source bar label: `SPACER 25@1000`
- L.2 key / bar_id: `spacer_bars` / `R13-B10-SPACER_BAR-c8906a`
- L.2 quantity: 4 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 540.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm

VALUE:
clear_span_mm = 2656.6 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
spacer uses width - 2*cover, not Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = width_mm - 2 * cover_mm  (or provided_cut_length_mm if set)

INPUT VALUES:
{
  "width_mm": 600.0,
  "cover_mm": 30,
  "provided_cut_length_mm": null
}

L.2 stored cut_length_mm: 540.0
Engine cut_length_source: `SpacerRuleEngine_M.2`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 540.0
expected_from_formula_mm = 540.0

Result:
0.540 m  (540.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
none

Development length addition:
none

#### Total Length

No. of Bars:
4

Cut Length:
0.540 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
4 × 0.540000 = 2.160000

Result:
2.16 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
3.853360 kg/m

Total Length:
2.160000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*25.0^2/4)*540*4*7850/1e9`)

Calculation:
recomputed = 8.323257 kg
engine = 8.323257 kg

Result:
Excel Total kg = 8.323
Excel diameter-column kg = 8.323

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B10 Reconciliation

BEAM ID:
B10

BBS LINE TOTALS (Excel data rows, excluding header):
5 lines

SUM OF BBS ROW WEIGHTS:
161.558 kg  (BBSCompletionEngine rounded 0.001 kg per row)

SteelWeightCompletion bar-sum (Steel Summary source):
161.33614 kg

STEEL SUMMARY DIAMETER TOTALS:
161.335 kg  {'20': 57.419376, '16': 67.183457, '10': 28.410051, '25': 8.323257}

STEEL SUMMARY BEAM TOTAL:
161.336 kg

DIFFERENCE (Steel Summary total − diameter sum):
0.001 kg  (within 0.05 kg rounding)

DIFFERENCE (BBS row-sum − SteelWeightCompletion):
0.22186 kg
This is **not** rounding: stirrup cut/weight on the BBS sheet was recomputed by a second SI.1 call without the GN loader.

---
## 6. Beam B23

Section 600 × 750 mm. `clear_span_mm` = 7800.351 (`geometry_source` = REINFORCEMENT_DIMENSION, confidence = 0.582). Emitted roles: ['SPACER', 'STIRRUP', 'TOP_EXTRA', 'TOP_MAIN']. No BOTTOM_MAIN, BOTTOM_EXTRA, or SFR rows on this beam.

### B23 — Line 1

Description:
Top bars

Bar type / role:
TOP_MAIN (Top bars)

Diameter:
20 mm  (L.2 source diameter 20.0; normalized 20)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B23
- Frame: GF
- Source bar label: `5-Y20`
- L.2 key / bar_id: `top_main_bars` / `R13-B23-TOP_MAIN-5c6a95`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 10000.4 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 7800.351 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
20 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 20, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 20, M30)
table_hit = True

Final Ld:
1000 mm / 1.0 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
2.0


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 7800.351,
  "Ld_mm": 1000,
  "two_Ld_mm": 2000
}

L.2 stored cut_length_mm: 10000.4
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 9800.350999999999
expected_from_formula_mm = 9800.350999999999

Result:
9.800 m  (9800.4 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
5

Cut Length:
9.800 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 9.800351 = 49.001755

Result:
49.002 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
2.466150 kg/m

Total Length:
49.001755 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*20.0^2/4)*9800*5*7850/1e9`)

Calculation:
recomputed = 120.845690 kg
engine = 120.845690 kg

Result:
Excel Total kg = 120.846
Excel diameter-column kg = 120.846

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B23 — Line 2

Description:
Top bars - Extra

Bar type / role:
TOP_EXTRA (Top bars - Extra)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B23
- Frame: GF
- Source bar label: `5Y16#L`
- L.2 key / bar_id: `top_extra_bars` / `R13-B23-TOP_EXTRA-645920`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 3710.1 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 7800.351 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 7800.351,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 3710.1
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 9400.350999999999
expected_from_formula_mm = 9400.350999999999

Result:
9.400 m  (9400.4 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
5

Cut Length:
9.400 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 9.400351 = 47.001755

Result:
47.002 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
47.001755 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*9400*5*7850/1e9`)

Calculation:
recomputed = 74.184569 kg
engine = 74.184569 kg

Result:
Excel Total kg = 74.185
Excel diameter-column kg = 74.185

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B23 — Line 3

Description:
Top bars - Extra

Bar type / role:
TOP_EXTRA (Top bars - Extra)

Diameter:
16 mm  (L.2 source diameter 16.0; normalized 16)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B23
- Frame: GF
- Source bar label: `5Y16#R`
- L.2 key / bar_id: `top_extra_bars` / `R13-B23-TOP_EXTRA-a36b4f`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 3710.1 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.clear_span_mm

VALUE:
clear_span_mm = 7800.351 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
YES

Steel:
Fe550

Diameter:
16 mm

Concrete:
M30

Rule source:
Galera GN TABLE 1 (`development_length_table[(Fe550, 16, M30)]`)

Resolved Ld/d:
50.0

Formula:
Ld_mm = EngineeringContextLoader.get_development_length_mm(dia, concrete, steel)
     = table[(steel, dia, conc)]   # current implementation; not 40d scalar

Calculation:
key = (Fe550, 16, M30)
table_hit = True

Final Ld:
800 mm / 0.8 m

Excel Dvlp. L (m) display formula:
BBSCompletionEngine: dvlp_m = cut_m - span_m   (= 2*Ld/1000 for longitudinal; NEGATIVE for spacers)

Excel Dvlp. L (m) value this line would display:
1.6


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = clear_span_mm + 2 * Ld_mm

INPUT VALUES:
{
  "clear_span_mm": 7800.351,
  "Ld_mm": 800,
  "two_Ld_mm": 1600
}

L.2 stored cut_length_mm: 3710.1
Engine cut_length_source: `EngineeringContext`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 9400.350999999999
expected_from_formula_mm = 9400.350999999999

Result:
9.400 m  (9400.4 mm)

Cover deduction:
none on longitudinal (Ld added, cover not deducted from span)

Hook addition:
none

Development length addition:
+ 2 × Ld_mm

#### Total Length

No. of Bars:
5

Cut Length:
9.400 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 9.400351 = 47.001755

Result:
47.002 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
1.578336 kg/m

Total Length:
47.001755 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*16.0^2/4)*9400*5*7850/1e9`)

Calculation:
recomputed = 74.184569 kg
engine = 74.184569 kg

Result:
Excel Total kg = 74.185
Excel diameter-column kg = 74.185

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B23 — Line 4

Description:
Stirrups (Mid.)

Bar type / role:
STIRRUP (Stirrups (Mid.))

Diameter:
10 mm  (L.2 source diameter 10.0; normalized 10)

Spacing:
0.1

No. of Bars:
79

#### Source Evidence

- Beam ID: B23
- Frame: GF
- Source bar label: `4L-Y10@100#Zone_A`
- L.2 key / bar_id: `stirrups` / `R13-B23-STIRRUP-2ee285`
- L.2 quantity: 79 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 2900.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm and geometry.depth_mm

VALUE:
clear_span_mm = 7800.351 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
stirrup Dvlp.L in Excel is hook allowance 2*N*d, not TABLE 1 Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = 2*(width-2*cover)+2*(depth-2*cover)+2*hook_multiple*d

INPUT VALUES:
{
  "width_mm": 600.0,
  "depth_mm": 750.0,
  "cover_mm": 30,
  "hook_multiple": 5,
  "hook_mm": 100.0,
  "perimeter_mm": 2460.0,
  "defaults_if_missing": "depth default 600 if None; width default 200 if None"
}

L.2 stored cut_length_mm: 2900.0
Engine cut_length_source: `SI1_zone_engine`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 2560.0
expected_from_formula_mm = 2560.0

Result:
2.560 m  (2560.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
2 × hook_multiple × d  (Steel Summary uses GN hook_multiple=5; BBS SI.1 re-entry may use default 10 — see observations)

Development length addition:
none

#### Total Length

No. of Bars:
79

Cut Length:
2.560 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
79 × 2.560000 = 202.240000

Result:
203.82 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
0.616538 kg/m

Total Length:
202.240000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `SI.1: W=(pi*10.0^2/4)*2560*79*7850/1e9`)

Calculation:
recomputed = 124.688556 kg
engine = 124.688556 kg

Result:
Excel Total kg = 125.663
Excel diameter-column kg = 125.663

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: StirrupImprover.compute_beam + StirrupWeightEngine.cut_length_mm then SteelWeightCompletion SI.1 branch
BBS: BBSCompletionEngine.generate re-invokes StirrupImprover.compute_beam per STIRRUP BarSteelWeight
Quantity: StirrupQuantityEngine.calculate (spacing-derived) or L.2 quantity for legacy

### B23 — Line 5

Description:
Spacer bars

Bar type / role:
SPACER (Spacer bars)

Diameter:
25 mm  (L.2 source diameter 25.0; normalized 25)

Spacing:
none (not a spacing-derived longitudinal/spacer BBS field)

No. of Bars:
5

#### Source Evidence

- Beam ID: B23
- Frame: GF
- Source bar label: `SPACER 25@1000`
- L.2 key / bar_id: `spacer_bars` / `R13-B23-SPACER_BAR-7ce240`
- L.2 quantity: 5 (classified: **directly extracted** from L.2 `quantity`, except stirrups which are SI.1 spacing-derived and happened to equal L.2 qty on these three beams)
- L.2 `cut_length_mm` on record: 540.0 — **not used** for longitudinal cut in VB.1 (`provided_cut` is honored only for SPACER)
- Provenance: L.2 `engineering_metadata` empty on these records; bar_id prefix `R13-` indicates Phase R.1.3 EngineeringBarBuilder

#### Geometry Source

FIELD USED:
geometry.width_mm

VALUE:
clear_span_mm = 7800.351 mm
width_mm = 600.0 mm
depth_mm = 750.0 mm
cover_mm = 30 mm (GN TABLE 2, not the L.2 top_cover_mm field at calculation time except as duplicate 30)

UNIT:
mm

SOURCE:
L.2 `model.geometry` (B1/B10 `geometry_source=BEAM_REGISTRY` confidence 0.55; B23 `REINFORCEMENT_DIMENSION` confidence 0.582)
VB.1: `SteelWeightCompletion._compute_beam`: `span_mm = float(geom.get("clear_span_mm") or 0)`

SOURCE CODE PATH:
`PhaseVB.1_production_output_completion/steel_weight_completion.py` `_compute_beam` / `_derive_cut_length`

LOW_CLEAR_LENGTH:
Not a pipeline field. No symbol by that name. The length consumed for longitudinal bars is **`clear_span_mm`**, aliased as `span_mm` inside VB.1. `effective_span_mm` on the L.2 geometry object equals `clear_span_mm` on these three beams and is **not** read by `_compute_beam`.

#### Development Length

Used:
NO

Reason:
spacer uses width - 2*cover, not Ld


#### Clear / Effective Length

As above. Longitudinal cut uses `clear_span_mm` + 2×Ld. Stirrups use section width/depth, not span, for cut; span is used only for quantity. Spacers use width − 2×cover.

#### Cut Length

Formula:
cut_mm = width_mm - 2 * cover_mm  (or provided_cut_length_mm if set)

INPUT VALUES:
{
  "width_mm": 600.0,
  "cover_mm": 30,
  "provided_cut_length_mm": null
}

L.2 stored cut_length_mm: 540.0
Engine cut_length_source: `SpacerRuleEngine_M.2`
cut_matches_current_formula: True

Calculation:
engine_cut_mm = 540.0
expected_from_formula_mm = 540.0

Result:
0.540 m  (540.0 mm)

Cover deduction:
width/depth minus 2×cover on each face (stirrup perimeter / spacer)

Hook addition:
none

Development length addition:
none

#### Total Length

No. of Bars:
5

Cut Length:
0.540 m

Formula:
total_length_m = quantity × cut_length_mm / 1000
(`BBSCompletionEngine.generate`; SI.1 `group_to_bbs_dict` same)

Calculation:
5 × 0.540000 = 2.700000

Result:
2.7 m (Excel/BBS rounded)

#### Weight

Unit weight formula:
uw_kg_m = (π × d² / 4) × 1000 × 7850 / 1e9
        = (π × d² / 4) × 0.00785 kg/m

Unit weight:
3.853360 kg/m

Total Length:
2.700000 m

Final formula:
Weight = (π × d² / 4) × cut_length_mm × quantity × 7850 / 1e9
(`BarSteelWeight.formula_used` = `W = (pi*25.0^2/4)*540*5*7850/1e9`)

Calculation:
recomputed = 10.404071 kg
engine = 10.404071 kg

Result:
Excel Total kg = 10.404
Excel diameter-column kg = 10.404

line total weight equals the occupied diameter column (rounded to 0.001 kg).

#### Code Path

Weight: SteelWeightCompletion._compute_bar / _derive_cut_length
BBS: BBSCompletionEngine.generate
Quantity: L.2 bar.quantity (directly extracted)

### B23 Reconciliation

BEAM ID:
B23

BBS LINE TOTALS (Excel data rows, excluding header):
5 lines

SUM OF BBS ROW WEIGHTS:
405.283 kg  (BBSCompletionEngine rounded 0.001 kg per row)

SteelWeightCompletion bar-sum (Steel Summary source):
404.307455 kg

STEEL SUMMARY DIAMETER TOTALS:
404.308 kg  {'20': 120.84569, '16': 148.369138, '10': 124.688556, '25': 10.404071}

STEEL SUMMARY BEAM TOTAL:
404.307 kg

DIFFERENCE (Steel Summary total − diameter sum):
-0.001 kg  (within 0.05 kg rounding)

DIFFERENCE (BBS row-sum − SteelWeightCompletion):
0.975545 kg
This is **not** rounding: stirrup cut/weight on the BBS sheet was recomputed by a second SI.1 call without the GN loader.

---
## 7. Cross-Beam Calculation Matrix

| Bar Role | B1 Calculation Path | B10 Calculation Path | B23 Calculation Path | Same / Different |
| --- | --- | --- | --- | --- |
| Geometry source | BEAM_REGISTRY `clear_span_mm` 4158.3 | BEAM_REGISTRY `clear_span_mm` 2656.6 | REINFORCEMENT_DIMENSION `clear_span_mm` 7800.351 | Same field, different source class |
| Longitudinal TOP_MAIN | span + 2×Ld; **3 records** each 2Y16 full span | span + 2×Ld; 5Y20 once + **2 records** 5Y16 full span | span + 2×Ld; 5Y20 once | Same formula; B1/B10 duplicate groups |
| Extra top | 2Y20 span+2×Ld | (none) | 5Y16#L and 5Y16#R both span+2×Ld (L.2 cuts 3710 ignored) | Same formula when present |
| Stirrups | SI.1 uniform `floor(span/s)+1`; cut with GN cover 30 / hook 5d for Steel Summary | same family | same family | Same; BBS sheet uses loader-less SI.1 on B10/B23 (visible cut/weight drift) |
| Spacer | provided L.2 cut 140 = 200−2×30 | provided L.2 cut 540 = 600−2×30 | provided L.2 cut 540 = 600−2×30 | Same `width-2cover` / M.2 |
| Ld usage | TABLE 1 Fe550/M30 50d on long bars; stirrup Excel Dvlp = hook not Ld | same | same | Same |
| Quantity | L.2 qty copied (stirrup SI.1 equals L.2) | same | same | Same |
| Weight | πd²/4 × L × 7850/1e9 | same | same | Same |
| SFR / bottom | not emitted | not emitted | not emitted | Same (absent) |

---

## 8. Suspected Calculation Issues

All items below are **W17_OBSERVATION_ONLY**. None were fixed.

ISSUE ID:
W17-OBS-01

BEAM:
B1, B10, B23 (all longitudinal)

BAR ROLE:
TOP_MAIN / TOP_EXTRA

OBSERVED BEHAVIOR:
L.2 already stores `cut_length_mm` (piece-specific, e.g. B1 2799.6 mm vs 5918.3 mm; B23 extras 3710.1 mm). VB.1 **discards** that value for non-spacer roles and always uses `clear_span_mm + 2×Ld`.

CURRENT FORMULA:
`cut_mm = span_mm + 2 * get_development_length_mm(d)`  
`provided_cut` is read only when `role == "SPACER"`.

INPUT VALUES:
B1 Y16 L.2 cuts 5918.3 / 2799.6 / 2799.6 → engine 5758.3 for all three.
B23 extras L.2 3710.1 → engine 9400.4.

WHY IT LOOKS SUSPICIOUS:
Left/right or curtailed pieces are billed as full-span bars with both-end Ld.

SOURCE CODE:
`steel_weight_completion.py` `_derive_cut_length` (longitudinal branch) and `_compute_bar` (provided_cut only forwarded for spacer).

RECOMMENDED FOLLOW-UP:
Correction phase: honor piece `cut_length_mm` or apply curtailment geometry instead of always span+2Ld.

Classification:
CONFIRMED (current formula)

---

ISSUE ID:
W17-OBS-02

BEAM:
B1, B10, B23

BAR ROLE:
TOP_MAIN / TOP_EXTRA

OBSERVED BEHAVIOR:
Multiple L.2 records with the same label each receive a **full** span+2Ld cut. B1 emits three 2-Y16 rows (6 bars billed at 5.758 m). B10 emits two 5-Y16 rows. B23 emits both 5Y16#L and 5Y16#R at full 9.400 m.

CURRENT FORMULA:
One BBS row per L.2 bar record; each independently `span + 2 Ld`.

INPUT VALUES:
B1: three `top_main_bars` 2-Y16. bar_id strings include `TOP_EXTRA` while sitting in `top_main_bars`.
B23: labels `5Y16#L` / `5Y16#R`.

WHY IT LOOKS SUSPICIOUS:
Looks like piece-splitting (left/mid/right) without reducing length or quantity. May triple-count top steel on B1.

SOURCE CODE:
R.1.3 builder emission into L.2 lists + VB.1 per-record full-span cut.

RECOMMENDED FOLLOW-UP:
Estimator to confirm intended bars vs pieces. Then a correction phase for piece vs group aggregation.

Classification:
CONFIRMED that the pipeline does this; NEEDS ESTIMATOR REVIEW whether the drawing intends 6×Y16 full length on B1.

---

ISSUE ID:
W17-OBS-03

BEAM:
B1, B10, B23

BAR ROLE:
SPACER

OBSERVED BEHAVIOR:
Excel **Dvlp. L (m)** is negative (B1 −4.018, B10 −2.117, B23 −7.260).

CURRENT FORMULA:
`dvlp_length_m = cut_length_mm/1000 - span_mm/1000` applied to **all** non-stirrup rows.

INPUT VALUES:
B1: cut 0.140 m, span 4.158 m → −4.018 m.

WHY IT LOOKS SUSPICIOUS:
Spacers do not use development length. The column is a residual of the longitudinal identity `cut = span + 2 Ld`.

SOURCE CODE:
`bbs_completion_engine.py` `BBSCompletionEngine.generate` dvlp assignment.

RECOMMENDED FOLLOW-UP:
Do not use cut−span for spacers; leave blank or show N/A.

Classification:
CONFIRMED

---

ISSUE ID:
W17-OBS-04

BEAM:
B10, B23 (B1 cut coincidentally identical)

BAR ROLE:
STIRRUP

OBSERVED BEHAVIOR:
Steel Summary stirrup weight uses loader-aware SI.1 (cover 30 mm, hook 5d). The BBS sheet re-invokes `StirrupImprover()` constructed **without** a loader at import time (cover fallback 40 mm, hook fallback 10d).

CURRENT FORMULA:
Steel Summary: `cut = 2(W−2×30)+2(D−2×30)+2×5×d`
BBS sheet: `cut = 2(W−2×40)+2(D−2×40)+2×10×d`

INPUT VALUES:
B10: Steel Summary cut 2560 mm, 28.410 kg; BBS/Excel cut 2.58 m, 28.632 kg; Δ = 0.222 kg.
B23: Steel Summary 2560 mm, 124.689 kg; BBS/Excel 2.58 m, 125.663 kg; Δ = 0.976 kg.
B1 Y8: both cuts 1740 mm (numerical coincidence of the two formulas on 200×750).

WHY IT LOOKS SUSPICIOUS:
One beam, two stirrup cut lengths. Steel Summary vs BBS do not share the same SI.1 context.

SOURCE CODE:
`steel_weight_completion.py` constructs `StirrupImprover(loader)`.
`bbs_completion_engine.py` module-level `_STIRRUP_IMPROVER = StirrupImprover()` then `compute_beam(bar.__dict__, ...)`.

RECOMMENDED FOLLOW-UP:
Pass the same loader into the BBS SI.1 instance; do not recompute stirrups from BarSteelWeight dicts.

Classification:
CONFIRMED

---

ISSUE ID:
W17-OBS-05

BEAM:
all longitudinal lines

BAR ROLE:
TOP_MAIN / TOP_EXTRA

OBSERVED BEHAVIOR:
Excel column **Dvlp. L (m)** equals **2×Ld in metres**, not one-end Ld (Y16 → 1.600 m = 2 × 0.800 m).

CURRENT FORMULA:
`dvlp_m = round(cut_m - span_m, 3)` = `2 Ld / 1000`.

WHY IT LOOKS SUSPICIOUS:
Estimators may read the column as single-end development. The implementation stores the two-end remainder.

SOURCE CODE:
`bbs_completion_engine.py` lines computing `dvlp_length_m`.

RECOMMENDED FOLLOW-UP:
Label the column as 2Ld or print one-end Ld.

Classification:
CONFIRMED (display convention, not a weight error)

---

ISSUE ID:
W17-OBS-06

BEAM:
B1

BAR ROLE:
TOP_MAIN vs TOP_EXTRA labelling

OBSERVED BEHAVIOR:
`bar_id` `R13-B1-TOP_EXTRA-...` sits in L.2 `top_main_bars` (2-Y16). `R13-B1-TOP_MAIN-...` sits in `top_extra_bars` (2-Y20). BBS descriptions follow the **L.2 list key**, not the bar_id role token.

CURRENT FORMULA:
`_L2_ROLE_MAP` in `steel_weight_completion.py`.

WHY IT LOOKS SUSPICIOUS:
Role inversion between identifier and bucket. Estimator may disagree which layer is “extra”.

SOURCE CODE:
R.1.3 emission + VB.1 `_L2_ROLE_MAP`.

RECOMMENDED FOLLOW-UP:
Drawing check of B1 top vs extra; then role-mapping correction phase.

Classification:
SUSPECTED / NEEDS ESTIMATOR REVIEW

---

## 9. Reconciliation Results

| Beam | Excel BBS lines | BBS weight sum (kg) | Steel Summary total (kg) | SS vs diameter sum (kg) | BBS vs SS engine (kg) |
| --- | ---: | ---: | ---: | ---: | ---: |
| B1 | 8 | 106.336 | 106.337 | 0.000 | −0.001 (rounding) |
| B10 | 5 | 161.558 | 161.336 | 0.001 | +0.222 (OBS-04 stirrup) |
| B23 | 5 | 405.283 | 404.307 | −0.001 | +0.976 (OBS-04 stirrup) |

Steel Summary **beam total = diameter subtotal** within 0.001 kg on all three beams. That invariant holds. The BBS sheet is **not** the Steel Summary source; stirrup dual-path makes B10/B23 BBS sums differ.

No UNTRACEABLE numeric outputs on the audited lines. Geometry provenance stops at L.2 `geometry_source` (registry vs reinforcement dimension); framing DXF entity IDs were not required to reproduce VB.1 numbers.

---

## 10. Final Classification

**W17_AUDIT_COMPLETE_WITH_OBSERVATIONS**

**ESTIMATOR_REVIEW_READY**

The BBS lines for B1, B10, and B23 are fully reproduced from current source code and W.16 Galera context. Observations above are documented, not patched.

Recommended next correction phase (not executed here):

1. Stop dual SI.1 (BBS without loader) so BBS stirrup cut matches Steel Summary.
2. Do not apply span+2Ld to every L.2 piece; use piece cut or curtailment for #L/#R and short records.
3. Stop printing cut−span as Dvlp.L on spacers.
4. Estimator review of B1 2-Y16 triple emission and B1 top vs extra role buckets.
