# Day-1 Addendum — Set 1 Stirrup Notation Exhaustive Raw-Text Sweep

**MODEL_VERSION:** 9.1.0 (read-only; no code/config/artefact modifications)

## Verdict: **B — EXISTS BUT UNREACHED** (confidence: HIGH)

Set 1 stirrup notation **does exist** as live drawing text. It is stored almost entirely in **DIMENSION entity text overrides** on layer `-STR-RF-DIM`, often with an MTEXT paragraph break between `@` and the spacing (`2L-Y8@\P100C/C`).

R.1’s entity collector only accepts `TEXT` / `MTEXT` (`adaptive_association_engine._collect_entities`, ~L171), so these callouts never enter discovery — producing the Day-1 **0/23** Set 1 result.

This is a **third failure mode: NOTATION-FORMAT / ENTITY-TYPE MISS**, not pure geometry absence. For Set 1, prefer a **small discovery patch (~1–2 days)** before committing Set 1 entirely to Track 1 geometry inference.

> Day-1 overall Track 1 confirmation for Sets 2/3 (sparse MSP TEXT) still stands. This addendum **revises Set 1 only**: Set 1’s zero was an R.1 blind spot, not true absence.

---

## Step 1 — Confirmed Set 1 source files

Same Day-1 run_root / drawing_manifest:

- **run_root:** `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_First_Set_Drawings_20260731_154657`
- **manifest:** `…\PhaseVROOT.1_dynamic_pipeline_initialization\drawing_manifest.json`
- **GENERAL_NOTES:** `…\general_notes\SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf`
- **FRAMING_PLAN:** `…\framing\SampleBeam_FramingPlan_DXF.dxf`
- **BEAM_REINFORCEMENT:** `…\reinforcement\SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf`

---

## Step 2 — Exhaustive match summary

Sweep covered: modelspace + paperspace + every block definition + `INSERT.virtual_entities()` + ATTRIB/ATTDEF + DIMENSION text overrides + TABLE/MLEADER best-effort. No layer filter. Case-insensitive substrings: `C/C`, `L-Y`, `Ø`/`PHI`/`DIA`, `STIRRUP`; `@` counted only.

### GENERAL_NOTES

| Finding | Detail |
|---------|--------|
| Stirrup callouts (`YD@S`) | **None** |
| Legend | `STRPS = STIRRUPS` (abbreviation table) |
| DIA noise | Several general-notes sentences containing `DIA` (not stirrup callouts) |
| XREFs | none blocking |

### FRAMING_PLAN

| Finding | Detail |
|---------|--------|
| Live MSP callouts | **None** |
| Unreferenced block `A$C01067336` | `2L-Y10@100C/C` (MTEXT) + `2L-Y8@100C/C` (DIMENSION) — **not inserted** into MSP |
| Legend block `TTRRER` | `2 LEG-STIRRUP` … `7 LEG-STIRRUPS` titles |

### BEAM_REINFORCEMENT (primary)

| Finding | Detail |
|---------|--------|
| **Live DIMENSION callouts** | **24** entities on layer `-STR-RF-DIM`, nesting depth **0** (modelspace) |
| After `\P` strip → parseable callouts | **24/24** |
| Unique cleaned strings | 6 (see below) |
| TEXT/MTEXT MSP callouts | **0** (matches Day-1) |
| Unreferenced block residue | same `A$C01067336` library strings as framing |
| Inserted legend | `TTRRER` → “TYPICAL STIRRUP DETAILS” / N-LEG-STIRRUP titles via INSERT.virtual |

**Unique cleaned DIMENSION callouts (reinforcement DXF):**

| Count | Cleaned string |
|------:|----------------|
| 9 | `2L-Y8@ 100/200/100C/C` (Type3 zoned) |
| 8 | `2L-Y8@ 100C/C` |
| 2 | `2L-Y10@ 100C/C` |
| 2 | `2L-Y8@ 150C/C` |
| 2 | `2L-Y8@ 200C/C` |
| 1 | `2L-Y8@100C/C` (no `\P` / no space) |

**Raw examples (verbatim DIMENSION overrides):**

| Raw string | Entity | Layer | Block | Depth | Approx (x,y) |
|------------|--------|-------|-------|------:|--------------|
| `2L-Y8@\P100C/C` | DIMENSION | `-STR-RF-DIM` | modelspace | 0 | e.g. (21601, 16743) |
| `2L-Y8@\P100/200/100C/C` | DIMENSION | `-STR-RF-DIM` | modelspace | 0 | e.g. (16294, 13124) |
| `2L-Y10@\P100C/C` | DIMENSION | `-STR-RF-DIM` | modelspace | 0 | e.g. (9654, 19947) |
| `2L-Y8@100C/C` | DIMENSION | `-STR-RF-DIM` | modelspace | 0 | (26912, 13346) |

Full hit lists (all drawings, all entity types) are in `day1_set1_stirrup_rawtext_addendum.json`.

### Why R.1 misses them

```171:172:Version9/src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py
            if entity.dxftype() not in ("TEXT", "MTEXT"):
                continue
```

- DIMENSION overrides are skipped entirely.
- `strip_mtext` already handles `\P` (`dxf_text_utils.py` ~L8/L19) — once DIMENSION text is collected, existing cleaning + `_RE_STIRRUP` should parse `2L-Y8@\P100C/C` → `2L-Y8@ 100C/C`.
- Secondary (smaller): INSERT.virtual_entities not collected — irrelevant for Set 1 beam callouts (they are already MSP DIMENSION).

---

## Step 3 — Spatial cross-check (GT stirrup beams)

GT: **23 stirrup rows** across **18 beams** (B1–B18).

For **every** GT stirrup beam, at least one parseable DIMENSION callout lies within the R.1 detail radius (8000) of the beam centroid:

| Beam | Callout dim within radius? | Nearest dist | Nearest cleaned callout |
|------|---------------------------|-------------:|-------------------------|
| B1 | YES | 3245.6 | `2L-Y10@ 100C/C` |
| B2 | YES | 3284.8 | `2L-Y10@ 100C/C` |
| B3 | YES | 1022.4 | `2L-Y8@ 100C/C` |
| B4 | YES | 3129.5 | `2L-Y8@ 100C/C` |
| B5 | YES | 3308.5 | `2L-Y8@ 100/200/100C/C` |
| B6 | YES | 1418.5 | `2L-Y8@ 150C/C` |
| B7 | YES | 495.5 | `2L-Y10@ 100C/C` |
| B8 | YES | 1500.1 | `2L-Y8@ 100C/C` |
| B9 | YES | 1945.6 | `2L-Y8@ 100C/C` |
| B10 | YES | 2171.4 | `2L-Y8@ 100C/C` |
| B11 | YES | 1479.7 | `2L-Y8@ 200C/C` |
| B12 | YES | 1978.2 | `2L-Y8@ 100/200/100C/C` |
| B13 | YES | 1953.7 | `2L-Y8@ 100/200/100C/C` |
| B14 | YES | 1496.9 | `2L-Y8@100C/C` |
| B15 | YES | 2392.1 | `2L-Y8@ 100C/C` |
| B16 | YES | 2431.5 | `2L-Y8@ 150C/C` |
| B17 | YES | 1362.3 | `2L-Y8@ 200C/C` |
| B18 | YES | 1204.5 | `2L-Y8@ 100C/C` |

**Detail-zone text that *is* already in R.1:** longitudinal bars (`2-Y16`, `2-Y20`, …) and SFR notes — confirming the segmenter reaches the beam region; only the stirrup channel (DIMENSION) is missing.

Focused nearest-text samples (B1 / B9 / B10):

- **B1:** mark `B1(200X600)` + `2-Y12` / `2-Y20` / `2-Y16`; nearest stirrup DIMENSION `2L-Y10@\P100C/C` at ~3246.
- **B9:** mark + `2-Y16`; stirrup DIMENSION `2L-Y8@\P100C/C` at ~1946 (well inside detail).
- **B10:** mark + SFR `4-Y8…`; stirrup DIMENSION `2L-Y8@\P100C/C` at ~2171.

---

## Step 4 — Verdict classification

| Option | Result |
|--------|--------|
| A. TRUE ABSENCE | **Rejected** — 24 live DIMENSION callouts; all 18 GT beams have one nearby |
| **B. EXISTS BUT UNREACHED** | **Accepted** — entity type DIMENSION / layer `-STR-RF-DIM` / MSP depth 0; R.1 scans only TEXT/MTEXT |
| C. MIXED | **Rejected** — no GT stirrup beam lacked a nearby callout after DIMENSION+`\\P` strip |

### Recommended discovery patch (NOT implemented — diagnosis only)

| Item | Scope |
|------|--------|
| Where | `Version9/src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py` → `_collect_entities` (~L168–190); mirror in `beam_detail_segmenter._legacy_segment` if still used |
| What | Also accept entities where `"DIMENSION" in dxftype()`; read `entity.dxf.text` when not `<>` / empty; run existing `strip_mtext`; use dimension text position / defpoint for (x,y) |
| Format | Rely on existing `strip_mtext` for `\P`; optional: collapse whitespace before `_RE_STIRRUP` |
| Nesting | Depth 0 MSP is sufficient for Set 1; INSERT explode remains a separate optional Sets 2/3 micro-fix |
| Effort | **~1–2 days** (TEXT/RULE FIX), plus QA.2A re-run on Set 1 |
| Expected Set 1 impact | Surfaces ~24 stirrup annotations into R.1; should cover all 18 GT stirrup beams’ primary callouts (qty/zone math still downstream) |

**Track 1 implication for Set 1:** do **not** default Set 1 to pure-geometry recovery first. Land the DIMENSION collector, re-measure Set 1 STIRRUP missing, then use Track 1 for residual / confirmation / Sets 2–3 text-sparse beams.

---

## Integrity

- NO pipeline code modified
- NO config modified
- NO production artefacts rewritten
- NO stages re-run
- Raw DXF read directly with ezdxf (independent of R.1)
- Script: `Version9/data/output/QA2A_GroundTruthBenchmark/day1_set1_stirrup_rawtext_addendum.py`
- Machine-readable dump: `day1_set1_stirrup_rawtext_addendum.json` (raw sweep; verdict narrative in this `.md` is authoritative after DIMENSION/`\\P` reclassification)
