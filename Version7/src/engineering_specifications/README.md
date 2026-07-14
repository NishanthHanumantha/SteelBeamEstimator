# Engineering Specifications

## Purpose

This package will host the **Engineering Specification Builder** — the Phase H synthesis layer that turns resolved engineering properties and semantic relationships into structured, beam-level reinforcement specifications ready for geometry placement and quantity takeoff.

Phase G produces *what the drawing says* (objects, roles, properties, resolution). Phase H will produce *what must be built* — normalized specification records per beam and reinforcement zone.

## Planned phases

| Phase | Focus |
|-------|--------|
| **H.1** | Engineering Specification Builder — core builder and specification model |
| **H.2+** | Reinforcement specification types, registry, validation, and export |

## Expected modules

Future modules will live in this package (names indicative, not final):

- **Specification Builder** — orchestrates input from property resolver and engineering objects
- **Reinforcement Specifications** — base specification types and composition
- **Main Reinforcement** — bottom/main bar specifications
- **Bottom Reinforcement** — explicit bottom bar groups
- **Extra Top Reinforcement** — additional top steel at supports or laps
- **Stirrups** — shear/torsion link specifications
- **Specification Registry** — indexed store of all beam specifications
- **Specification Validation** — structural and completeness checks
- **Specification Export** — JSON and downstream handoff artifacts

No modules are implemented yet. Validators, registries, and exporters follow the same in-package patterns used elsewhere in Version7.

## Relationship with existing architecture

| Upstream package | Role |
|------------------|------|
| `engineering_objects/` | Typed engineering objects and object graph (G.5.1) |
| `property_graph/` | Property candidates linked to objects (G.5.2) |
| `property_parser/` | Parsed engineering property values (G.5.3.1) |
| `property_resolver/` | Resolved properties, confidence, lifecycle (G.5.3.2–G.5.3.4) |
| `reinforcement/` | Semantic roles, relationships, beam matching (G.5.0–G.3) |
| `framing/` | Beam geometry, spans, engineering context (Phase F) |
| `general_notes/` + `services/` | Cover, development length tables, engineering rules (Phase E) |

This package **consumes** resolved properties and object semantics; it does **not** replace parsing, resolution, or framing logic.

## Future integration points

- **Input:** `property_resolver` resolved registry, `engineering_objects` graph, beam match decisions from `reinforcement/`
- **Output:** Specification registry consumed by `engineering_geometry/` (placement) and eventually `engineering_calculations/` (lengths) and `boq/` (quantities)
- **Config:** Paths and feature flags will extend `config/` and `src/config/output_paths.py` when Phase H is implemented
- **Pipeline:** Wired through `reinforcement/reinforcement_drawing_builder.py` (or successor runner) after G.5.3.4 outputs

## Status

**Phase H.1 complete** — Engineering Specification Builder aggregates resolved properties into reference-ready specifications.

**Phase H.1.1 complete** — Reference integrity contract established. Specifications contain engineering intent only; geometry is resolved through IDs in Phase H.2.

Reference documentation is exported to `data/output/phase_h/h_1_engineering_specifications/reference_contract.json`.
