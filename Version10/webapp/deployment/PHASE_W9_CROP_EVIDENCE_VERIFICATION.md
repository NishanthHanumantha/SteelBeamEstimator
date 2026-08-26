# PHASE W.9 — CROP / EVIDENCE VERIFICATION

Run: `20260826_065256_4ba41266`  
Host: Lightsail production Version10 (`phase=W.9`)  
Drawing: First Set Galera OHT&STP

C.5 always records `n_images: 2` in the request contract (`context_images=1`, `detail_images=1`). Distinctness is verified by SHA-256 of `hybrid_evidence/<beam_id>/{context,detail}/selected.png`.

## Summary

| Class | Count | Distinct context/detail | Same SHA (duplicate payload) |
|------|------:|------------------------:|-----------------------------:|
| P2.6.10 PRIMARY | 13 | 13 | 0 |
| Compatibility / fallback | 5 | 1 (B18 mixed) | 4 (B11, B15, B16, B17) |
| Unavailable | 0 | — | — |
| **Total** | **18** | **14** | **4** |

Primary path is **not** the W.7 behavior of one envelope PNG duplicated as detail.

## P2.6.10 PRIMARY TWO-IMAGE CASES (13)

All `evidence_class=PRIMARY`, `visual_source=P2610B1_ADAPTIVE_CONTEXT_DETAIL`, `ctx_phase=B.1`, `det_phase=B.1`, `n_images=2`, `same_sha=false`.

B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B12, B13, B14.

Example B1:

- context SHA prefix `6cba1162e313`
- detail SHA prefix `296bccf0cfd7`
- contract `{context_images: 1, detail_images: 1, multiple_detail_supported_in_request: false}`

## COMPATIBILITY FALLBACK CASES (5)

| Beam | Class | Source | Reason | Same SHA | What was sent |
|------|--------|--------|--------|----------|----------------|
| B11 | COMPATIBILITY | W6_ENVELOPE_RENDER | C1C2_SELECTED_NON_PRIMARY | yes | W.6 envelope as context **and** detail |
| B15 | FALLBACK | W6_ENVELOPE_RENDER | P2610_PRIMARY_NOT_USABLE | yes | W.6 envelope as context **and** detail |
| B16 | FALLBACK | W6_ENVELOPE_RENDER | P2610_PRIMARY_NOT_USABLE | yes | W.6 envelope as context **and** detail |
| B17 | FALLBACK | W6_ENVELOPE_RENDER | P2610_PRIMARY_NOT_USABLE | yes | W.6 envelope as context **and** detail |
| B18 | COMPATIBILITY | W8_SELECTED_MIXED | C1C2_SELECTED_NON_PRIMARY | **no** | W.6 context + B.1 detail |

B18 is mixed, not a silent duplicate. B11/B15–B17 are the only duplicated-image cases, and each is explicitly classified.

## Provenance location

`data/web_runs/20260826_065256_4ba41266/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence/<beam_id>/evidence_manifest.json`

Manifests record beam_id, candidates considered, selected context/detail source phases, completeness, fallback status/reason, and the Claude image contract. No API keys.

## Coverage identity

```
Hybrid eligible 18
= P2.6.10 primary 13
+ other explicit runtime candidate 0 (no T1 native selected)
+ explicit compatibility/fallback 5
+ explicit unavailable 0
unexplained = 0
```
