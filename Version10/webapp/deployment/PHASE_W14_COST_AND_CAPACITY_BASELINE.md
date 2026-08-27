# PHASE W.14 — COST AND CAPACITY BASELINE

Date: 2026-08-27  
Run ID: `20260827_093245_a32541a7`  
Drawing: Galera GF, 65 beams, 64 Vision calls

## Labeling

| Quantity | Label | Source |
| --- | --- | --- |
| Input / output / total tokens | **ACTUAL_OBSERVED** | Application Hybrid shadow telemetry (`usage.input_tokens` / `usage.output_tokens`) |
| USD cost | **ESTIMATED** | Public list rates in `PhaseW5_production_hybrid_shadow/cost.py` |
| Anthropic billed spend change | **NOT OBSERVED** | Console invoice/spend delta was not available in this validation |

Do not treat the USD figures below as billed cost.

Rates used (ESTIMATED, USD per million tokens):

- Input: $3.00 / MTok
- Output: $15.00 / MTok

## Measured Galera result

| Metric | Value | Label |
| --- | ---: | --- |
| Vision calls attempted | 64 | ACTUAL_OBSERVED |
| Vision calls successful | 64 | ACTUAL_OBSERVED |
| Vision calls failed | 0 | ACTUAL_OBSERVED |
| Input tokens | 246,621 | ACTUAL_OBSERVED |
| Output tokens | 43,535 | ACTUAL_OBSERVED |
| Total tokens | 290,156 | ACTUAL_OBSERVED |
| Estimated application-side cost | **$1.392888** | ESTIMATED |
| Cost per attempted beam | **$0.021764** | ESTIMATED |
| Cost per successful Vision beam | **$0.021764** | ESTIMATED |
| Cost per total drawing (65 beams) | **$1.392888** | ESTIMATED |

Per-success token spread (ACTUAL_OBSERVED):

- min 3,788
- mean 4,533.7
- max 4,974

Max/mean = 1.10, so a linear beam-count extrapolation is not marked unreliable for this drawing.

## 143-beam projection — PROJECTION ONLY

Method: `estimated_galera_usd * (143 / 64)` using attempted Vision beams.

| Item | Value |
| --- | --- |
| Label | **PROJECTION ONLY** |
| Basis | W.14 Galera ESTIMATED $1.392888 for 64 successful Vision calls |
| Projected 143-beam Hybrid Vision cost | **$3.112234** |
| Implied tokens if mix is similar | ~649k total tokens |

This projection assumes a similar token mix to Galera GF. A 143-beam Sixth Set drawing may differ in crop size and response length. It is not billed cost and was not executed.

Remaining workspace headroom after the $50 limit increase was not independently verified from Anthropic billing. Application evidence shows the previous 26-call spend-limit cliff did not recur on this 64-call run.
