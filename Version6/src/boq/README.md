# Bill of Quantities (BOQ)

## Purpose

This package will implement **steel BOQ generation** — Phase J assembly of bar schedules, quantity summaries, Excel exports, cost estimation hooks, and reporting from calculation outputs.

This is the final synthesis stage: structured quantities and deliverables for estimators and fabricators.

## Planned phases

| Phase | Focus |
|-------|--------|
| **J.1+** | Steel BOQ model and bar schedule generation |
| **J.x** | Excel export, quantity summary, cost estimation, reporting |

Phase numbering will be finalized when Phase J is scoped.

## Expected modules

Future modules will live in this package (names indicative, not final):

- **Steel BOQ** — master BOQ structure per project / floor / beam
- **Bar Schedule** — mark, diameter, shape code, count, length, weight
- **Excel Export** — formatted workbook output for estimators
- **Quantity Summary** — aggregated tonnage and count by diameter / grade
- **Cost Estimation** — unit rates and extended amounts (optional integration)
- **Reporting** — validation summaries and export audit trails

No modules are implemented yet. Export patterns may mirror existing JSON exporters in `property_resolver/` and `framing/` but remain inside this package.

## Relationship with existing architecture

| Upstream package | Role |
|------------------|------|
| `engineering_calculations/` | Cut lengths, bar lengths, laps (Phase I, planned) |
| `engineering_specifications/` | Specification metadata for schedule columns |
| `engineering_geometry/` | Shape / placement context for schedule notes |
| `project/` | Project and drawing set identity for report headers |
| `estimation/` | Estimator rules that may influence costing |

BOQ does **not** re-run parsing, resolution, or calculations; it aggregates finalized calculation outputs.

## Future integration points

- **Input:** Calculation registry, specification registry, project workspace metadata
- **Output:** `bar_schedule.json`, Excel workbooks, summary reports under `data/output/phase_j/` (paths TBD)
- **Pipeline:** Final stage after Phase I in the main runner (`Run_PY/`)
- **Config:** Export paths and templates in `config/` when Phase J is implemented

## Status

**Architecture placeholder only.** No BOQ generator, exporters, or pipeline changes until Phase J begins.
