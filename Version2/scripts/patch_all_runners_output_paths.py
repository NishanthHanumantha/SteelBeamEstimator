"""Apply OutputPaths updates to all run_phase_*.py runners."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IMPORT_LINE = "from src.config.output_paths import OutputPaths, OUTPUT_ROOT\n"

PHASE_DIR_MAP = {
    "run_phase_d11_annotation_audit.py": "phase_d1_1_dir",
    "run_phase_d12_spatial_validation.py": "phase_d1_2_dir",
    "run_phase_d13_region_validation.py": "phase_d1_3_dir",
    "run_phase_d131_boundary_leakage.py": "phase_d1_3_1_dir",
    "run_phase_d14_reassignment.py": "phase_d1_4_dir",
    "run_phase_d15_post_reassignment_validation.py": "phase_d1_5_dir",
    "run_phase_d16_annotation_classification.py": "phase_d1_6_dir",
    "run_phase_d16a_annotation_coverage.py": "phase_d1_6a_dir",
    "run_phase_d16b_entity_survey.py": "phase_d1_6b_dir",
    "run_phase_d17_dimension_extraction.py": "phase_d1_7_dir",
    "run_phase_d17a_dimension_source_audit.py": "phase_d1_7a_dir",
}

PATH_ATTR_MAP = {
    "beam_annotations_raw.json": "beam_annotations_raw",
    "beam_sketches_debug.json": "beam_sketches_debug",
    "sketch_ownership.json": "sketch_ownership",
    "header_occurrences.json": "header_occurrences",
    "beam_cells.json": "beam_cells",
    "beam_annotations_reassigned.json": "beam_annotations_reassigned",
    "annotation_region_validation.json": "annotation_region_validation",
    "annotation_region_validation_summary.json": "annotation_region_validation_summary",
    "boundary_leakage_report.json": "boundary_leakage_report",
    "boundary_leakage_summary.json": "boundary_leakage_summary",
    "annotation_ownership_audit.json": "annotation_ownership_audit",
    "annotation_ownership_validation.json": "annotation_ownership_validation",
    "annotation_ownership_summary.txt": "annotation_ownership_summary",
    "annotation_ownership_debug.dxf": "annotation_ownership_debug_dxf",
    "annotation_spatial_validation.json": "annotation_spatial_validation",
    "annotation_spatial_validation_summary.json": "annotation_spatial_validation_summary",
    "annotation_spatial_validation_report.txt": "annotation_spatial_validation_report",
    "annotation_spatial_validation_debug.dxf": "annotation_spatial_validation_debug_dxf",
    "annotation_region_validation_report.txt": "annotation_region_validation_report",
    "annotation_region_validation_debug.dxf": "annotation_region_validation_debug_dxf",
    "boundary_leakage_report.txt": "boundary_leakage_report_txt",
    "boundary_leakage_validation.json": "boundary_leakage_validation",
    "boundary_leakage_debug.dxf": "boundary_leakage_debug_dxf",
    "ownership_reassignment_log.json": "ownership_reassignment_log",
    "ownership_reassignment_summary.json": "ownership_reassignment_summary",
    "ownership_reassignment_validation.json": "ownership_reassignment_validation",
    "ownership_reassignment_debug.dxf": "ownership_reassignment_debug_dxf",
    "post_reassignment_audit.json": "post_reassignment_audit",
    "post_reassignment_region_validation.json": "post_reassignment_region_validation",
    "post_reassignment_leakage_report.json": "post_reassignment_leakage_report",
    "post_reassignment_validation_summary.json": "post_reassignment_validation_summary",
    "post_reassignment_validation_report.txt": "post_reassignment_validation_report",
    "post_reassignment_validation_status.json": "post_reassignment_validation_status",
    "post_reassignment_validation_debug.dxf": "post_reassignment_validation_debug_dxf",
    "annotation_types.json": "annotation_types",
    "annotation_type_validation.json": "annotation_type_validation",
    "annotation_type_summary.txt": "annotation_type_summary",
    "annotation_type_debug.dxf": "annotation_type_debug_dxf",
    "annotation_coverage_audit.json": "annotation_coverage_audit",
    "annotation_coverage_summary.json": "annotation_coverage_summary",
    "annotation_coverage_report.txt": "annotation_coverage_report",
    "annotation_coverage_validation.json": "annotation_coverage_validation",
    "annotation_coverage_debug.dxf": "annotation_coverage_debug_dxf",
    "dxf_entity_type_inventory.json": "dxf_entity_type_inventory",
    "dxf_text_inventory.json": "dxf_text_inventory",
    "dxf_pattern_search.json": "dxf_pattern_search",
    "dxf_entity_type_summary.json": "dxf_entity_type_summary",
    "dxf_entity_type_report.txt": "dxf_entity_type_report",
    "dxf_entity_type_validation.json": "dxf_entity_type_validation",
    "dxf_entity_type_debug.dxf": "dxf_entity_type_debug_dxf",
    "beam_annotations_extended.json": "beam_annotations_extended",
    "dimension_extraction_validation.json": "dimension_extraction_validation",
    "dimension_extraction_debug.dxf": "dimension_extraction_debug_dxf",
    "annotation_types_extended.json": "annotation_types_extended",
    "annotation_type_validation_extended.json": "annotation_type_validation_extended",
    "annotation_type_summary_extended.json": "annotation_type_summary_extended",
    "annotation_type_summary_extended.txt": "annotation_type_summary_extended_txt",
    "dimension_source_audit.json": "dimension_source_audit",
    "dimension_source_summary.json": "dimension_source_summary",
    "dimension_source_repeated_values.json": "dimension_source_repeated_values",
    "dimension_source_validation.json": "dimension_source_validation",
    "dimension_source_report.txt": "dimension_source_report",
    "dimension_source_debug.dxf": "dimension_source_debug_dxf",
}


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "from src.config.output_paths import" in text:
        print(f"Skip (already patched): {path.name}")
        return

    text = re.sub(
        r"DEFAULT_OUTPUT_DIR = Path\(\"data/output\"\)\n(?:DEFAULT_[^\n]+\n)+",
        "",
        text,
        count=1,
    )

    if IMPORT_LINE not in text:
        text = text.replace("from loguru import logger\n", "from loguru import logger\n\n" + IMPORT_LINE, 1)

    text = text.replace(
        "def parse_args() -> argparse.Namespace:\n    parser",
        "def parse_args() -> argparse.Namespace:\n    paths = OutputPaths()\n    parser",
        1,
    )

    for filename, attr in PATH_ATTR_MAP.items():
        text = text.replace(f"DEFAULT_OUTPUT_DIR / \"{filename}\"", f"paths.{attr}")
        text = text.replace(f"output_dir / \"{filename}\"", f"paths.{attr}")

    text = text.replace("default=DEFAULT_OUTPUT_DIR", "default=OUTPUT_ROOT")
    text = text.replace(
        "help=f\"Output directory (default: {DEFAULT_OUTPUT_DIR})\"",
        "help=f\"Output root directory (default: {OUTPUT_ROOT})\"",
    )

    phase_dir = PHASE_DIR_MAP.get(path.name)
    if phase_dir and "paths = OutputPaths(output_dir)" not in text:
        text = text.replace(
            "output_dir.mkdir(parents=True, exist_ok=True)",
            f"paths = OutputPaths(output_dir)\n    paths.{phase_dir}.mkdir(parents=True, exist_ok=True)",
            1,
        )

    path.write_text(text, encoding="utf-8")
    print(f"Patched {path.name}")


def main() -> None:
    for path in sorted(ROOT.glob("run_phase_*.py")):
        patch(path)


if __name__ == "__main__":
    main()
