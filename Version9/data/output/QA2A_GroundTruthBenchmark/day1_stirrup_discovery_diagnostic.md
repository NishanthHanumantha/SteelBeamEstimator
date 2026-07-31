# Day-1 Diagnostic — Stirrup Discovery vs Association

**MODEL_VERSION:** 9.1.0 (read-only; no code/config/artefact modifications)

## Verdict

**Dominant failure mode: DISCOVERY** (R.1 loose stirrup texts = 20 vs GT stirrup rows = 209; ratio **9.6%**).

Every stirrup annotation that R.1 *does* find survives into the final model as `STIRRUP` (association/relationship loss volume on discovered texts = **0** in the traced sample). The ~182 §2 production MISSING rows are explained by **absent per-beam stirrup callout text**, not by R.1.1A/R.3.1 dropping them.

**Track 1 (vector-space geometric stirrup evidence): CONFIRMED** for the volume problem. A pure association-rule fix would not recover the bulk.

## Step 1 — Regex scan of R.1 `reinforcement_annotations.json`

Patterns:
- **Strict Type2/Type3** from `Requirement_Rules.txt` (`\dL-Y…@…C/C`)
- **Loose** = R.1 native `_RE_STIRRUP` (`Y8@100C/C` without required `2L-` prefix)

| Set | Annos scanned | Type2 | Type3 | Strict total | Loose YD@S | R.1 role=STIRRUP | Near-misses |
|-----|--------------:|------:|------:|-------------:|-----------:|-----------------:|------------:|
| First Set Drawings | 65 | 0 | 0 | 0 | 0 | 0 | 0 |
| Second Set Drawings | 229 | 0 | 0 | 0 | 3 | 3 | 1 |
| Third Set Drawings | 277 | 2 | 0 | 2 | 17 | 17 | 1 |

### Samples (loose — authoritative for what R.1 can parse)

**First Set Drawings:**
- `(none)`

**Second Set Drawings:**
- `Y8@100C/C`
- `Y8@150C/C`
- `Y8@150C/C`
Near-misses (gate hit, strict/loose rejected):
- beam BR1: `2L-Y8,3 NO'S`

**Third Set Drawings:**
- `Y8@100C/C`
- `Y8@100C/C`
- `Y8@150C/C`
- `Y8@150C/C`
- `Y8@150C/C`
Strict Type2/Type3 samples:
- `2L-Y8@200C/C`
- `4L-Y8@100C/C`
Near-misses (gate hit, strict/loose rejected):
- beam B56: `TYPICAL STIRRUP DETAILS`

### Near-miss insight

Most real drawing callouts are `Y8@100C/C` / `Y8@150C/C` (**no `NL-` leg prefix**). Strict Requirement_Rules Type2 alone under-counts; R.1's own loose regex already accepts them. Strict≪loose is a regex-breadth issue in this diagnostic, **not** evidence of additional undiscovered text inside R.1 JSON.

### DXF corroboration (read-only, same run inputs)

| Set | DXF MSP loose | DXF INSERT virtual loose | R.1 loose |
|-----|--------------:|-------------------------:|----------:|
| First Set Drawings | 0 | 0 | 0 |
| Second Set Drawings | 3 | 7 | 3 |
| Third Set Drawings | 17 | 3 | 17 |

R.1 loose counts **exactly match** DXF modelspace TEXT/MTEXT (20 = 20). INSERT.virtual_entities would add **~10** more (Sets 2/3); Set 1 has a block-*definition* `2L-Y10@100C/C` that is **not inserted** into MSP.

## Step 2 — Discovery vs GT

| Set | GT stirrup rows | R.1 stirrup annos (loose) | Discovery ratio |
|-----|----------------:|--------------------------:|----------------:|
| First Set Drawings | 23 | 0 | 0.0% |
| Second Set Drawings | 90 | 3 | 3.3% |
| Third Set Drawings | 96 | 17 | 17.7% |

**Overall:** 20 R.1 discoveries / 209 GT rows = **9.6%**.

§2 baseline (final production): 182 missing / 12 partial / 11 wrong-qty / 2 matched.

**Gap signal (primary):** R.1 discoveries = DXF MSP texts << GT. The gap between R.1 and production for *discovered* texts is ~0; the gap between R.1 and GT is the story (~189 GT rows never appear as stirrup text in R.1).

## Step 3 — Per-beam trace (R.1 → R.1.1A → R.3.1 → final)

| Beam | Set | GT statuses | R.1 found? | Strings | R.1.1A beam? | R.3.1 explicit? | Final | Loss stage |
|------|-----|-------------|------------|---------|--------------|-----------------|-------|------------|
| B1 | First Set Drawings | PARTIAL_MATCH | N | `—` | Y | N* | PARTIAL/misfile vs GT | DISCOVERY + QA false-PARTIAL (no stirrup text; model SFR/spacer matched to GT stirrup) |
| B9 | First Set Drawings | PARTIAL_MATCH | N | `—` | Y | N* | PARTIAL/misfile vs GT | DISCOVERY + QA false-PARTIAL (no stirrup text; model SFR/spacer matched to GT stirrup) |
| B10 | First Set Drawings | PARTIAL_MATCH | N | `—` | Y | N* | PARTIAL/misfile vs GT | DISCOVERY + QA false-PARTIAL (no stirrup text; model SFR/spacer matched to GT stirrup) |
| B2 | First Set Drawings | MISSING,MISSING | N | `—` | Y | N* | MISSING | R.1 discovery (stirrup text never in R.1) |
| B6 | Second Set Drawings | WRONG_DIAMETER,MISSING | Y | `Y8@100C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |
| B36 | Second Set Drawings | WRONG_QUANTITY | Y | `Y8@150C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |
| B38 | Second Set Drawings | WRONG_QUANTITY | Y | `Y8@150C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |
| B1 | Second Set Drawings | MISSING | N | `—` | Y | N* | MISSING | R.1 discovery (stirrup text never in R.1) |
| B16 | Third Set Drawings | - | Y | `Y8@100C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |
| B19 | Third Set Drawings | WRONG_DIAMETER,MISSING,MISSING,MISSING,MISSING | Y | `Y8@150C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |
| B38 | Third Set Drawings | MATCH | Y | `Y8@150C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |
| B42 | Third Set Drawings | WRONG_QUANTITY | Y | `2L-Y8@200C/C` | Y | N* | STIRRUP present | none — survived R.1 to final as STIRRUP |

\* R.3.1 JSON often lacks STIRRUP role strings even when the bar later appears in `engineering_bar_models.json`; final column is authoritative for survival.

Traced distribution: discovery-loss 5/12; discovered-and-kept 7/12; association/role-loss 0/12.

## Step 4 — Outcome classification

| Signal | Value |
|--------|-------|
| Discovery ratio (Step 2) | **9.6%** (R.1 ≪ GT) |
| Per-beam pattern (Step 3) | 5 never in R.1; 7 found+kept; 0 assoc/role loss |
| Volume-weighted | ~189 of 209 GT rows never text-discovered; 0/20 discovered texts lost before final STIRRUP |
| **Outcome** | **DISCOVERY dominates** |
| **Fix class** | Track 1 geometric / typical-detail inference for volume; optional INSERT text explode as micro TEXT FIX |

Plan T1.3 claim 'annotation exists but never associated' is FALSIFIED for the dominant volume: annotations mostly do not exist as per-beam MSP text. Association loss volume on discovered texts = 0 in this sample.

## Step 5 — Recommendation

1. **CONFIRM Track 1** (vector-space stirrup detector in DXF geometry → R.2.1D `GEOMETRY_STIRRUP` evidence). Effort class: **GEOMETRIC EVIDENCE ENGINE (~weeks)**.
2. **Do not** treat this as a 1-week R.1.1A/R.3.1 association-threshold fix — that path cannot create the ~180 missing callouts that were never text.
3. **Optional parallel TEXT FIX (~days):** explode `INSERT.virtual_entities()` in `adaptive_association_engine._collect_entities` (~lines 168–190) to pick up ~10 block-nested `Y8@…C/C` callouts on Sets 2/3.
4. Set1 B1/B9/B10 §2 PARTIAL/WRONG_ROLE pattern is **not** stirrup text mis-filed after discovery — R.1 never had stirrup text; QA matched SFR/spacer model rows to GT STIRRUP.

### File / line pointers

- `Version9/src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py:_collect_entities (~L168) — TEXT/MTEXT only, skips INSERT`
- `Version9/src/PhaseR.1_generalized_reinforcement_discovery/annotation_discovery.py:_RE_STIRRUP (~L47) — already accepts Y8@150C/C`
- `Version9/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_role_classifier.py — not the dominant loss path for missing rows`

## Artefact paths (reproducibility)

- **First Set Drawings**
  - r1_annotations: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_First_Set_Drawings_20260731_154657\data\output\PhaseR.1_generalized_reinforcement_discovery\reinforcement_annotations.json`
  - qa_bar_matching: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\output\QA2A_GroundTruthBenchmark\First_Set_Drawings\bar_matching.json`
  - run_root: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_First_Set_Drawings_20260731_154657`
  - dxf: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_First_Set_Drawings_20260731_154657\reinforcement\SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf`
- **Second Set Drawings**
  - r1_annotations: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Second_Set_Drawings_20260731_154739\data\output\PhaseR.1_generalized_reinforcement_discovery\reinforcement_annotations.json`
  - qa_bar_matching: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\output\QA2A_GroundTruthBenchmark\Second_Set_Drawings\bar_matching.json`
  - run_root: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Second_Set_Drawings_20260731_154739`
  - dxf: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Second_Set_Drawings_20260731_154739\reinforcement\Galera_GF_BeamReinforcementDetails.dxf`
- **Third Set Drawings**
  - r1_annotations: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Third_Set_Drawings_20260731_154835\data\output\PhaseR.1_generalized_reinforcement_discovery\reinforcement_annotations.json`
  - qa_bar_matching: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\output\QA2A_GroundTruthBenchmark\Third_Set_Drawings\bar_matching.json`
  - run_root: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Third_Set_Drawings_20260731_154835`
  - dxf: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Third_Set_Drawings_20260731_154835\reinforcement\Galera_TF_BeamReinforcementDetails.dxf`

## Integrity confirmation

- NO pipeline source code modified for this diagnostic
- NO config modified
- NO production artefacts rewritten
- NO stages re-run — used existing Version9 `qa2_*_20260731_154*` web_run outputs only
- DXF files were opened read-only for corroboration counts (same inputs as those runs)
- Diagnostic script path: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\output\QA2A_GroundTruthBenchmark\day1_stirrup_discovery_diagnostic.py`
