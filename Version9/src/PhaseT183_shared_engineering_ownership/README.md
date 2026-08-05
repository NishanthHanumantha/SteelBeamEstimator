# Phase T1.8.3 — Shared Engineering Ownership

**MODEL_VERSION:** 9.5.3

Additive multi-beam ownership for engineering annotations that legitimately
apply to more than one beam (initially **SIDE FACE REINFORCEMENT** only).

## What this phase does

- Detects SFR annotations using the existing T1.7 text classifier
- Builds an `EngineeringScope` over collinear, continuous framing beams
- Assigns `SharedEngineeringAnnotation` → many beams
- Merges at runtime: `effective = owned + shared`
- Renders via T1.8.1 / T1.8.2 helpers without mutating T1.8 artefacts

## What it does NOT do

- Does not edit T1.7 / T1.7.1 / T1.8 / T1.8.1 / T1.8.2 source
- Does not mutate `BeamOwnership.json` / `BeamScopedAnnotations.json`
- Does not share stirrups, longitudinal bars, dimensions, or beam names

## Run

```text
python Version9/data/output/Track1_geometric_evidence/_9_5_3_t183_shared_ownership.py
```

Disable shared ownership (legacy-identical path):

```python
PhaseT183Orchestrator(..., enable_shared_ownership=False).run()
```

## Key outputs

- `SharedOwnershipQA.json`
- `OwnershipDiff.md`
- `EngineeringScopes.json`
- `RenderedBeams/` / `Comparison/` / `Diff/`
