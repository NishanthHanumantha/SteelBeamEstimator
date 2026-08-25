# PHASE W.8 — EVIDENCE COVERAGE REPORT

Prepared: 2026-08-25  
Canonical local E2E run: `20260825_195802_60556880` (First Set)

## Coverage identity

```
eligible_hybrid_beams (18)
  = beams_with_valid_evidence (18)
  + explicitly_unavailable_beams (0)

beams_with_valid_evidence (18)
  = beams_sent_to_claude (18)
  + explicitly_skipped_beams (0)
```

`identity_ok: true`  
`unexplained: 0`

## Counts (full local E2E)

| Metric | Count |
|---|---|
| total beams | 18 |
| Hybrid eligible | 18 |
| evidence packages generated | 18 |
| context selected | 18 |
| detail selected | 18 |
| distinct context/detail packages | 14 |
| P2.6.10 primary path | 13 (B1–B10, B12–B14; B9 included) |
| W.6 compatibility / fallback | 5 (B11, B15, B16, B17, B18) |
| T1 compatibility | 0 |
| evidence unavailable | 0 |
| Claude calls attempted | 18 |
| Claude success | 18 |
| Claude failure | 0 |
| Hybrid resolved | 18 |
| Hybrid unavailable | 0 |

Coverage JSON on that run tagged `p2610_primary_evidence=14` because B18 `W8_SELECTED_MIXED` was counted as primary. Manifests are the source of truth: **13 PRIMARY + 5 W.6/mixed**. Coverage classification was corrected after the run so mixed/compatibility is not counted as primary.

## Per-beam evidence class (manifests)

| Beam | Class | Source | Fallback |
|---|---|---|---|
| B1–B10, B12–B14 | PRIMARY | P2610B1_ADAPTIVE_CONTEXT_DETAIL | NONE |
| B11 | COMPATIBILITY | W6_ENVELOPE_RENDER | COMPATIBILITY |
| B15, B16 | FALLBACK | W6_ENVELOPE_RENDER | FALLBACK |
| B17 | COMPATIBILITY | W6_ENVELOPE_RENDER | COMPATIBILITY |
| B18 | COMPATIBILITY | W8_SELECTED_MIXED | COMPATIBILITY |

B11/B15–B18: P2.6.10 pair rendered but C3 returned `VISION_NOT_READY`. With T1.5 envelopes present, W.6 envelope crop was used explicitly (logged, not silent).

## Bounded live (before full E2E)

`webapp/tests/run_w8_live_verify.py` with `HYBRID_MAX_LIVE_CALLS=1` on First Set DXF without T1 envelopes:

- 13 PRIMARY, 5 UNAVAILABLE (W.6 fallback blocked: `ENVELOPE_EXTENT_MISSING`)
- 1/1 Claude success
- `identity_ok` for that fixture: eligible = 13 valid + 5 unavailable

Full pipeline E2E supplies envelopes, so those five become explicit W.6 fallback instead of unavailable.

## Visual evidence

- Context is sent: yes
- Detail is sent: yes
- Multiple detail images in the Claude request: **no** (C.5 contract remains 1+1)
- Crop provenance: `hybrid_evidence/<beam_id>/evidence_manifest.json` (no API keys)
