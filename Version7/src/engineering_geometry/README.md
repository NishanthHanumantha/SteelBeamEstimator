# Engineering Geometry

## Purpose

This package will provide **engineering geometry association** — mapping reinforcement specifications to physical positions along beams using framing geometry, stationing, offsets, and coordinate systems established in earlier phases.

Where Phase H defines *what* reinforcement is required, this layer defines *where* it sits in engineering space relative to beam supports, faces, and detail views.

## Planned phases

| Phase | Focus |
|-------|--------|
| **H.x** | Beam geometry association and stationing (alongside or after specification builder) |
| **Later** | Reinforcement positioning, lookup services, coordinate mapping for calculations |

Exact phase numbering will be assigned when Phase H is scoped; this package is reserved for geometry synthesis, not DXF parsing or raw framing extraction.

## Expected modules

Future modules will live in this package (names indicative, not final):

- **Beam Geometry Association** — link specifications to framing beam instances and spans
- **Stationing** — chainage / station along beam centerline or reference axis
- **Offsets** — cover-based and detail-driven offsets from faces and centerlines
- **Reinforcement Positioning** — bar group anchor points and extent along station range
- **Geometry Lookup** — query API for positions by beam, zone, and specification id
- **Engineering Coordinate Mapping** — transforms between drawing, framing, and detail-local frames

No modules are implemented yet.

## Relationship with existing architecture

| Upstream package | Role |
|------------------|------|
| `framing/` | Beam centerlines, supports, clear spans, section context (Phase F) |
| `project/` | Drawing set, floor workspace, beam index |
| `reinforcement/` | Detail views, ownership, match decisions |
| `engineering_specifications/` | Specification records to be positioned (Phase H, planned) |
| `engineering_objects/` | Object identities and semantic anchors |

Raw geometry extraction remains in `framing/` and `parser/`. This package operates on **engineering-normalized** geometry already validated through Phase F and G.

## Future integration points

- **Input:** Framing beam geometry exports, specification registry from `engineering_specifications/`
- **Output:** Positioned reinforcement geometry records for `engineering_calculations/` (cut lengths, hooks, laps)
- **Validation:** In-package validators following the pattern in `framing/engineering_*_validator.py`
- **Export:** Phase-specific JSON under `data/output/phase_h/` (paths TBD in `output_paths.py`)

## Status

**Architecture placeholder only.** No geometry engine, classes, or pipeline changes until Phase H geometry work begins.
