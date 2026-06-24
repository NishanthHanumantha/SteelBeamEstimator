# Version2 Pipeline Outputs

All pipeline artifacts live under `data/output/`, grouped by phase subdirectory.

Canonical paths are defined in `src/config/output_paths.py` (`OutputPaths`).

## Directory layout

| Folder | Phase | Runner |
|--------|-------|--------|
| `phase_a/` | A — Framing extraction | `docs/run_phases_abc.py` |
| `phase_b/` | B — Reinforcement headers | `docs/run_phases_abc.py` |
| `phase_c/` | C — Beam cells | `docs/run_phases_abc.py` |
| `phase_c_debug/` | C debug — Cells + sketches | `docs/run_phases_abc.py`, `docs/run_beam_cells_debug.py`, `run_beam_sketches_debug.py` |
| `phase_c5/` | C.5 — Sketch ownership | `run_sketch_ownership.py` |
| `phase_d1/` | D.1 — Raw annotation extraction | `run_phase_d1_annotations.py` |
| `phase_d1_1/` | D.1.1 — Ownership audit | `run_phase_d11_annotation_audit.py` |
| `phase_d1_2/` | D.1.2 — Spatial validation | `run_phase_d12_spatial_validation.py` |
| `phase_d1_3/` | D.1.3 — Region validation | `run_phase_d13_region_validation.py` |
| `phase_d1_3_1/` | D.1.3.1 — Boundary leakage | `run_phase_d131_boundary_leakage.py` |
| `phase_d1_4/` | D.1.4 — Ownership reassignment | `run_phase_d14_reassignment.py` |
| `phase_d1_5/` | D.1.5 — Post-reassignment validation | `run_phase_d15_post_reassignment_validation.py` |
| `phase_d1_6/` | D.1.6 — Type classification | `run_phase_d16_annotation_classification.py` |
| `phase_d1_6a/` | D.1.6A — Coverage audit | `run_phase_d16a_annotation_coverage.py` |
| `phase_d1_6b/` | D.1.6B — DXF entity survey | `run_phase_d16b_entity_survey.py` |
| `phase_d1_7/` | D.1.7 — DIMENSION extraction | `run_phase_d17_dimension_extraction.py` |
| `phase_d1_7a/` | D.1.7A — Dimension source audit | `run_phase_d17a_dimension_source_audit.py` |
| `phase_d1_7b/` | D.1.7B — Engineering annotation filter | `run_phase_d17b_engineering_filter.py` |
| `phase_d1_7c/` | D.1.7C — Engineering annotation integrity audit | `run_phase_d17c_integrity_audit.py` |
| `phase_d1_7d/` | D.1.7D — Engineering dataset finalization | `run_phase_d17d_engineering_dataset_finalization.py` |

## Cross-phase inputs (common dependencies)

| File | Location |
|------|----------|
| `beam_cells.json` | `phase_c/` |
| `beam_sketches_debug.json` | `phase_c_debug/` |
| `header_occurrences.json` | `phase_c5/` |
| `sketch_ownership.json` | `phase_c5/` |
| `beam_annotations_raw.json` | `phase_d1/` |
| `beam_annotations_reassigned.json` | `phase_d1_4/` |
| `beam_annotations_extended.json` | `phase_d1_7/` |
| `engineering_annotations.json` | `phase_d1_7b/` |
| `engineering_annotations_final.json` | `phase_d1_7d/` |

## Usage

```powershell
cd Version2
$env:PYTHONPATH="."

from src.config.output_paths import OutputPaths
paths = OutputPaths()
print(paths.sketch_ownership)
# data\output\phase_c5\sketch_ownership.json
```

Runners accept `-o` / `--output-dir` to override the root (default: `data/output`). Phase subfolders are created automatically.

## Migration

Existing flat files were moved with `scripts/organize_output_files.py`. Re-run that script only if legacy flat files reappear at the output root.
