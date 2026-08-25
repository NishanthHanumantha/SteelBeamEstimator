# PHASE W.8 — CURRENT VS TARGET CROP PATH

Prepared: 2026-08-25

## W.7 production crop path (before W.8)

```
R13 catalog beam_ids
  → W.6 ensure_visuals
      1. Prefer T1 opencv_renders/{beam_id}_crop.png
      2. Else T1.5 geometry_envelopes.json extent
         + M.1 render_dxf_region_to_png
         → PhaseW6_hybrid_semantic_resolution/crops/{beam_id}_crop.png
  → W.5 discover_visuals (one PNG)
  → live_invoke.call_shadow_beam(render_path=ONE png)
  → E.2 call_live_beam(context_path=same, detail_path=same)
  → C.5 encodes 2 images (often identical bytes)
  → D.2 → W.6 handoff → VB.1
```

First Set W.7 go-live: **0 T1 OpenCV crops**. All 18 beams used the W.6 envelope renderer. The same PNG was sent as both context and detail. `context_source` / `detail_source` were hardcoded `T1_OPENCV_CROP`.

W.6 adapter role before W.8: **PRIMARY for First Set** (compatibility crop, not P2.6.10 evidence selection).

## P2.6.10 target path

```
R13 catalog + run reinforcement DXF
  → title localize
  → build_adaptive_regions (distinct context vs detail extents)
  → render_crop context (1400 px) + detail (1800 px)
  → validate_render + C3 gate
  → C1C2 select vs W.6/T1 challenger if primary unusable
  → hybrid_evidence/<beam_id>/{context,detail}/selected.png
  → evidence_manifest.json (no secrets)
  → E.2 Vision with two paths
  → existing D.2 / handoff / VB.1
```

## Exact differences

| Capability | W.7 | P2.6.10 C1–C5 / B.1 | W.8 production source |
|---|---|---|---|
| Beam population | R13 catalog | Fourth-set B.1 validation IDs | R13 catalog |
| Candidate inventory | T1 then W.6 single crop | B.1/B.2/B.3 PNG inventory | Generated B.1 pair + optional W.6/T1 challenger |
| Crop selection | First existing file | C1C2 preference-preserving | C1C2 `select_for_type` |
| Context rendering | Same as detail | Distinct wider envelope | B.1 `context_extent` + `render_crop` |
| Detail rendering | W.6 envelope or T1 | Adaptive evidence envelope | B.1 `detail_extent` + `render_crop` |
| Rendering quality | File size ≥ 200 | `validate_render` | `validate_render` + C3 gate |
| Visual completeness | None | C.3 gate | C.3 gate (REUSABLE_WITH_ADAPTER) |
| Multiple detail regions | No | Not in C.5 Claude contract | Not sent (1+1 contract preserved) |
| Crop provenance | Weak / mis-tagged T1 | Selection manifest | `evidence_manifest.json` |
| Claude images | Often identical PNG twice | Context + detail | Selected context + detail |
| Silent fallback | T1-or-W.6, sources mixed | N/A | No. Fallback logged in manifest |
| W.6 envelope | De facto primary | Research unused | FALLBACK |
| T1 OpenCV | Preferred if present | Unused | COMPATIBILITY if primary fails |

## Integration decisions

1. Do not copy C1–C5 orchestrators or `data/output` review trees into production.
2. Generate B.1-style crops **per web run** under `hybrid_evidence/`.
3. Reuse existing E.2 / D.2 / W.6 handoff / VB.1.
4. Keep C.5 two-image contract. Do not invent multi-detail Claude payloads.
5. If C3 is `VISION_NOT_READY`, try W.6 envelope (needs T1.5 `geometry_envelopes.json`) then T1, else `EVIDENCE_UNAVAILABLE`. Deterministic Excel continues. No fabricated Vision patch.

## W.8 production evidence path

```
beam_id
  ↓
candidate inventory (B.1 pair, optional W.6/T1)
  ↓
evidence selection (C1C2)
  ↓
context selected.png  +  detail selected.png
  ↓
Claude Vision (E.2 / C.5)
  ↓
Hybrid Resolution (D.2)
  ↓
VB.1
```
