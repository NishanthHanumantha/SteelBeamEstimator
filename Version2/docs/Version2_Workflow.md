# Steel Beam Estimator — Version 2 Workflow Document

**Project:** SteelBeamEstimator  
**Scope:** Version 2 pipeline (Phases A through C.5.2)  
**Date:** June 2026  
**Status:** Pre-Phase D — ownership validated, awaiting approval

---

## 1. Executive Summary

Version 2 extracts structural beam data from two AutoCAD DXF sources:

1. **Framing plan** — beam marks, centreline geometry, span dimensions  
2. **Reinforcement details** — section headers, grid layout, reinforcement sketches

The pipeline progresses from framing geometry (Phase A) through reinforcement headers (Phase B), spatial grid cells (Phase C), sketch detection, and sketch-to-header ownership validation (Phases C.5–C.5.2).

**Current sample drawing results:**

| Metric | Value |
|--------|-------|
| Unique beams (framing) | 18 (B1–B18) |
| Reinforcement header occurrences | 24 |
| Reinforcement sketches detected | 38 |
| Ownership assignments | 38 |
| Ownership status | PASS |
| Audit status | PASS_WITH_WARNINGS |

**Version 1 is frozen.** All new development occurs only inside `Version2/`.

---

## 2. Input Data

| File | Path | Purpose |
|------|------|---------|
| Framing plan DXF | `data/framing/Beam_FramingPlan.dxf` | Beam labels + STR-BEAM centreline geometry |
| Reinforcement DXF | `data/reinforcement/Beam_ReinforcementDetails.dxf` | Section titles (SEC TEXT) + detail geometry |

---

## 3. Pipeline Overview

```
┌─────────────────────┐     ┌─────────────────────┐
│  Framing Plan DXF   │     │ Reinforcement DXF   │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           ▼                           ▼
    ┌──────────────┐            ┌──────────────┐
    │  PHASE A     │            │  PHASE B     │
    │ Framing      │            │ Header       │
    │ Extraction   │            │ Extraction   │
    └──────┬───────┘            └──────┬───────┘
           │                           │
           │                           ▼
           │                    ┌──────────────┐
           │                    │  PHASE C     │
           │                    │ Beam Cells   │
           │                    └──────┬───────┘
           │                           │
           │                           ▼
           │                    ┌──────────────┐
           │                    │ Sketch Debug │
           │                    │ Detection    │
           │                    └──────┬───────┘
           │                           │
           │                           ▼
           │              ┌────────────────────────┐
           │              │ PHASE C.5 / C.5.1 /    │
           │              │ C.5.2 Ownership      │
           │              │ Validation + Audit   │
           │              └────────────────────────┘
           │                           │
           ▼                           ▼
    data/output/*.json         data/output/*.json
    data/output/*.dxf          data/output/*.dxf
```

---

## 4. Phase A — Framing Plan Extraction

**Objective:** Match beam labels `B{n}(WxD)` to STR-BEAM centreline segments and compute span geometry.

**Key modules:**

- `src/parser/dxf_flattener.py` — expands INSERT blocks (labels live inside blocks)
- `src/framing/framing_beam_extractor.py` — label-to-centreline matching
- `src/framing/framing_validator.py` — validation
- `src/framing/beam_geometry.py` — shared geometry helpers

**Algorithm highlights:**

- Flatten INSERT entities via `virtual_entities()`
- Greedy point-to-segment matching for labels to centreline segments
- Extract beam mark, width, depth, start/end coordinates, span length

**Outputs:**

| File | Description |
|------|-------------|
| `framing_beams.json` | 18 beams with geometry |
| `framing_validation.json` | No duplicates, all marks present |

**Run:** Part of `docs/run_phases_abc.py`

---

## 5. Phase B — Reinforcement Header Extraction

**Objective:** Detect reinforcement section titles from SEC TEXT layer.

**Key modules:**

- `src/reinforcement/header_extractor.py`
- `src/reinforcement/header_validator.py`
- `src/extractor/beam_label_extractor.py` — `B{n}(WxD)` pattern

**Important concept:** A beam mark may appear **multiple times** on the reinforcement sheet. Duplicate marks (B3, B12, B13, B18) indicate **multiple detail sketches**, not duplicate beams.

**Outputs:**

| File | Description |
|------|-------------|
| `reinforcement_headers.json` | 18 unique marks (deduped for catalog) |
| `reinforcement_header_validation.json` | 24 raw occurrences; duplicates reported |

---

## 6. Phase C — Header Grid Segmentation

**Objective:** Cluster headers into horizontal rows and assign column ownership cells.

**Key modules:**

- `src/grid/beam_cell_builder.py` — row clustering (±1000 mm Y tolerance)
- `src/grid/beam_cell_validator.py`

**Algorithm:**

1. Cluster headers into rows by Y coordinate
2. Sort headers within each row by X
3. Compute midpoint boundaries between adjacent headers
4. Assign xmin/xmax/ymin/ymax ownership cells per beam

**Sample result:** 4 rows — Row 1: 4 beams, Row 2: 7, Row 3: 4, Row 4: 3

**Outputs:**

| File | Description |
|------|-------------|
| `beam_cells.json` | 18 ownership cells |
| `beam_cells_validation.json` | No overlaps, no orphan headers |

**Debug (optional):**

- `beam_cells_debug.json`, `beam_cells_debug.dxf`, `beam_cells_debug_validation.json`
- Run: `docs/run_beam_cells_debug.py`

---

## 7. Sketch Debug Detection (Pre-Phase D)

**Objective:** Detect reinforcement detail sketches per header occurrence without merging.

**Key modules:**

- `src/grid/beam_sketch_debug_detector.py`
- `src/grid/beam_sketch_debug_exporter.py`
- `src/geometry/geometry_graph.py` — `GeometryGraphBuilder.build_sketches()`

**Concept:** **1 beam = N sketches.** Sketches are detected independently per header occurrence.

**Sample result:** 38 sketches across 18 beams; 10 beams have multiple sketches.

**Outputs:**

| File | Description |
|------|-------------|
| `beam_sketches_debug.json` | Sketch bboxes per beam |
| `beam_sketches_debug_validation.json` | PASS |
| `beam_sketches_debug.dxf` | Visual debug layer |

**Run:** `run_beam_sketches_debug.py`

---

## 8. Phase C.5 — Sketch Ownership Validation

**Objective:** Verify each sketch is owned by the correct header **occurrence** (not just beam mark).

**Key modules:**

- `src/grid/header_occurrence_exporter.py` — all 24 occurrences, no dedup
- `src/grid/sketch_ownership_builder.py` — nearest same-mark assignment
- `src/grid/sketch_ownership_validator.py`
- `src/grid/sketch_ownership_debug_exporter.py`

**Assignment rule:** For each sketch, compute bbox centroid; assign to nearest header occurrence of the **same beam mark**.

**Example (B3):**

- Occurrence 1 → B3_S1  
- Occurrence 2 → B3_S2

**Outputs:**

| File | Description |
|------|-------------|
| `header_occurrences.json` | 24 header positions |
| `sketch_ownership.json` | Sketches grouped per occurrence |
| `sketch_ownership_validation.json` | Validation report |
| `sketch_ownership_debug.dxf` | Layer `DEBUG_SKETCH_OWNERSHIP` |

**Run:** `run_sketch_ownership.py`

---

## 9. Phase C.5.1 — Ownership Audit Enhancement

**Objective:** Add distance metrics and confidence classification (audit only; no assignment changes).

**Key module:** `src/grid/sketch_ownership_auditor.py`

**Per-sketch fields in `sketch_ownership.json`:**

- `distance_mm` — Euclidean distance header → sketch centroid  
- `confidence` — HIGH (≤1500 mm), MEDIUM (≤4000 mm), LOW (>4000 mm)

**Note:** Large distances are normal — sections are often drawn 8–12 m below titles.

---

## 10. Phase C.5.2 — Audit Refinement

**Objective:** Separate ownership errors from layout warnings.

**Ownership status (FAIL only on true errors):**

1. Orphan sketches  
2. Multi-owned sketches  
3. Beam mark mismatch  
4. Missing ownership records  
5. Duplicate ownership records  

**Audit status:**

- `PASS` — no warnings  
- `PASS_WITH_WARNINGS` — long-distance warnings (>10000 mm)

**Current sample:**

- Ownership: **PASS**  
- Audit: **PASS_WITH_WARNINGS** (1 warning: B17_S2 at 12365.2 mm)

**Distance distribution:**

| Band | Count |
|------|-------|
| 0–1500 mm | 0 |
| 1500–4000 mm | 16 |
| 4000–8000 mm | 11 |
| 8000+ mm | 11 |

---

## 11. CLI Reference

All commands from `Version2/` with `$env:PYTHONPATH="."`

| Script | Phases | Outputs |
|--------|--------|---------|
| `docs/run_phases_abc.py` | A, B, C + cell debug | framing, headers, cells |
| `docs/run_beam_cells_debug.py` | Cell debug only | beam_cells_debug.* |
| `run_beam_sketches_debug.py` | Sketch detection | beam_sketches_debug.* |
| `run_sketch_ownership.py` | C.5, C.5.1, C.5.2 | ownership, validation, DXF |

---

## 12. Output File Inventory

### JSON (data/output/)

| File | Phase |
|------|-------|
| framing_beams.json | A |
| framing_validation.json | A |
| reinforcement_headers.json | B |
| reinforcement_header_validation.json | B |
| beam_cells.json | C |
| beam_cells_validation.json | C |
| beam_cells_debug.json | C debug |
| beam_sketches_debug.json | Sketch debug |
| beam_sketches_debug_validation.json | Sketch debug |
| header_occurrences.json | C.5 |
| sketch_ownership.json | C.5 / C.5.1 |
| sketch_ownership_validation.json | C.5 / C.5.2 |

### DXF debug overlays (data/output/)

| File | Layer | Content |
|------|-------|---------|
| beam_cells_debug.dxf | DEBUG_BEAM_CELLS | Cell boundaries |
| beam_sketches_debug.dxf | DEBUG_SKETCHS | Sketch bboxes |
| sketch_ownership_debug.dxf | DEBUG_SKETCH_OWNERSHIP | Headers, leaders, distances, WARNING labels |

---

## 13. Architecture Principles

1. **Version 1 frozen** — no changes outside Version2  
2. **Phased pipeline** — each phase produces validated JSON artifacts  
3. **1 beam = N sketches** — multiple headers per mark are intentional  
4. **Occurrence-level ownership** — not just beam-level grouping  
5. **Debug DXF overlays** — every major phase has visual verification in AutoCAD  
6. **Separation of concerns** — extraction, grid, sketches, ownership, audit are separate modules  

---

## 14. What Is NOT Yet Implemented (Phase D+)

- Phase D — annotation ownership within sketches  
- Reinforcement steel quantity parsing  
- Cross-linking framing spans to reinforcement details  
- Estimator / billing calculations  

**Next step:** Phase D after review and approval of ownership validation.

---

## 15. Document History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | June 2026 | Initial workflow through Phase C.5.2 |
