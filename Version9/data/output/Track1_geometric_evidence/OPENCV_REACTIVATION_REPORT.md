# Track 1 Patch 9.3.2 — OpenCV Fallback Activation + Scoped Re-verification

Date: 2026-08-03

## STEP 0 — Root-cause confirmation

| Check | Result |
|---|---|
| Interpreter | `C:\Users\nishanth.h\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.3) — same interpreter used by `Run_PY/` |
| `pip show opencv-python` | **not installed** |
| `pip show opencv-python-headless` | **not installed** (before STEP 2) |
| `import cv2` | `ModuleNotFoundError: No module named 'cv2'` |
| `requirements.txt` | no opencv entry (before STEP 2) |
| Trigger code | `opencv_fallback.py` lines 44–48: `try: import cv2` / `except ImportError: reject_reason = "opencv_not_installed"` |

**Root cause confirmed:** OpenCV was never a dependency; every prior Track 1 “opencv_fallback” result was the ImportError dead path.

## STEP 1 — Scoped target list

`opencv_reactivation_target_beams.json` — **74 beams** with `reject_reason == opencv_not_installed` in latest flag-on evidence:

| Set | Count |
|---|---:|
| Set1 | 12 |
| Set2 | 32 |
| Set3 | 30 |

Prior vector reject reasons (why they fell to OpenCV): mostly `pitch_range_filter` / `median_pitch_out_of_range:*` / low tick counts (noise pitches like 0.69 mm, 35 mm, 42 mm).

## STEP 2 — Install

- Installed: `opencv-python-headless==5.0.0.93`
- Verified: `import cv2; print(cv2.__version__)` → **5.0.0**
- Pinned in `Version9/requirements.txt`

## Additional blockers found (and minimally fixed) while enabling the real path

Installing cv2 alone was not sufficient for a meaningful OpenCV test:

1. **Blank geometry-only render** — `render_text=False` used a per-entity `draw_entity` loop that produced **zero ink** (white PNG). Fixed in `dxf_renderer.py` to use `draw_layout(..., filter_func=...)`.
2. **CoordTransform vs actual PNG size mismatch** — transform claimed 6000×4400 while file was ~800×1077; crop/mm-scale wrong. Fixed to read actual PNG size into `CoordTransform`.
3. **OpenCV 5 HoughLinesP shape** — `(N,4)` vs `(N,1,4)` crashed the fallback. Normalized in `opencv_fallback.py` (no threshold changes).

These are environment/compatibility fixes required for the designed fallback to execute — not detection-threshold or fusion-rule changes.

## STEP 3 — Scoped OpenCV re-run (74 beams)

| Metric | Value |
|---|---|
| Targets | 74 |
| `opencv_not_installed` remaining | **0** |
| Accepted | **7** (all Set3) |
| Still rejected (real reasons) | 67 |
| Elapsed | 210.97 s (~2.85 s/beam) |

Reject reasons after real OpenCV:

| Reason | Count |
|---|---:|
| `tick_count=0 < 3` | 43 |
| `tick_count=1 < 3` | 9 |
| `tick_count=2 < 3` | 8 |
| `no_hough_lines` | 5 |
| `pitch_range_filter` | 2 |

Accepted (existing thresholds unchanged; OpenCV hardcodes `confidence=0.45`):

| Beam | Pitch mm | Conf | Ticks | Groups |
|---|---:|---:|---:|---|
| Set3 B17 | 63.47 | 0.45 | 10 | WRONG_QTY |
| Set3 B19A | 63.47 | 0.45 | 17 | WRONG_QTY |
| Set3 B28 | 111.06 | 0.45 | 8 | WRONG_QTY |
| Set3 B48 | 174.54 | 0.45 | 3 | WRONG_QTY |
| Set3 B54 | 63.47 | 0.45 | 4 | WRONG_QTY |
| Set3 B56 | 63.47 | 0.45 | 22 | MISSING+WRONG_QTY |
| Set3 B59 | 63.47 | 0.45 | 4 | MISSING+WRONG_QTY |

**R2 flag:** repeated `63.47` mm pitch on multiple beams looks suspicious (possible hatch/noise). Spot-check crops under `PhaseT1_geometric_stirrup_evidence/opencv_renders/` (e.g. `Set3_B17_crop.png`, `Set1_B11_crop.png` failing, `Set1_B10_crop.png` failing).

## STEP 4 — Fusion (scoped)

**0 fusion retags.** Existing `r21d_fusion.py` requires `geo_conf >= 0.55` for AGREE/CONFLICT/GEOMETRY_ONLY_SYNTH. OpenCV fallback hardcodes `confidence=0.45`, so all 7 accepts are weak geometry → TEXT_ONLY under unmodified rules.

## STEP 5 — QA.2A delta

### (a) Targeted beams (74)

Production `beam_reinforcement_models_production.json` for all 74 target beams: **byte/row-identical before vs after** (0 diffs).  
⇒ **No STIRRUP status changes** (MISSING/WRONG_QTY/MATCH unchanged for every target beam).

### (b) Full 3-set sanity

| Metric | 9.3.1 before | 9.3.2 after |
|---|---:|---:|
| Overall | 70.23% | **70.23%** |
| Steel | 91.07% | **91.07%** |
| Bar detection | 68.52% | **68.52%** |
| Bar accuracy | 27.41% | **27.41%** |

STIRRUP totals unchanged: MISSING **31**, WRONG_QTY **113**, MATCH **63**.

**R4 (outside target list):** Set1 6/6, Set2 33/33, Set3 31/31 clean — **0 leakage**.

Avg pipeline time rose ~56 s → ~136 s (OpenCV render cost on residual fallback beams) — bounded, not a full redesign.

## R1–R5

| Risk | Result |
|---|---|
| R1 OpenCV still fails some beams | **Yes — 67/74** real rejects (insufficient ticks / no lines / pitch filter). Valuable Track-2 candidates. |
| R2 False positives | **7 accepts**, several share identical 63.47 mm pitch — flag for visual review; fusion did not act (conf 0.45). |
| R3 Performance | 211 s for 74 beams (~2.85 s/beam); full QA avg pipeline +80 s. Acceptable. |
| R4 Scope leakage | **CLEAN** |
| R5 Flag-off | Soft-exit confirmed (`enable=false` → no-op). Flag re-enabled after check. |

## Verdict

**OpenCV is now installed and the fallback path truly runs**, but with existing thresholds + hardcoded OpenCV confidence 0.45, it **does not shrink** the residual 31 MISSING / 113 WRONG_QTY. The bottleneck is not “missing cv2” alone — vector already covers strong cases; OpenCV rarely clears the fusion bar; qty/zone/face problems remain Track 2 territory.

**Track 2 remains the right next investment.**

MODEL_VERSION: **9.3.2**
