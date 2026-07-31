# Steel Beam Estimator — Version 9 Accuracy Context Knowledge
**Purpose of this document:** Compiled context from the brainstorming chat (Claude) for use in the prompt-generation and validation chats. Contains project state, benchmark findings, root-cause analysis, agreed architecture, frozen specs, and open items.
**Date compiled:** 2026-07-31

---

## 1. Project overview

- **Project:** SteelBeamEstimator — reads DXF drawings (General Notes + Framing Plan + Reinforcement Plan) and produces beam-wise steel quantity estimates (KG/MT) in an Excel output matching estimator manual sheets.
- **Repo:** `C:\Users\nishanth.h\SteelBeamEstimator` / github.com/NishanthHanumantha/SteelBeamEstimator
- **Versions:** Version8 is FROZEN and certified (MODEL_VERSION 8.9.5, tag v8.9.5) — do not modify. Version9 is the active accuracy-development branch, forked from V8.
- **Tooling workflow:** Cursor Pro for development (Grok 4.5 for most tasks, Sonnet 4.6 for hard interpretation tasks). Claude (this account) for: brainstorming (chat 1), prompt generation (chat 2), output validation (chat 3).
- **Pipeline stages (production spine):** V.ROOT.1 (beam registry) → R.1 (reinforcement annotation discovery) → R.2A (engineering context: Ld, cover, grades from General Notes) → R.2.1B → R.2.1C → R.2.1D (Evidence & Hypothesis engine) → L.2.2 (geometry registry) → R.3 (geometry context) → R.3.1 (drawing relationships) → R.1.2A (geometry catalog) → R.1.3 (EngineeringBarModel integration / piece generation) → V.B.1 (steel/BBS/Excel output).
- Runners live in `Version9/Run_PY/`, packages in `Version9/src/PhaseXXX/`, run-context via `STEEL_ENGINE_ROOT` / `STEEL_RUN_ROOT` / `STEEL_OUTPUT_ROOT`, soft-exit semantics throughout.
- **Notation rules (Requirement_Rules.txt):** Type1 `2Y-16` = 2 bars Ø16. Type2 `2L-Y10@100C/C` = 2-leg stirrups Ø10 @100mm. Type3 `2L-Y8@100/200/100C/C` = zoned stirrup spacing (equal thirds if lengths not shown). Type4 = dimension callouts on beams (e.g. `2150` = top-extra clear length; `500` = deduction from bottom clear length to get bottom-extra length).
- **Bar roles:** TOP_MAIN, TOP_EXTRA, BOTTOM_MAIN, BOTTOM_EXTRA, STIRRUP, STIRRUP_HOOK (derived), SIDE_FACE_REINFORCEMENT (SFR), SPACER_BAR (computed, never drawn).
- **Key formulas:** Cutting Length = Clear Length + Development Length + Bend Correction; Bend Correction = 2×dia(mm)/1000; Steel KG = Total Length × Unit Weight(dia).

## 2. QA.2A Ground-truth benchmark results (MODEL_VERSION 8.9.1, 3 drawing sets, 148 beams, 937 GT bars)

| Metric | Value |
|---|---|
| Beam detection | 93.92% (139/148) |
| Bar detection | 41.52% (389/937) |
| Bar matching accuracy | 24.16% (94 correct) |
| Steel KG accuracy | 72.69% |
| Overall | 58.07% |
| Total errors | 993 |

Per set: Set1 100% beam det / 41.9% bar acc / 70.1% steel; Set2 95.5% / 27.5% / 79.3%; Set3 90.5% / 16.6% / 68.7%.

**Error frequency:** Missing Bar 548, Wrong Diameter 176, Extra Bar 159, Wrong Role 58, Wrong Quantity 36, Beam Missing 9, Beam Mismatch 4, Steel Difference 3.

**Role × status matrix (from detailed Excel, all sets):**

| Role | Missing | Wrong Dia | Extra | Match | Partial | Wrong Qty | Wrong Role |
|---|---|---|---|---|---|---|---|
| STIRRUP | 182 | 2 | 1 | 2 | 12 | 11 | 0 |
| STIRRUP_HOOK | 81 | 0 | 0 | 0 | 2 | 0 | 0 |
| SPACER_BAR | 98 | 9 | 3 | 0 | 1 | 0 | 0 |
| BOTTOM_MAIN | 89 | 62 | 0 | 9 | 1 | 14 | 20 |
| TOP_MAIN | 36 | 75 | 0 | 55 | 4 | 5 | 18 |
| TOP_EXTRA | 22 | 24 | 114 | 27 | 3 | 5 | 3 |
| BOTTOM_EXTRA | 15 | 4 | 40 | 1 | 0 | 1 | 14 |
| SFR | 16 | 0 | 0 | 0 | 2 | 0 | 3 |

**Diameter evidence:** Y10 is 98–99% missing on Sets 2/3 (2202 GT vs 32 model on Set3); Y8 72–97% missing; Y25 82–100% missing (spacers). Y16/Y20 aggregate quantities within 2.5–6.5% of GT.

## 3. Root-cause analysis (agreed diagnosis)

**Key reframe: main-bar text READING is essentially solved (Y16/Y20 near-parity). The losses are placement/association and derived-piece computation, not text recognition.**

- **RC-1 Stirrups + hooks (~263 missing rows, ~6,700 pieces Y8/Y10/Y12):** biggest KG loss. Annotations exist as text; failure is discovery/association and/or piece generation. STIRRUP_HOOK derivation is NOT IMPLEMENTED AT ALL (0 hooks even for the ~27 beams whose stirrups reach output).
- **RC-2 Spacer bars (98/98 missing, ~436 pieces Y25):** spacers are never drawn — pure rule computation gap. No CV can help. Cheapest big win.
- **RC-3 Main-bar diameter swaps (137/176 wrong-dia are TOP_MAIN/BOTTOM_MAIN with qty correct):** systematic mis-association — right annotation count, wrong beam face (top↔bottom swap or section-vs-elevation confusion). Spatial judgment problem.
- **RC-4 Extra over-generation (114 TOP_EXTRA + 40 BOTTOM_EXTRA phantom rows, est_qty=0):** duplication across views/spans or main-bars demoted to extras. Dedup/placement problem.

Cursor validated RC-1 against raw bar_matching.json (Set1): B1/B9/B10 stirrups reached output but misclassified (TOP_EXTRA/SPACER_BAR, qty=4 vs GT 57/31/40); other 15 beams fully MISSING.

## 4. Agreed architecture principle

Deterministic V8 spine stays **authoritative and reproducible**. OpenCV and Vision LLM enter as **evidence providers** feeding R.2.1D (Evidence & Hypothesis) and R.3.1 — never mutating `beam_reinforcement_models_production.json` directly. All new stages additive, config-flagged, soft-exit. VLM verdicts logged (tile hash + JSON) and disagreements feed R.1.5/R.1.6 so the rule engine absorbs VLM judgments over time (VLM reliance shrinks).

**Deferred:** OCR (inputs are native DXF text; revisit only for exploded SHX/raster underlays). YOLO (needs labeled raster data; poor ROI on vector inputs; if ever needed, auto-label from validated pipeline output projected onto rendered tiles).

## 5. Track plan (agreed, with corrections)

### Track 0 — Deterministic fixes (first)
- **T0.1 Spacer rule engine** — frozen spec in §7. Target: 98 missing → ~0.
- **T0.2a Stirrup hook generation NOW** for the ~27 beams whose stirrups already reach output (rule not implemented at all; no dependency on Track 1). Hook length from General Notes anchorage table via R.2A context. **T0.2b:** remaining hooks flow automatically as Track 1 recovers parent stirrups.
- **T0.3 Diameter sanity gate:** if the same source annotation is claimed by both TOP and BOTTOM faces, or one face empty while the other has 2 candidates → raise `FACE_CONFLICT` hypothesis instead of committing silently. Guard rail feeding Track 2.

### Track 1 — Stirrup recovery (OpenCV / vector geometry)
- **T1.1 Renderer:** Phase M.1 (`PhaseM.1_engineering_vision_dataset`) already contains dxf_renderer.py (ezdxf+matplotlib), beam_cropper.py, CoordTransform, dataset_exporter — promote to shared rendering infra. **Validate first (half-day):** (a) CoordTransform round-trip exact at tile EDGES; (b) all layers containing stirrup ticks included (dataset renderers may filter layers); (c) line weights ≥1px at chosen scale; (d) text rendering toggleable (OFF for CV path, ON for VLM tiles).
- **T1.2 Stirrup detector — vector-space FIRST:** query DXF entities (closed LWPOLYLINE rectangles in sections; evenly-spaced short vertical LINE tick trains in elevations — measured tick pitch independently cross-checks parsed `@spacing`). OpenCV raster fallback (findContours/minAreaRect, Hough clustering) only when geometry exploded/blocked. Output `stirrup_geometry_evidence.json` per beam.
- **T1.3 Fusion in R.2.1D:** new evidence type GEOMETRY_STIRRUP. Text+geometry agree → HIGH commit. Text only → commit WARN (current behavior). Geometry only → SYNTHESIZE stirrup hypothesis (dia from nearest text or GN minimum), flag for VLM confirmation.
- **T1.4 Type3 zones:** place 100/200/100 boundaries from measured tick-pitch changes / SupportLocations.json instead of equal-thirds fallback.

### Track 2 — Vision LLM arbiter (narrow, flagged beams only, ≤30%)
Three constrained structured questions only: **T2.1** face assignment per numbered annotation (TOP/BOTTOM/SIDE/SECTION, JSON) for FACE_CONFLICT beams → fixes RC-3. **T2.2** full-span main vs curtailed extra + cross-view duplicate detection → fixes RC-4. **T2.3** orphan stirrup confirmation for Track 1 synthesized hypotheses. JSON-schema validated, one retry, deterministic fallback offline. Config flag `enable_vision_arbiter`. Cost negligible (~$1–1.50/full QA run).
**Models:** test `claude-sonnet-4-6` (default) vs `claude-haiku-4-5` on 10 hand-picked WRONG_DIAMETER beams; pick on measured face-assignment agreement. Extended thinking unnecessary. (Older names like claude-3-5-sonnet are outdated — do not use.)

### Track 3 — Measurement
QA.2A as one-command regression gate after every landing; store role×status matrix per run; attribute each accuracy point to a change. V9.0.0 done = overall ≥80% Sets 1–2, ≥72% Set 3, no beam-detection regression. Targets: bar detection ≥85%, bar match ≥70%, steel KG ≥92%.

## 6. Day-1 stirrup diagnostic (HIGHEST-LEVERAGE OPEN ITEM — gates Track 1 design)

Read-only, ~1 hour: regex-scan R.1 output `reinforcement_annotations.json` for `\dL-Y\d+@` per drawing set; compare counts vs GT stirrup rows. Then trace 5–10 specific missing-stirrup beams through R.1.1A → R.3.1.

| Outcome | Meaning | Fix class |
|---|---|---|
| Count ≈ GT | Discovery fine; loss in association (R.3.1/R.1.1A) | Track 1 geometric evidence correct |
| Count ≪ GT | Loss at discovery (layers/MTEXT/R.2.0) | Track 0-class text fix, NO CV |
| Count ≈ GT, wrong role | Role classifier misfiring | Classifier rule fix |

Set1 partial-matches hint at outcome 1 or 3, but all-3-set counts are the definitive answer. If outcome 2, Track 1 shrinks from a 4-week CV effort to a ~1-week rule fix. Run in parallel with T0.1.

## 7. FROZEN SPEC — T0.1 Spacer Bar Engine (estimation-team clarified)

**Estimation-team ruling (SpacerBar_Computation doc):** spacer interpretation is HARDCODED, an exceptional case, NOT derived from general notes. Triggers where ≥2 longitudinal bars come together in the SAME face (top+top_extra; two tops; bottom+bottom_extra; two bottoms). No spacer when a face has only one bar layer. **Note2:** estimator GT sheets may have MISSED spacers on some beams — the rule OVERRIDES the GT; model-only spacers are correct.

**Constants (hardcoded):** `SPACER_DIA_MM = 25`, `SPACER_SPACING_MM = 1000`. Only context input: `cover_mm` = beam clear cover from R.2A EngineeringContext (General Notes Table 2, beam clear cover; R.2A field `cover_beam_mm`).

**Resolved ambiguities (user-confirmed):** (a) rounding = **ceil**; (b) overlap length = **only the lap region where extra overlaps main** (intersection of extents), not the extra's full length; (c) cut = width − 2×cover confirmed (250 − 2×50 = 150 → GT 0.15 m ✓); (d) cover = GN Table2 beam clear cover.

**Algorithm:**
```
for each beam:
  for each face in {TOP, BOTTOM} independently:
    groups = longitudinal bar groups on face (MAIN + EXTRA only;
             exclude STIRRUP, SFR, SPACER, UNKNOWN)
    if len(groups) < 2 → no spacers on this face
    compute each group's longitudinal extent [start, end] along beam axis
    zones = maximal intervals where ≥2 groups coexist (interval intersection/merge;
            3 bars stacked = still ONE zone over the union where ≥2 coexist)
    for each zone:
        N = ceil(zone_length_mm / 1000) + 1
        emit SPACER_BAR: dia=25, qty=N,
             cut_length_mm = beam_width_mm − 2 × cover_mm
```
Each zone emits its own row (GT B4 has two rows). Engine purely additive — must not modify existing bar groups.

**Extent fallback (will fire often until Track 2 lands):** if an extra's extent is missing/low-confidence (no Type4 dimension associated), fall back to zone_length = extra bar's clear length with a WARN flag — never silently skip, never crash.

**Unit test vectors (hand-computed from GT):**
- B2: one zone 4000 → qty 5, cut 0.15 m
- B4: zones 3000 & 7000 → qty 4 & qty 8, cut 0.15 m each
- Ceil: 2150 → qty 4; exact multiple 3000 → qty 4 (ceil of exact doesn't bump)
- Single-bar face → 0; main-only face → 0; stirrups/SFR present with one longitudinal group → 0
- Three stacked bars with intersecting extents → ONE zone (no double-emit)
- Cut: width 250, cover 50 → 150 mm; assert cover from R.2A and dia/spacing NOT from context

**Module shape:** self-contained `PhaseV9_spacer_rule/spacer_engine.py` with unit tests, invoked from Version9's R.1.3 behind config flag `enable_spacer_rule`. No new pipeline stage/runner.

**QA.2A amendment (must ship with T0.1 — Cursor will omit unless told):** model-emits-spacer / GT-has-none → classify `ACCEPTABLE_EXTRA`, excluded from Extra Bar penalty, reported in its own column for estimator review. GT-has / model-missing spacer remains a real error.

**Acceptance:** SPACER_BAR missing 98 → ~0 across 3 sets; Y25 diff% <15; all other roles unchanged (purely additive); unit tests green before integration.

## 8. Immediate sequence

1. Generate Cursor implementation prompt for T0.1 (spec §7 + extent-fallback risk + QA carve-out) in prompt-generation chat; run in Cursor.
2. Validate Cursor output: constants truly hardcoded; cover truly from R.2A; per-zone interval intersection (not per-beam); ACCEPTABLE_EXTRA implemented in QA; unit tests match §7 vectors.
3. QA.2A regression on all 3 sets → acceptance criteria.
4. In parallel: Day-1 stirrup diagnostic (§6) — its outcome gates all Track 1 design.
5. Then T0.2a hook generation (week 2), T0.3 face-conflict gate, M.1 renderer validation checklist, T1.2 vector stirrup query, Track 2.

## 9. Standing conventions for all prompts to Cursor

- Never modify frozen Version8; all work in Version9.
- New logic behind config flags; purely additive to production model; soft-exit + artefact-presence semantics like existing runners.
- Every change followed by QA.2A regression on all 3 benchmark sets; compare role×status matrix to §2 baseline.
- Deterministic engine remains authoritative; CV/VLM are evidence into R.2.1D hypotheses only.
- Read-only diagnostics must not touch pipeline code or artefacts.
