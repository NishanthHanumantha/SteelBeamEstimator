"""One-time migration: organize flat data/output files into phase subfolders."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "output"

MIGRATION: dict[str, str] = {
  "framing_beams.json": "phase_a",
  "framing_validation.json": "phase_a",
  "reinforcement_headers.json": "phase_b",
  "reinforcement_header_validation.json": "phase_b",
  "beam_cells.json": "phase_c",
  "beam_cells_validation.json": "phase_c",
  "beam_cells_debug.json": "phase_c_debug",
  "beam_cells_debug_summary.json": "phase_c_debug",
  "beam_cells_debug_validation.json": "phase_c_debug",
  "beam_cells_debug.dxf": "phase_c_debug",
  "beam_sketches_debug.json": "phase_c_debug",
  "beam_sketches_debug_validation.json": "phase_c_debug",
  "beam_sketches_debug.dxf": "phase_c_debug",
  "header_occurrences.json": "phase_c5",
  "sketch_ownership.json": "phase_c5",
  "sketch_ownership_validation.json": "phase_c5",
  "sketch_ownership_debug.dxf": "phase_c5",
  "beam_annotations_raw.json": "phase_d1",
  "beam_annotations_validation.json": "phase_d1",
  "beam_annotations_debug.dxf": "phase_d1",
  "annotation_ownership_audit.json": "phase_d1_1",
  "annotation_ownership_validation.json": "phase_d1_1",
  "annotation_ownership_summary.txt": "phase_d1_1",
  "annotation_ownership_debug.dxf": "phase_d1_1",
  "annotation_spatial_validation.json": "phase_d1_2",
  "annotation_spatial_validation_summary.json": "phase_d1_2",
  "annotation_spatial_validation_report.txt": "phase_d1_2",
  "annotation_spatial_validation_debug.dxf": "phase_d1_2",
  "annotation_region_validation.json": "phase_d1_3",
  "annotation_region_validation_summary.json": "phase_d1_3",
  "annotation_region_validation_report.txt": "phase_d1_3",
  "annotation_region_validation_debug.dxf": "phase_d1_3",
  "boundary_leakage_report.json": "phase_d1_3_1",
  "boundary_leakage_summary.json": "phase_d1_3_1",
  "boundary_leakage_report.txt": "phase_d1_3_1",
  "boundary_leakage_validation.json": "phase_d1_3_1",
  "boundary_leakage_debug.dxf": "phase_d1_3_1",
  "beam_annotations_reassigned.json": "phase_d1_4",
  "ownership_reassignment_log.json": "phase_d1_4",
  "ownership_reassignment_summary.json": "phase_d1_4",
  "ownership_reassignment_validation.json": "phase_d1_4",
  "ownership_reassignment_debug.dxf": "phase_d1_4",
  "post_reassignment_audit.json": "phase_d1_5",
  "post_reassignment_region_validation.json": "phase_d1_5",
  "post_reassignment_leakage_report.json": "phase_d1_5",
  "post_reassignment_validation_summary.json": "phase_d1_5",
  "post_reassignment_validation_report.txt": "phase_d1_5",
  "post_reassignment_validation_status.json": "phase_d1_5",
  "post_reassignment_validation_debug.dxf": "phase_d1_5",
  "annotation_types.json": "phase_d1_6",
  "annotation_type_validation.json": "phase_d1_6",
  "annotation_type_summary.txt": "phase_d1_6",
  "annotation_type_debug.dxf": "phase_d1_6",
  "annotation_coverage_audit.json": "phase_d1_6a",
  "annotation_coverage_summary.json": "phase_d1_6a",
  "annotation_coverage_report.txt": "phase_d1_6a",
  "annotation_coverage_validation.json": "phase_d1_6a",
  "annotation_coverage_debug.dxf": "phase_d1_6a",
  "dxf_entity_type_inventory.json": "phase_d1_6b",
  "dxf_text_inventory.json": "phase_d1_6b",
  "dxf_pattern_search.json": "phase_d1_6b",
  "dxf_entity_type_summary.json": "phase_d1_6b",
  "dxf_entity_type_report.txt": "phase_d1_6b",
  "dxf_entity_type_validation.json": "phase_d1_6b",
  "dxf_entity_type_debug.dxf": "phase_d1_6b",
  "beam_annotations_extended.json": "phase_d1_7",
  "dimension_extraction_validation.json": "phase_d1_7",
  "dimension_extraction_debug.dxf": "phase_d1_7",
  "annotation_types_extended.json": "phase_d1_7",
  "annotation_type_validation_extended.json": "phase_d1_7",
  "annotation_type_summary_extended.json": "phase_d1_7",
  "annotation_type_summary_extended.txt": "phase_d1_7",
  "dimension_source_audit.json": "phase_d1_7a",
  "dimension_source_summary.json": "phase_d1_7a",
  "dimension_source_repeated_values.json": "phase_d1_7a",
  "dimension_source_validation.json": "phase_d1_7a",
  "dimension_source_report.txt": "phase_d1_7a",
  "dimension_source_debug.dxf": "phase_d1_7a",
}


def main() -> None:
    moved = 0
    skipped = 0
    for filename, phase in MIGRATION.items():
        src = ROOT / filename
        if not src.exists():
            skipped += 1
            continue
        dest_dir = ROOT / phase
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        if dest.exists():
            skipped += 1
            continue
        src.rename(dest)
        moved += 1
        print(f"Moved {filename} -> {phase}/")
    print(f"Done: {moved} moved, {skipped} skipped")


if __name__ == "__main__":
    main()
