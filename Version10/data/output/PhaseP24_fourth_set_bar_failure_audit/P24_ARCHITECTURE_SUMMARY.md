# P2.4 Architecture Summary

## Purpose
Attribute every Fourth Set GT reinforcement bar to the earliest pipeline stage
where expected information is lost or becomes incorrect.

## Inputs (read-only)
- Estimator Excel (GT only, post-processing comparison)
- Model Estimation_Output.xlsx (VB1)
- R3.1 PhysicalBars, T16 ownership, T17 AnnotationGraph
- T18 BeamOwnership, T18.3.1 shared scopes
- R1.3 beam_reinforcement_models_production

## Pipeline stages audited
GT → DXF → PhysicalBar → Ownership → Annotation → Leader → Role → Diameter → Quantity → Engineering → VB1 → Steel

## Matching
Reuses QA.2A BarMatcher deterministically (role/diameter/quantity).
GT Excel never influences detection/ownership/association.

## Constraints
- Fourth Set only
- No production mutations
- Determinism: audit executed twice
