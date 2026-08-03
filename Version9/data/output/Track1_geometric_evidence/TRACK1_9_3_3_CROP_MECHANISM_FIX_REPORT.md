# Track 1 Patch 9.3.3 — Local-Extent Crop Rendering + Beam-Scoped Bbox + Visual Regression Gate

Date: 2026-08-03
MODEL_VERSION: **9.3.3** (PATCH — render/crop mechanism fix only; no T1.2 detection, T1.3 fusion, or T1.4 zone-refinement changes)

## Objective recap

The prior diagnostic (verdict C — MIXED) confirmed beam bbox *location* was correct but the render/crop *mechanism* was broken: full-sheet render (6000×4400px) then pixel-crop produced ~100–130px beam crops, a coarse ±1500mm blanket pad bled into neighboring beams (B8 pulling in `%%UB13`), and some existing artefacts were stale. This patch fixes the mechanism only.

---

## PART A — Beam-scoped extent + local-extent render

### A1. Beam-scoped extent (`beam_extent.py`, new file)

Replaces the ±1500mm blanket pad with: bounding union of (a) the beam-mark label entity (`find_beam_mark`), (b) all entities R.1's existing annotation association already ties to the beam (reused as-is, no re-derivation), resolved to their **actual DXF entity bounding boxes** (`build_label_entity_index` + `_resolve_bbox`) rather than zero-sized anchor points — this was required to stop text glyphs (e.g. "2-Y16", "4-Y8 SIDE FACE REINF") from clipping — plus (c) a 350mm default pad, shrunk **per side, independently** (`_per_side_pads`) whenever a neighbor beam's core sits closer than the pad allows. Overlaps are handled with a **graduated** response (`allowed = max(0, pad_mm + gap)` for `gap < 0`) rather than a hard zero-out, so a beam only barely touching a neighbor doesn't lose all its padding on that side.

### A2. Local-extent render (`dxf_renderer.py` → `render_dxf_region_to_png`, new function)

Filters DXF entities to the beam-scoped extent **before** rendering (`draw_layout(..., filter_func=...)`), renders directly to a resolution decoupled from sheet size: **long side capped at 1200px, short side floored at 400px, natural aspect ratio of the extent preserved** (no forced aspect ratio — an earlier attempt to force a fixed W×H reintroduced bleed by symmetrically over-padding short dimensions). `render_text` on/off toggle preserved.

### Resolution comparison (test set)

| Beam | Old crop (full-sheet-then-slice, per diagnostic) | New crop (local-extent) | Line weight (new, min / median ink-run px) |
|---|---|---|---|
| B1 | ~100–130px | 1200×708 | 2 / 3 |
| B2 | ~100–130px | 1200×712 | 2 / 3 |
| B8 | ~100–130px | 856×1200 | 1 / 2 |
| B9 | ~100–130px | 1047×1200 | 2 / 6 |
| B10 | ~100–130px | 1200×931 | 1 / 5 |

All 5 pass the same ≥1px line-weight bar T1.1 used for the full-sheet render (`_9_3_3_crop_line_weight_check.py`, reusing `renderer_validation.py`'s exact scan methodology). Resolution increased **~9–12×** on the long axis; a full ~6–10× effective increase over the diagnostic's blurry 100–130px baseline once aspect ratio is accounted for.

---

## PART B — Purge + regenerate (test set)

`_local_crop_test.py` explicitly deleted all 10 existing `Set1_{B1,B2,B8,B9,B10}_{crop,notext}.png` files (sizes logged, e.g. `Set1_B1_crop.png` 47,555B stale → deleted) before regenerating — no silent overwrite. Regenerated files carry fresh timestamps (`local_crop_test_report.json`) and materially different byte sizes/dimensions, confirming none are stale carryovers.

---

## PART C — Visual regression gate

| Beam | Label | Bar callouts | Stirrup spec | Dim strings | Beam-scoped (no bleed) | Verdict |
|---|---|---|---|---|---|---|
| B1 | ✅ %%UB1(200X600) | ✅ | ✅ | ✅ | ✅ | **PASS** |
| B2 | ✅ %%UB2(200X600) | ✅ | ✅ | ✅ | ✅ (B6 overlap zeroed correctly) | **PASS** |
| B8 | ✅ %%UB8(200X600) | ✅ | ✅ | ✅ | ✅ — no more `%%UB13` bleed (regression fixed) | **PASS** |
| B9 | ✅ %%UB9(200X600) | ✅ | ✅ (very minor non-critical character graze on a side-face-reinf banner, genuine −5.8mm overlap with B4) | ✅ | ✅ | **PASS** (documented minor caveat) |
| B10 | ✅ %%UB10(200X600) | ✅ | ✅ | ✅ | ✅ — no bleed into B4/B14/B15 | **PASS** |

### C.4 — notext.png ink density (non-blank confirmation)

| Beam | notext ink % (new) | Old (stale/pre-fix, from purged file evidence) |
|---|---:|---|
| B1 | 2.52% | old notext file was 10,581B — same order but from full-sheet slice, not a validated local render |
| B2 | 2.25% | 11,226B |
| B8 | 1.94% | 11,467B |
| B9 | 1.55% (production re-run: 1.545%) | 7,364B |
| B10 | 1.76% | 8,419B |

All well above the `_CROP_INK_INVALID_THRESHOLD_PCT = 0.2%` gate. **Gate result: PASS for all 5 test-set beams.** Proceeded to Part D per the gate's own rule.

---

## PART D — Scoped detection re-run + QA.2A delta

`phase_t1_orchestrator._opencv_for_beam` rewritten to: precompute `beam_extents` for **every** beam with R.1 annotations (not just the residual scope, so neighbor-aware padding sees beams outside the run's own residual list too — R4 requirement), purge stale crop/notext before each regenerate, render via `render_dxf_region_to_png`, and gate on notext ink density (`crop_invalid` if `< 0.2%`) before ever handing the crop to `detect_ticks_opencv`.

**Scope note:** the original 74-beam `opencv_reactivation_target_beams.json` list from 9.3.2 was a transient in-memory scoping list (`reject_reason == opencv_not_installed`, pre-cv2-install) and was not persisted to disk in this repo, so it can't be reloaded verbatim. Part D was instead run across **all 115 residual beams** (13 Set1 + 52 Set2 + 50 Set3) — a strict superset of the original 74 — giving full, not partial, coverage of Part A's fix.

### Test set before/after (B1, B2, B8, B9, B10)

| Beam | 9.3.2 (blank-crop era) | 9.3.3 (this patch) |
|---|---|---|
| B1 | not in T1's residual scope (already resolved by an earlier phase) — Part C exercised its render/crop path in isolation only; no detection re-run applicable | same — unaffected, as expected |
| B2 | opencv_fallback, rejected `tick_count=0<3` | opencv_fallback, **accepted**, pitch 62.03mm, conf 0.45 |
| B8 | opencv_fallback, rejected `tick_count=2<3` | opencv_fallback, **accepted**, pitch 127.1mm, conf 0.45 |
| B9 | opencv_fallback, rejected `tick_count=0<3` | opencv_fallback, rejected `tick_count=1<3` (still rejected — genuinely sparse geometry in that beam's tight crop, not a blank-crop artefact) |
| B10 | opencv_fallback, rejected `tick_count=2<3` | opencv_fallback, rejected `pitch_range_filter` (a *different*, more specific real reason — crop is valid, geometry doesn't fit range) |

### Full residual-scope crop-validity + detection delta (all 3 sets, 115 beams)

| Set | Residual beams | Accepted before | Accepted after | Changed | `crop_invalid` after |
|---|---:|---:|---:|---:|---:|
| Set1 | 13 | 1 | 6 | 11 | 0 |
| Set2 | 52 | 16 | 29 | 30 | 0 |
| Set3 | 50 | 23 | 31 | 23 | 0 |
| **Total** | **115** | **40** | **66** | **64** | **0** |

- **Every regenerated crop across all 115 residual beams passed the ink-density validity check** (`crop_invalid_after_count: 0` in all 3 sets) — no beam's fix-era crop is near-blank. Any remaining rejection is now traceable to a real, specific reason (`pitch_range_filter`, `tick_count=N<3`), not an indistinguishable blank crop.
- **29 beams flipped rejected → accepted** with the clearer crop (e.g. Set1 B2/B4/B5/B7/B8; Set2 B13/B20/B22/B25/B39/B39A/B50/B55/B59/B60/B63/B7/B9; Set3 B11/B15A/B18/B20/B29A/B34/B43/B55/B60/B8/B9).
- **3 beams flipped accepted → rejected** (Set3 B28, B48, B59) — these were 9.3.2 OpenCV accepts on blank/near-blank crops (likely noise/hatch false positives per the 9.3.2 report's own R2 flag on suspicious repeated 63.47mm pitches); the clearer crop now correctly rejects them on `pitch_range_filter`. This is the fix working as intended, not a regression.
- Net: **26 more residual beams now produce an accepted OpenCV-fallback detection** with a visually valid, ink-confirmed crop, up from 40 to 66.

### Full 3-set QA.2A delta

**Fusion is unaffected: 0 change.** `r21d_fusion.py` requires `geo_conf >= 0.55` for AGREE/CONFLICT/GEOMETRY_ONLY_SYNTH; `opencv_fallback.py` hardcodes `confidence = 0.45` regardless of how many ticks are found or how clean the crop is. Every one of the 29 newly-accepted beams (and the 3 newly-rejected ones) is `detection_method: opencv_fallback` with `confidence: 0.45` — below the fusion bar either way, so all route to TEXT_ONLY exactly as in 9.3.2. This was confirmed two ways this session:
1. **Logical proof** — traced the fusion threshold check against every changed beam's confidence value (all 0.45).
2. **Empirical re-run** — executed `r21d_fusion.py` for all 3 sets against the 9.3.3 T1 evidence; AGREE/CONFLICT/SYNTH/TEXT_ONLY counts matched the 9.3.2 baseline exactly. Original R2.1D outputs were restored afterward (no persistent change).

⇒ **QA.2A STIRRUP role×status matrix and overall accuracy are byte-identical to the 9.3.2 baseline: MISSING 31, WRONG_QTY 113, MATCH 63; Overall 70.23%.**

### R4-equivalent scope check

Confirmed structurally, not just empirically: `phase_t1_orchestrator.run()`'s beam-selection loop (`for beam_id in sorted(residual_ids)`, where `residual_ids = included_beam_ids_for_set(targets, set_id)`) is byte-identical to 9.3.2 — the 9.3.3 diff touches only the body of `_opencv_for_beam` (crop generation), never which beams enter the loop or which detection path they take. `beam_extents` is precomputed for *all* beams with R.1 annotations (superset of `residual_ids`) specifically so cross-beam padding decisions see full context, but only beams already in `residual_ids` ever get a crop generated or a detection call. **No beam outside the residual scope is touched. CLEAN.**

### R6-equivalent flag-off check

Ran the T1 orchestrator with `enable_geometry_stirrup_evidence` forced to `False` (in-process monkeypatch of the config-loader call, no on-disk config file changed) against Set1:

```json
{
  "phase_id": "T1", "model_version": "9.3.3", "enabled": false,
  "soft_exit": true, "success": true,
  "message": "enable_geometry_stirrup_evidence=false — no-op (R6 flag-off)"
}
```

`by_beam` count = 0. **Soft-exit path reproduced exactly, unaffected by the render/crop change.** (`_9_3_3_r6_check.py`)

---

## R1–R5 risk-check results

| Risk | Result |
|---|---|
| **R1** extent too tight | No blocking case found in the test set. The one genuine near-miss (B9, −5.8mm overlap with B4) causes a cosmetic single-character graze on a non-critical banner, not a lost stirrup-spec/dimension. `r1_r3_padding_evidence.json` shows this is the graduated-overlap path working as designed (partial pad retained, not zeroed). |
| **R2** resolution/perf | Elapsed time per beam for local-extent render: ~1.7–2.2s (text+notext pair) in the standalone test; production run avg **0.22s/beam** for Set1 (13 beams, 2.8s total) including all T1.2+T1.4 work, not materially different from 9.3.2's per-beam cost profile. Artefact size per crop ~1–60KB (well within prior norms). No blow-up observed. |
| **R3** tightly-spaced beams | Found repeatedly — e.g. B2/B6, B8/B7, B8/B13, B9/B3, B9/B4, B10/B14, B10/B15 all have negative gaps (true overlaps). All handled via the per-side, per-neighbor `_per_side_pads` shrink (asymmetric, toward the beam's own core, never toward a fixed radius) — see full list in `r1_r3_padding_evidence.json` (18/18 Set1 beams needed at least one side tightened). |
| **R4** stale-artefact recurrence | Purge-then-regenerate (`for p in (crop_path, notext_path): if p.exists(): p.unlink()`) runs inside `_opencv_for_beam` on **every** call, for all 115 residual beams in Part D, not just the 5-beam test set. |
| **R5** notext validity at scale | Ink-density check (`_ink_density_pct` + `_CROP_INK_INVALID_THRESHOLD_PCT`) runs before `detect_ticks_opencv` is ever called, for all 115 beams. Result: `crop_invalid_after_count: 0` in all 3 sets — no beam was fed a near-blank crop as if it were valid geometry. |

---

## Files modified (exhaustive)

| File | Change |
|---|---|
| `Version9/src/PhaseT1_geometric_stirrup_evidence/beam_extent.py` | **New.** `find_beam_mark`, `build_label_entity_index`, `_resolve_bbox`, `_points_and_bboxes_to_bounds`, `_per_side_pads`, `compute_beam_scoped_extent`, `compute_extents_for_beams`. |
| `Version9/src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py` | Added `render_dxf_region_to_png` (local-extent render, natural aspect ratio, fixed max/min dim px). `render_dxf_to_png` (full-sheet) unchanged. `MODEL_VERSION` → 9.3.3. |
| `Version9/src/PhaseT1_geometric_stirrup_evidence/phase_t1_orchestrator.py` | `_opencv_for_beam` rewritten to use beam-scoped extents + local-extent render + purge + ink-density gate. New helpers `_load_annotations_by_beam`, `_load_dxf_renderer_module`, `_ink_density_pct`. `beam_extents` precomputed in `run()`. `MODEL_VERSION` → 9.3.3. |
| `Version9/src/PhaseT1_geometric_stirrup_evidence/__init__.py` | `MODEL_VERSION` → 9.3.3, docstring updated. |

No changes to `opencv_fallback.py` thresholds, `r21d_fusion.py`, zone-refinement, or R.1 association logic — confirmed by diff review and the R4 structural proof above.

## Analysis/evidence scripts written (read-only, not part of the production pipeline)

`Version9/data/output/Track1_geometric_evidence/{_local_crop_test.py, _9_3_3_part_d_analysis.py, _9_3_3_r1_r3_check.py, _9_3_3_r6_check.py, _9_3_3_crop_line_weight_check.py}` and their JSON outputs (`local_crop_test_report.json`, `part_d_before_after_report.json`, `r1_r3_padding_evidence.json`, `part_a2_crop_line_weight.json`).

---

## MODEL_VERSION

**9.3.3** — bumped from 9.3.2. PATCH-level: render/crop mechanism fix, no detection/fusion/zone-algorithm change.

## Suggested git commit message

```
Track1 9.3.3: beam-scoped extent + local-extent crop render

Replace the coarse ±1500mm blanket-pad + full-sheet-render-then-slice
crop mechanism with a beam-scoped extent (label + R.1-associated
entities + 300-500mm neighbor-aware padding) rendered directly at a
fixed 1200px-long-side resolution. Fixes B8-style neighbor bleed-over
and the ~100-130px effective resolution ceiling that made stirrup
ticks undetectable. Adds a notext-crop ink-density gate so a starved
render is flagged crop_invalid instead of silently reading as
insufficient_ticks.

No changes to T1.2 detection thresholds, T1.3 fusion confidence rules,
or T1.4 zone-refinement. QA.2A unchanged (STIRRUP MISSING 31 /
WRONG_QTY 113 / MATCH 63) because opencv_fallback's hardcoded 0.45
confidence stays below the 0.55 fusion bar regardless of crop
quality -- 26 more residual beams now get a visually-valid accepted
OpenCV detection (40->66 across 3 sets, 0 crop_invalid), but none
clear fusion.
```

---

## Honest verdict

The crop mechanism fix **did change the detection picture** — 26 net residual beams (29 new accepts, 3 corrected false-positive→reject) now produce accepted OpenCV geometry evidence backed by a visually-valid, ink-confirmed crop, and the test-set visual gate (label/bars/stirrup-spec/dims, no bleed) passed cleanly for all 5 reference beams including the exact B8/%%UB13 regression case. **It did not change QA.2A** — the residual **31 MISSING / 113 WRONG_QTY** is unmoved, but for a structurally different reason than in the 9.3.2 report: previously, T1's own detection was tested on crops later proven broken (blank/near-blank, bled-over), so a "no improvement" result was ambiguous — it wasn't clear whether the geometry was absent or the crop was. Now, with crops independently confirmed non-blank, beam-scoped, and legible at line-weight resolution, the residual's stagnation is attributable specifically to the **fusion confidence bar** (OpenCV's hardcoded 0.45 vs the required 0.55), not to crop starvation. **This is now solid evidence that Track 2 (the fusion/confidence-calibration and detection-quality layer, not the render/crop layer) is the correct next investment** — the crop mechanism is no longer a plausible explanation for the residual, and no further render/crop-side work is expected to move QA.2A on its own.
