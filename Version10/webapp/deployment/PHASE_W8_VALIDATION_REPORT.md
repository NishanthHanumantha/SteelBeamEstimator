# PHASE W.8 — VALIDATION REPORT

Prepared: 2026-08-25  
Lightsail: not mutated during local validation.

## TEST-W8 results

| ID | Result | Evidence |
|---|---|---|
| TEST-W8-01 HYBRID_MODE=off | **PASS** | `run_production_hybrid(mode=off)`: 0 Claude calls, R13 and Excel unchanged |
| TEST-W8-02 C1–C5 inventory | **PASS** | `COMPONENT_INVENTORY` every row in allowed classes |
| TEST-W8-03 W.7 crop-path trace | **PASS** | Documented in `PHASE_W8_CURRENT_VS_TARGET_CROP_PATH.md`. E.2/live_invoke now accept split context/detail |
| TEST-W8-04 P2.6.10 selection reuse | **PASS** | First Set B1: PRIMARY, distinct context (85978 B) vs detail (65336 B), C3 `VISION_READY_WITH_LIMITATIONS` |
| TEST-W8-05 Context+detail to Claude | **PASS** | Mock client received 2 images with different bytes and context/detail paths. Live log: `n_images=2` |
| TEST-W8-06 Population coverage | **PASS** | First Set 18/18 accounted. E2E unexplained=0, identity_ok |
| TEST-W8-07 Visual completeness | **PASS** | 14 packages with distinct context/detail. Five beams explicit W.6 fallback after C3 NOT_READY |
| TEST-W8-08 Live Claude bounded | **PASS** | `HYBRID_MAX_LIVE_CALLS=1` then 18. Model `claude-sonnet-4-5`. Key not printed |
| TEST-W8-09 Semantic through D.2 | **PASS** | E2E Hybrid SUCCESS, 18 resolved, 299 fields patched, handoff `HYBRID_SEMANTIC_HANDOFF_APPLIED` |
| TEST-W8-10 Engineering preservation | **PASS** | Existing-bar `cut_length_mm` overwrites=0; stirrup `quantity` overwrites=0 |
| TEST-W8-11 Evidence generation failure | **PASS** | No T1/DXF: `EVIDENCE_UNAVAILABLE`, Excel/R13 unchanged, no Vision patch |
| TEST-W8-12 Claude API failure | **PASS** | Fail client: classification fallback/API error, Excel/R13 unchanged |
| TEST-W8-13 Full local E2E | **PASS** | Run `20260825_195802_60556880`. Excel download 200. Steel 1468.732 kg. 18/18 Claude |
| TEST-W8-14 Production dry run | **PASS** (inventory only) | See pack list. Deploy executed only after this local gate set |

## Unit regression

- `PhaseW8_production_vision_evidence.unit_tests` PASS
- `PhaseW6_hybrid_production_authority.unit_tests` PASS
- Flask `test_w5_hybrid_shadow` / `test_w6_hybrid_authority` PASS (`phase=W.8`)

## Local E2E headline

```
run_id=20260825_195802_60556880
classification=HYBRID_SUCCESS
claude=18/18
p2610_primary=13
w6_fallback=5
unavailable=0
unexplained=0
cut_length_overwrites=0
stirrup_quantity_overwrites=0
excel=Estimation_Output.xlsx download HTTP 200
```

## API safety

- Key never printed in tests, manifests, coverage, or this report
- Key never committed
- `Version10/requirements.txt` remains `anthropic>=0.49.0,<1`
- Live client used existing P253/C.5 stack (not anthropic 1.x)

## Remaining limitation

Five First Set beams (B11, B15–B18) use explicit W.6 envelope fallback because C3 marked the B.1 pair `VISION_NOT_READY`. That is classified fallback, not silent envelope-for-all.
