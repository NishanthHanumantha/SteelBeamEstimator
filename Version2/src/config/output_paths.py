"""Canonical paths for Version2 pipeline outputs under data/output/."""

from pathlib import Path

OUTPUT_ROOT = Path("data/output")

PHASE_A = "phase_a"
PHASE_B = "phase_b"
PHASE_C = "phase_c"
PHASE_C_DEBUG = "phase_c_debug"
PHASE_C5 = "phase_c5"
PHASE_D1 = "phase_d1"
PHASE_D1_1 = "phase_d1_1"
PHASE_D1_2 = "phase_d1_2"
PHASE_D1_3 = "phase_d1_3"
PHASE_D1_3_1 = "phase_d1_3_1"
PHASE_D1_4 = "phase_d1_4"
PHASE_D1_5 = "phase_d1_5"
PHASE_D1_6 = "phase_d1_6"
PHASE_D1_6A = "phase_d1_6a"
PHASE_D1_6B = "phase_d1_6b"
PHASE_D1_7 = "phase_d1_7"
PHASE_D1_7A = "phase_d1_7a"
PHASE_D1_7B = "phase_d1_7b"
PHASE_D1_7C = "phase_d1_7c"
PHASE_D1_7D = "phase_d1_7d"


def phase_dir(root: Path, phase: str) -> Path:
    return root / phase


class OutputPaths:
    """Resolve output file paths grouped by pipeline phase."""

    def __init__(self, root: Path = OUTPUT_ROOT) -> None:
        self.root = root

    # --- Phase A ---
    @property
    def phase_a_dir(self) -> Path:
        return phase_dir(self.root, PHASE_A)

    @property
    def framing_beams(self) -> Path:
        return self.phase_a_dir / "framing_beams.json"

    @property
    def framing_validation(self) -> Path:
        return self.phase_a_dir / "framing_validation.json"

    # --- Phase B ---
    @property
    def phase_b_dir(self) -> Path:
        return phase_dir(self.root, PHASE_B)

    @property
    def reinforcement_headers(self) -> Path:
        return self.phase_b_dir / "reinforcement_headers.json"

    @property
    def reinforcement_header_validation(self) -> Path:
        return self.phase_b_dir / "reinforcement_header_validation.json"

    # --- Phase C ---
    @property
    def phase_c_dir(self) -> Path:
        return phase_dir(self.root, PHASE_C)

    @property
    def beam_cells(self) -> Path:
        return self.phase_c_dir / "beam_cells.json"

    @property
    def beam_cells_validation(self) -> Path:
        return self.phase_c_dir / "beam_cells_validation.json"

    # --- Phase C debug (cells + sketches) ---
    @property
    def phase_c_debug_dir(self) -> Path:
        return phase_dir(self.root, PHASE_C_DEBUG)

    @property
    def beam_cells_debug(self) -> Path:
        return self.phase_c_debug_dir / "beam_cells_debug.json"

    @property
    def beam_cells_debug_summary(self) -> Path:
        return self.phase_c_debug_dir / "beam_cells_debug_summary.json"

    @property
    def beam_cells_debug_validation(self) -> Path:
        return self.phase_c_debug_dir / "beam_cells_debug_validation.json"

    @property
    def beam_cells_debug_dxf(self) -> Path:
        return self.phase_c_debug_dir / "beam_cells_debug.dxf"

    @property
    def beam_sketches_debug(self) -> Path:
        return self.phase_c_debug_dir / "beam_sketches_debug.json"

    @property
    def beam_sketches_debug_validation(self) -> Path:
        return self.phase_c_debug_dir / "beam_sketches_debug_validation.json"

    @property
    def beam_sketches_debug_dxf(self) -> Path:
        return self.phase_c_debug_dir / "beam_sketches_debug.dxf"

    # --- Phase C.5 ---
    @property
    def phase_c5_dir(self) -> Path:
        return phase_dir(self.root, PHASE_C5)

    @property
    def header_occurrences(self) -> Path:
        return self.phase_c5_dir / "header_occurrences.json"

    @property
    def sketch_ownership(self) -> Path:
        return self.phase_c5_dir / "sketch_ownership.json"

    @property
    def sketch_ownership_validation(self) -> Path:
        return self.phase_c5_dir / "sketch_ownership_validation.json"

    @property
    def sketch_ownership_debug_dxf(self) -> Path:
        return self.phase_c5_dir / "sketch_ownership_debug.dxf"

    # --- Phase D.1 ---
    @property
    def phase_d1_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1)

    @property
    def beam_annotations_raw(self) -> Path:
        return self.phase_d1_dir / "beam_annotations_raw.json"

    @property
    def beam_annotations_validation(self) -> Path:
        return self.phase_d1_dir / "beam_annotations_validation.json"

    @property
    def beam_annotations_debug_dxf(self) -> Path:
        return self.phase_d1_dir / "beam_annotations_debug.dxf"

    # --- Phase D.1.1 ---
    @property
    def phase_d1_1_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_1)

    @property
    def annotation_ownership_audit(self) -> Path:
        return self.phase_d1_1_dir / "annotation_ownership_audit.json"

    @property
    def annotation_ownership_validation(self) -> Path:
        return self.phase_d1_1_dir / "annotation_ownership_validation.json"

    @property
    def annotation_ownership_summary(self) -> Path:
        return self.phase_d1_1_dir / "annotation_ownership_summary.txt"

    @property
    def annotation_ownership_debug_dxf(self) -> Path:
        return self.phase_d1_1_dir / "annotation_ownership_debug.dxf"

    # --- Phase D.1.2 ---
    @property
    def phase_d1_2_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_2)

    @property
    def annotation_spatial_validation(self) -> Path:
        return self.phase_d1_2_dir / "annotation_spatial_validation.json"

    @property
    def annotation_spatial_validation_summary(self) -> Path:
        return self.phase_d1_2_dir / "annotation_spatial_validation_summary.json"

    @property
    def annotation_spatial_validation_report(self) -> Path:
        return self.phase_d1_2_dir / "annotation_spatial_validation_report.txt"

    @property
    def annotation_spatial_validation_debug_dxf(self) -> Path:
        return self.phase_d1_2_dir / "annotation_spatial_validation_debug.dxf"

    # --- Phase D.1.3 ---
    @property
    def phase_d1_3_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_3)

    @property
    def annotation_region_validation(self) -> Path:
        return self.phase_d1_3_dir / "annotation_region_validation.json"

    @property
    def annotation_region_validation_summary(self) -> Path:
        return self.phase_d1_3_dir / "annotation_region_validation_summary.json"

    @property
    def annotation_region_validation_report(self) -> Path:
        return self.phase_d1_3_dir / "annotation_region_validation_report.txt"

    @property
    def annotation_region_validation_debug_dxf(self) -> Path:
        return self.phase_d1_3_dir / "annotation_region_validation_debug.dxf"

    # --- Phase D.1.3.1 ---
    @property
    def phase_d1_3_1_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_3_1)

    @property
    def boundary_leakage_report(self) -> Path:
        return self.phase_d1_3_1_dir / "boundary_leakage_report.json"

    @property
    def boundary_leakage_summary(self) -> Path:
        return self.phase_d1_3_1_dir / "boundary_leakage_summary.json"

    @property
    def boundary_leakage_report_txt(self) -> Path:
        return self.phase_d1_3_1_dir / "boundary_leakage_report.txt"

    @property
    def boundary_leakage_validation(self) -> Path:
        return self.phase_d1_3_1_dir / "boundary_leakage_validation.json"

    @property
    def boundary_leakage_debug_dxf(self) -> Path:
        return self.phase_d1_3_1_dir / "boundary_leakage_debug.dxf"

    # --- Phase D.1.4 ---
    @property
    def phase_d1_4_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_4)

    @property
    def beam_annotations_reassigned(self) -> Path:
        return self.phase_d1_4_dir / "beam_annotations_reassigned.json"

    @property
    def ownership_reassignment_log(self) -> Path:
        return self.phase_d1_4_dir / "ownership_reassignment_log.json"

    @property
    def ownership_reassignment_summary(self) -> Path:
        return self.phase_d1_4_dir / "ownership_reassignment_summary.json"

    @property
    def ownership_reassignment_validation(self) -> Path:
        return self.phase_d1_4_dir / "ownership_reassignment_validation.json"

    @property
    def ownership_reassignment_debug_dxf(self) -> Path:
        return self.phase_d1_4_dir / "ownership_reassignment_debug.dxf"

    # --- Phase D.1.5 ---
    @property
    def phase_d1_5_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_5)

    @property
    def post_reassignment_audit(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_audit.json"

    @property
    def post_reassignment_region_validation(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_region_validation.json"

    @property
    def post_reassignment_leakage_report(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_leakage_report.json"

    @property
    def post_reassignment_validation_summary(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_validation_summary.json"

    @property
    def post_reassignment_validation_report(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_validation_report.txt"

    @property
    def post_reassignment_validation_status(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_validation_status.json"

    @property
    def post_reassignment_validation_debug_dxf(self) -> Path:
        return self.phase_d1_5_dir / "post_reassignment_validation_debug.dxf"

    # --- Phase D.1.6 ---
    @property
    def phase_d1_6_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_6)

    @property
    def annotation_types(self) -> Path:
        return self.phase_d1_6_dir / "annotation_types.json"

    @property
    def annotation_type_validation(self) -> Path:
        return self.phase_d1_6_dir / "annotation_type_validation.json"

    @property
    def annotation_type_summary(self) -> Path:
        return self.phase_d1_6_dir / "annotation_type_summary.txt"

    @property
    def annotation_type_debug_dxf(self) -> Path:
        return self.phase_d1_6_dir / "annotation_type_debug.dxf"

    # --- Phase D.1.6A ---
    @property
    def phase_d1_6a_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_6A)

    @property
    def annotation_coverage_audit(self) -> Path:
        return self.phase_d1_6a_dir / "annotation_coverage_audit.json"

    @property
    def annotation_coverage_summary(self) -> Path:
        return self.phase_d1_6a_dir / "annotation_coverage_summary.json"

    @property
    def annotation_coverage_report(self) -> Path:
        return self.phase_d1_6a_dir / "annotation_coverage_report.txt"

    @property
    def annotation_coverage_validation(self) -> Path:
        return self.phase_d1_6a_dir / "annotation_coverage_validation.json"

    @property
    def annotation_coverage_debug_dxf(self) -> Path:
        return self.phase_d1_6a_dir / "annotation_coverage_debug.dxf"

    # --- Phase D.1.6B ---
    @property
    def phase_d1_6b_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_6B)

    @property
    def dxf_entity_type_inventory(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_entity_type_inventory.json"

    @property
    def dxf_text_inventory(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_text_inventory.json"

    @property
    def dxf_pattern_search(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_pattern_search.json"

    @property
    def dxf_entity_type_summary(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_entity_type_summary.json"

    @property
    def dxf_entity_type_report(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_entity_type_report.txt"

    @property
    def dxf_entity_type_validation(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_entity_type_validation.json"

    @property
    def dxf_entity_type_debug_dxf(self) -> Path:
        return self.phase_d1_6b_dir / "dxf_entity_type_debug.dxf"

    # --- Phase D.1.7 ---
    @property
    def phase_d1_7_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7)

    @property
    def beam_annotations_extended(self) -> Path:
        return self.phase_d1_7_dir / "beam_annotations_extended.json"

    @property
    def dimension_extraction_validation(self) -> Path:
        return self.phase_d1_7_dir / "dimension_extraction_validation.json"

    @property
    def dimension_extraction_debug_dxf(self) -> Path:
        return self.phase_d1_7_dir / "dimension_extraction_debug.dxf"

    @property
    def annotation_types_extended(self) -> Path:
        return self.phase_d1_7_dir / "annotation_types_extended.json"

    @property
    def annotation_type_validation_extended(self) -> Path:
        return self.phase_d1_7_dir / "annotation_type_validation_extended.json"

    @property
    def annotation_type_summary_extended(self) -> Path:
        return self.phase_d1_7_dir / "annotation_type_summary_extended.json"

    @property
    def annotation_type_summary_extended_txt(self) -> Path:
        return self.phase_d1_7_dir / "annotation_type_summary_extended.txt"

    # --- Phase D.1.7A ---
    @property
    def phase_d1_7a_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7A)

    @property
    def dimension_source_audit(self) -> Path:
        return self.phase_d1_7a_dir / "dimension_source_audit.json"

    @property
    def dimension_source_summary(self) -> Path:
        return self.phase_d1_7a_dir / "dimension_source_summary.json"

    @property
    def dimension_source_repeated_values(self) -> Path:
        return self.phase_d1_7a_dir / "dimension_source_repeated_values.json"

    @property
    def dimension_source_validation(self) -> Path:
        return self.phase_d1_7a_dir / "dimension_source_validation.json"

    @property
    def dimension_source_report(self) -> Path:
        return self.phase_d1_7a_dir / "dimension_source_report.txt"

    @property
    def dimension_source_debug_dxf(self) -> Path:
        return self.phase_d1_7a_dir / "dimension_source_debug.dxf"

    # --- Phase D.1.7B ---
    @property
    def phase_d1_7b_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7B)

    @property
    def engineering_annotations(self) -> Path:
        return self.phase_d1_7b_dir / "engineering_annotations.json"

    @property
    def geometry_dimension_annotations(self) -> Path:
        return self.phase_d1_7b_dir / "geometry_dimension_annotations.json"

    @property
    def rejected_measurement_annotations(self) -> Path:
        return self.phase_d1_7b_dir / "rejected_measurement_annotations.json"

    @property
    def engineering_annotation_summary(self) -> Path:
        return self.phase_d1_7b_dir / "engineering_annotation_summary.json"

    @property
    def engineering_annotation_validation(self) -> Path:
        return self.phase_d1_7b_dir / "engineering_annotation_validation.json"

    @property
    def engineering_annotation_report(self) -> Path:
        return self.phase_d1_7b_dir / "engineering_annotation_report.txt"

    @property
    def engineering_annotation_debug_dxf(self) -> Path:
        return self.phase_d1_7b_dir / "engineering_annotation_debug.dxf"

    # --- Phase D.1.7C ---
    @property
    def phase_d1_7c_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7C)

    @property
    def engineering_annotation_integrity_audit(self) -> Path:
        return self.phase_d1_7c_dir / "engineering_annotation_integrity_audit.json"

    @property
    def stirrup_integrity_report(self) -> Path:
        return self.phase_d1_7c_dir / "stirrup_integrity_report.json"

    @property
    def anchorage_integrity_report(self) -> Path:
        return self.phase_d1_7c_dir / "anchorage_integrity_report.json"

    @property
    def sfr_integrity_report(self) -> Path:
        return self.phase_d1_7c_dir / "sfr_integrity_report.json"

    @property
    def duplicate_engineering_annotations(self) -> Path:
        return self.phase_d1_7c_dir / "duplicate_engineering_annotations.json"

    @property
    def type_consistency_report(self) -> Path:
        return self.phase_d1_7c_dir / "type_consistency_report.json"

    @property
    def rejected_dataset_review(self) -> Path:
        return self.phase_d1_7c_dir / "rejected_dataset_review.json"

    @property
    def parser_readiness_assessment(self) -> Path:
        return self.phase_d1_7c_dir / "parser_readiness_assessment.json"

    @property
    def engineering_annotation_integrity_summary(self) -> Path:
        return self.phase_d1_7c_dir / "engineering_annotation_integrity_summary.json"

    @property
    def engineering_annotation_integrity_report(self) -> Path:
        return self.phase_d1_7c_dir / "engineering_annotation_integrity_report.txt"

    @property
    def engineering_annotation_integrity_validation(self) -> Path:
        return self.phase_d1_7c_dir / "engineering_annotation_integrity_validation.json"

    @property
    def engineering_annotation_integrity_debug_dxf(self) -> Path:
        return self.phase_d1_7c_dir / "engineering_annotation_integrity_debug.dxf"

    # --- Phase D.1.7D ---
    @property
    def phase_d1_7d_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7D)

    @property
    def engineering_annotations_final(self) -> Path:
        return self.phase_d1_7d_dir / "engineering_annotations_final.json"

    @property
    def fragment_resolution_report(self) -> Path:
        return self.phase_d1_7d_dir / "fragment_resolution_report.json"

    @property
    def sfr_parsing_policy(self) -> Path:
        return self.phase_d1_7d_dir / "sfr_parsing_policy.json"

    @property
    def d2_parser_policy(self) -> Path:
        return self.phase_d1_7d_dir / "d2_parser_policy.json"

    @property
    def engineering_dataset_final_validation(self) -> Path:
        return self.phase_d1_7d_dir / "engineering_dataset_final_validation.json"

    @property
    def engineering_dataset_final_summary(self) -> Path:
        return self.phase_d1_7d_dir / "engineering_dataset_final_summary.json"

    @property
    def engineering_dataset_final_report(self) -> Path:
        return self.phase_d1_7d_dir / "engineering_dataset_final_report.txt"

    @property
    def engineering_dataset_final_debug_dxf(self) -> Path:
        return self.phase_d1_7d_dir / "engineering_dataset_final_debug.dxf"

    def ensure_phase_dirs(self) -> None:
        """Create all phase output directories."""
        for phase in (
            PHASE_A,
            PHASE_B,
            PHASE_C,
            PHASE_C_DEBUG,
            PHASE_C5,
            PHASE_D1,
            PHASE_D1_1,
            PHASE_D1_2,
            PHASE_D1_3,
            PHASE_D1_3_1,
            PHASE_D1_4,
            PHASE_D1_5,
            PHASE_D1_6,
            PHASE_D1_6A,
            PHASE_D1_6B,
            PHASE_D1_7,
            PHASE_D1_7A,
            PHASE_D1_7B,
            PHASE_D1_7C,
            PHASE_D1_7D,
        ):
            phase_dir(self.root, phase).mkdir(parents=True, exist_ok=True)
