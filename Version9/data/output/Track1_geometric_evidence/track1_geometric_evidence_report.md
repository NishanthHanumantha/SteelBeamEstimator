# Track 1 — Geometric Stirrup Evidence Engine (9.3.0)

**Status:** Implemented (residual-scoped). QA.2A re-run complete.  
**MODEL_VERSION:** 9.3.0 (proposed MINOR bump from 9.2.0)  
**Config flag:** `enable_geometry_stirrup_evidence` (default `true`) in `Version9/config/geometric_stirrup_evidence.yaml`

---

## 1. Residual target list

**File:** `Version9/data/output/Track1_geometric_evidence/residual_target_beams.json`

| Group | Count | Notes |
|-------|------:|-------|
| TARGET_MISSING | **73** | Exact vs 9.2.0 QA.2A |
| TARGET_WRONG_QTY | **99** | 100 minus Set1 B3/B18 duplicate-grain artifacts |
| Unique beams | 115 | |

**Exclusions (documented in JSON):**
- **B3/B18:** identical duplicate uniform callouts — not Type3 zone-thirds candidates
- **B6:** MATCH+EXTRA zone-grain; not WRONG_QTY
- **B7:** kept — Type3 second callout may need zone refinement

Source QA.2A runs: `qa2_*_20260801_103357/103505/103630`.

---

## 2. T1.1 Renderer validation

**PASS** all four checks (artefact: `t1_1_renderer_validation.json`).

| Check | Result | Detail |
|-------|--------|--------|
| (a) Coord round-trip | PASS | max error **0.0 mm** (tol 1e-6 documented; practical 0.001) |
| (b) Layer completeness | PASS | Full modelspace render; `-STR-RF-DIM`, `-S-STIRUP` present. `S- Structural` absent on sampled DXF (not dropped by filter) |
| (c) Line weight | PASS | 30×22 in @ 200 dpi; min ink run ≥1 px; median thin run 3 px |
| (d) Text toggle | PASS | `render_text=False` → 0 text ink; True → text present |

Unplanned renderer fixes in `PhaseM.1/.../dxf_renderer.py`: `render_text`, layer include/exclude, DPI, float-safe CoordTransform.

---

## 3. T1.2 Detector

**Primary:** vector elevation tick trains (DXF LINE entities).  
**Secondary:** OpenCV fallback (soft-skip if OpenCV not installed).

**Thresholds (R2):** `min_tick_count≥3`, pitch **50–400 mm**, `pitch_cv_max=0.35`, fusion requires `confidence≥0.55`.

**Typical acceptance (latest runs):** Set1 ~1 accepted; Set2/3 ~16 each. Many residual MISSING beams have no recoverable tick geometry (legend/typical-detail).

**Sample output:** per-run `PhaseT1_geometric_stirrup_evidence/stirrup_geometry_evidence.json`.

---

## 4. T1.3 Fusion (`GEOMETRY_STIRRUP`)

Additive hook in `PhaseR2.1D` → `t1_geometry_fusion_summary.json` (mkdir-before-write fix).

| Case | Behavior |
|------|----------|
| TEXT+GEOMETRY AGREE | Annotate `GEOMETRY_TEXT_AGREE`, HIGH |
| TEXT only / weak geometry | Unchanged WARN text path |
| GEOMETRY only (TARGET_MISSING) | Synthesize `SYNTH:…` fact, confidence **WARN**, flags `SYNTHESIZED_GEOMETRY\|GEOMETRY_ONLY` |
| TEXT+GEOMETRY DISAGREE (conf≥0.55) | `GEOMETRY_TEXT_CONFLICT` — both values logged |

**Latest fusion (122/124 runs):** Set1 text_only=13; Set2 agree=1 synth=1; Set3 agree=5 conflict=1 synth=1.

**Known gap (R3):** synthesized facts appear in R.2.1D `EngineeringFacts.json` but often do **not** reach L2/Excel/QA `SYNTHESIZED_GEOMETRY` column (downstream intent→bar path drops `source=GEOMETRY_STIRRUP` / WARN). Flag propagation is wired in R13 builder + QA matcher + SI.1 Description `[SYNTHESIZED_GEOMETRY]` when label starts with `SYNTH:` — end-to-end visibility still incomplete until that drop is fixed. Track 2 can also confirm these hypotheses via VLM.

---

## 5. T1.4 Type3 zone refinement

**Architecture (after steel-regression fix):**
1. R.1.2D zone interpreter restored to **9.2.0 / V8 path** (no Type3 multi-intent segment expansion — that double-counted through R.1.3 + SI.1).
2. **SI.1** owns Type3 quantities: residual `TARGET_WRONG_QTY` only, repair truncated `2L-Y8@100` → `@100/200/100` from R.1 `clean_text` when first spacing matches.
3. Zone lengths: SI.1 equal-N default; **T1.4 pitch_change** boundaries override when T1.2 stores `zone_refinement.method=pitch_change`.

---

## 6. QA.2A — 9.2.0 vs 9.3.0 (latest: `qa2_*_20260801_124700/747/856`)

### Overall metrics

| Metric | 9.2.0 | 9.3.0 (latest) | Δ |
|--------|------:|---------------:|--:|
| Overall accuracy % | 67.97 | **70.23** | +2.26 |
| Bar detection % | 61.37 | **68.52** | +7.15 |
| Bar accuracy % | 25.04 | **27.41** | +2.37 |
| Steel KG accuracy % | 91.57 | **91.07** | −0.50 |
| Beam detection % | — | 93.92 | — |

### STIRRUP role × status

| Set | Status | 9.2.0 | 9.3.0 | Notes |
|-----|--------|------:|------:|-------|
| Set1 | MISSING | 5 | **0** | −100% |
| Set1 | WRONG_QTY | 15 | 16 | ≈flat |
| Set1 | MATCH | — | 6 | |
| Set1 | EXTRA | — | 12 | Type3 zone grain / duplicate bars |
| Set2 | MISSING | 27 | **9** | −67% |
| Set2 | WRONG_QTY | 45 | 41 | −4 |
| Set3 | MISSING | 41 | **22** | −46% |
| Set3 | WRONG_QTY | 41 | 56 | ↑ (zone-grain mismatch) |

**MISSING total:** 73 → **31** (−**57.5%**) — meets ≥50% first milestone.  
**WRONG_QTY total:** 100 → **113** — not improved overall (Set3 zone-grain / EXTRA tradeoff).  
**SYNTHESIZED_GEOMETRY column:** wired in QA.2A matrix/exporter; populated count **0** in Excel rows (see R3 gap).

### Non-STIRRUP / steel

- Overall and bar metrics improved vs 9.2.0.
- Steel −0.5 pp (Set1 improved; Set2/Set3 still soft vs 9.2.0 Set3 ~98.9%).
- Full non-STIRRUP role×status byte-diff vs 9.2.0 production not re-proven in this pass (R4) — flag-off (R6) recommended before merge.

---

## 7. Risk checks (R1–R6)

| ID | Result |
|----|--------|
| R1 Renderer gate | PASS — no stop |
| R2 False-positive geometry | Thresholds above; weak conf (&lt;0.55) treated as text-only |
| R3 Synth confidence | WARN + flags at R.2.1D; **Excel visibility incomplete** (blocking gap for “visible in final output”) |
| R4 Scope leakage | Residual gates on fusion + Type3 repair; R12D Type3 expansion removed. Formal non-residual byte-identity not re-run this pass |
| R5 Performance | T1+pipeline avg ~56–140 s/set; within &lt;2× prior R.1.2A-stage bound for QA runs |
| R6 Flag-off | Soft-exit implemented (T1 writes empty artefact; R.2.1D skips fusion; Type3 repair checks flag). **Full 3-set flag-off ≡ 9.2.0 not re-executed this pass** |

---

## 8. Config flag

```yaml
# Version9/config/geometric_stirrup_evidence.yaml
enable_geometry_stirrup_evidence: true   # false → T1 no-op, no fusion, no Type3 repair
```

---

## 9. Files added / modified

**Added**
- `Version9/src/PhaseT1_geometric_stirrup_evidence/` (package: detector, fusion, zone refiner, renderer validation, orchestrator, type3_label_repair, …)
- `Version9/Run_PY/run_phase_t1_geometric_stirrup_evidence.py`
- `Version9/config/geometric_stirrup_evidence.yaml`
- `Version9/data/output/Track1_geometric_evidence/residual_target_beams.json`
- This report + T1.1 validation artefacts

**Modified**
- `PhaseM.1_.../dxf_renderer.py` — text toggle / layers / CoordTransform
- `PhaseR2.1D_.../phase_r21d_orchestrator.py` — T1.3 fusion + summary mkdir
- `PhaseR1_2D_.../stirrup_zone_interpreter.py` — restored 9.2.0 path (no Type3 multi-expand)
- `PhaseSI.1_.../phase_si1_orchestrator.py` + `stirrup_zone_builder.py` — Type3 repair + T1.4 bounds
- `PhaseR1.3_.../engineering_bar_builder.py` — SYNTH / WARN evidence on L2 bars
- `PhaseQA.2A_.../bar_matcher.py`, `excel_exporter.py` — SYNTHESIZED_GEOMETRY column
- `PhaseQA.2_.../pipeline_runner.py`, `webapp/config.py` — T1 stage after R1

**Not touched:** Version8, 9.2.0 DIMENSION discovery patch, M.2 spacer engine, role classifiers.

---

## 10. MODEL_VERSION

Engine artefacts and T1 package use **9.3.0**. QA.2A runner banner may still print 9.1.0 (cosmetic — update when committing).

---

## 11. Suggested git commit message

```
feat(Version9): 9.3.0 Track 1 geometric stirrup evidence (residual-scoped)

Add vector tick detection + R.2.1D GEOMETRY_STIRRUP fusion, SI.1 Type3
label repair for WRONG_QTY residuals, T1.4 pitch-change zone bounds, and
QA.2A SYNTHESIZED_GEOMETRY visibility. Config-flagged soft-exit.
```

*(Do not commit until explicitly requested.)*

---

## 12. Known limitations → Track 2 scope

1. **No recoverable ticks** on many MISSING beams (typical-detail / legend) — geometry acceptance sparse; needs VLM.
2. **GEOMETRY_ONLY synth** facts often stop at R.2.1D — not yet in production Excel/QA column.
3. **TEXT+GEOMETRY CONFLICT** rare but present (e.g. pitch 50 vs text 200) — do not auto-pick; VLM arbiter.
4. **Type3 equal-N vs estimator zone grain** → Set3 WRONG_QTY/EXTRA can worsen even when MISSING falls.
5. **OpenCV fallback** inactive if `opencv-python` not installed.
6. **R4/R6 formal proofs** should be re-run before treating 9.3.0 as merge-ready.

---

## Fusion case examples (T1.3)

| Case | Example |
|------|---------|
| AGREE | Set2/3 beams with accepted ticks matching DIMENSION `@spacing` within 15 mm |
| TEXT_ONLY | Most Set1 residuals — no accepted tick train |
| GEOMETRY_ONLY_SYNTH | Set2 `B35A`: `SYNTH:2L-Y8@50C/C` WARN in EngineeringFacts (not yet in Excel) |
| CONFLICT | Set3: text spacing ≠ measured pitch (conf≥0.55) → `GEOMETRY_TEXT_CONFLICT` |
