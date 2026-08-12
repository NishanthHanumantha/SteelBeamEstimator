# P2.5.0.2 Executive Summary — Top Reinforcement Trace

- MODEL_VERSION: `10.6.1`
- MODE: `DIAGNOSTIC_ONLY`
- ENGINEERING_CHANGES: `NONE`
- Decision: **FIX_EVIDENCE_LAYER**
- Determinism: **PASS**
- Regression unchanged: **True**

## Answers

1. Actual B97A top reinforcement is DXF LWPOLYLINE handle 1247FFF / `OWN::B97A::1247FFF` on layer -STR-BEAM at Y≈-21208369 (inside concrete envelope top band).

2. Actual B98A top reinforcement is DXF LWPOLYLINE handle 1247FFE / `OWN::B98A::1247FFE` on layer -STR-BEAM at Y≈-21208369 (inside concrete envelope).

3. NO. BAR::2B7B3233 / BAR::5B1BFCC2 are far-elevation -STR-REINF LINE entities (handles 1221B7C / 12469C4). Classified FALSE_CANDIDATE for B97A top bars.

4. NO. BAR::4D469A4E / BAR::E6591903 are far-elevation -STR-REINF LINEs (handles 11CD1B7 / 11CD1B5). Classified FALSE_CANDIDATE for B98A top bars.

5. T18 rejected them with R5_NEIGHBOUR_REJECT / ownership_reason=bar_y_outside_reinforcement_elevation because Y is tens of metres outside the beam reinforcement elevation band.

6. YES — T18 rejection is correct for treating them as non-owned engineering bars of this beam elevation.

7. R.3.1 detected the far-elevation LINEs as PhysicalBars (UUID BAR:: ids) and incorrectly beam-tagged them by X heuristics. R.3.1 did NOT detect the actual -STR-BEAM LWPOLYLINE top bars (detector only scans rein layers).

8. Actual top bars were never in R.3.1 PhysicalBars; they exist as T16 OwnedEntity TOP_BAR and are referenced by accepted 4-Y25 chains. They were 'lost' only at the P2.5.0 evidence_pack mapping (PhysicalBar-only).

9. R.3.1 misses -STR-BEAM LWPOLYLINE top bars because PhysicalBarDetector.REINF_LAYERS excludes -STR-BEAM.

10. YES — 4-Y25 has valid physical geometry: OWN::* LWPOLYLINE TOP_BAR inside the envelope, tip/leader chain owned.

11. YES — ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY is true in the current P2.5.0.1 package (accepted ann+leader, reinforcement=[]), even though upstream OWN geometry exists.

12. NO — current crop shows beam+annotations+leaders but omits explicit packaged top-bar geometry IDs for Vision. Not Claude-ready for top-bar completeness.

13. Evidence layer must package accepted-chain OWN:: / T16 TOP_BAR geometry as reinforcement (or diagnostic visual evidence) without re-including T18-rejected BAR::*. Optionally later extend R.3.1 layer coverage.

14. NO — do not change T18 acceptance for these rejected bars.

15. Optional later — extend R.3.1 to detect -STR-BEAM horizontal top bars; not required to unblock if evidence layer consumes T16 OWN::.

16. YES — primary fix is evidence-layer packaging of accepted OWN:: TOP_BAR geometry.

17. Additional detection only if OWN:: is missing; here OWN:: already exists — packaging is the gap.

## Decision rationale

Rejected BAR::* are FALSE_CANDIDATE far-elevation lines (T18 rejection correct). Actual top reinforcement is OWN::* LWPOLYLINE on -STR-BEAM, already owned by T16 and referenced by accepted 4-Y25 chains, but P2.5.0 evidence_pack does not emit OwnedEntity into reinforcement[]. Do NOT re-include rejected bars (recreates huge crops). Optionally later extend R.3.1 to -STR-BEAM, but immediate safe path is evidence-layer packaging of accepted-chain OWN:: TOP_BAR geometry.
