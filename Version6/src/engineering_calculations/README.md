# Engineering Calculations

## Purpose

This package will host the **engineering calculation engine** — Phase I logic that converts positioned specifications and geometry into codified bar lengths, laps, hooks, anchorage, and curtailment per project rules and general-notes tables.

Calculations apply engineering formulas and tabulated values; they do not parse drawings or build specifications.

## Planned phases

| Phase | Focus |
|-------|--------|
| **I.1+** | Development length, lap length, hook length |
| **I.x** | Anchorage, curtailment, cut length, bar length aggregation |
| **I.x** | Engineering formula library and calculation registry |

Phase numbering will be finalized when Phase I is scoped. This package is reserved for all quantity-driving engineering math before BOQ assembly.

## Expected modules

Future modules will live in this package (names indicative, not final):

- **Development Length** — ld from diameter, grade, cover, and table lookup
- **Lap Length** — splice lengths per code and project rules
- **Hook Length** — standard and seismic hook extensions
- **Anchorage** — required embedment and availability checks
- **Curtailment** — bar termination stations and taper rules
- **Cut Length** — fabrication length per bar mark
- **Bar Length** — total supplied length including laps and hooks
- **Engineering Formula Library** — shared formulas referenced by calculation modules

No modules are implemented yet. Table lookups may delegate to `services/` (e.g. development length, cover) where Phase E already provides data.

## Relationship with existing architecture

| Upstream package | Role |
|------------------|------|
| `general_notes/` + `services/` | Engineering rules, ld/cover tables (Phase E) |
| `estimation/` | Estimator rule loading patterns |
| `engineering_specifications/` | Bar sizes, counts, grades (Phase H, planned) |
| `engineering_geometry/` | Stations, extents, positioning (Phase H, planned) |
| `property_resolver/` | Resolved numeric properties where specifications reference drawing values |

This package **does not** duplicate `services/development_length_service.py` or similar; it orchestrates calculation workflows for bar takeoff at a higher level.

## Future integration points

- **Input:** Specification registry, geometry placement registry, Phase E engineering knowledge JSON
- **Output:** Calculation registry and per-bar results consumed by `boq/`
- **Validation:** Calculation completeness and rule compliance checks (in-package)
- **Export:** Phase I outputs under `data/output/phase_i/` (paths TBD)

## Status

**Architecture placeholder only.** No calculation engine, formulas, or pipeline changes until Phase I begins.
