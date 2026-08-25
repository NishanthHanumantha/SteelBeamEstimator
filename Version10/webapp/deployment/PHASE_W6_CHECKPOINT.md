# PHASE W.6 — CHECKPOINT

Saved: 2026-08-25  
Classification: **W6_PASS_WITH_LIMITATIONS**

## Implementation state

Hybrid production authority lives in `Version10/src/PhaseW6_hybrid_production_authority/`.  
It reuses W.5 / E.2 / D.2. The web production stage list is:

`VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → HYBRID → VB1`

`HYBRID_MODE=off` (default) | `shadow` | `production`.  
`authoritative` remains forbidden.

## Local validation

- W.5 unit tests 12/12 PASS
- W.6 unit tests 14/14 PASS
- Flask W.2+W.5+W.6 19/19 PASS
- Live Claude: 1-beam smoke + First Set 18/18 calls (`claude-sonnet-4-5`)
- VB.1 after handoff: 18 beams, 92 bars, 1447.565 kg Excel

## Deployment state (unchanged this phase)

| Item | State |
|------|--------|
| Public URL | http://13.127.104.99/ |
| Public release | still W.5 / Hybrid off (W.6 not deployed) |
| Gunicorn | `127.0.0.1:8001`, workers=1 |
| This phase | local only |

## Rollback (after a later deploy)

`HYBRID_MODE=off` → restart `steel-beam-estimator-v10` → deterministic pipeline.
