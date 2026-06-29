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
PHASE_D1_7E = "phase_d17e"
PHASE_D1_7F = "phase_d17f"
PHASE_D1_7G = "phase_d17g"
PHASE_D2 = "phase_d2"
PHASE_D3 = "phase_d3"
PHASE_D31 = "phase_d31"
PHASE_D32 = "phase_d32"
PHASE_D33 = "phase_d33"
PHASE_D4 = "phase_d4"
PHASE_D41 = "phase_d41"
PHASE_D42 = "phase_d42"
PHASE_E = "phase_e"
PHASE_F = "phase_f"
PHASE_F_1_FRAMING_GEOMETRY = "f_1_framing_geometry"
PHASE_F_2_DIMENSION_RESOLUTION = "f_2_dimension_resolution"
PHASE_F_3_SUPPORT_AND_SECTION = "f_3_support_and_section"
PHASE_F_4_ENGINEERING_LENGTH = "f_4_engineering_length"
PHASE_F_5_KNOWLEDGE_GRAPH = "f_5_knowledge_graph_and_coordinates"
PHASE_F_6_ENGINEERING_CONTEXT = "f_6_engineering_context"
PHASE_F_7_PROJECT_WORKSPACE = "f_7_project_workspace"


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

    # --- Phase D.1.7E ---
    @property
    def phase_d17e_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7E)

    @property
    def validated_sfr_annotations(self) -> Path:
        return self.phase_d17e_dir / "validated_sfr_annotations.json"

    @property
    def validated_annotations_master(self) -> Path:
        return self.phase_d17e_dir / "validated_annotations_master.json"

    @property
    def sfr_validation_report(self) -> Path:
        return self.phase_d17e_dir / "sfr_validation_report.json"

    @property
    def sfr_validation_report_txt(self) -> Path:
        return self.phase_d17e_dir / "sfr_validation_report.txt"

    @property
    def sfr_ownership_debug_dxf(self) -> Path:
        return self.phase_d17e_dir / "ownership_debug.dxf"

    # --- Phase D.1.7F ---
    @property
    def phase_d17f_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7F)

    @property
    def engineering_annotations_semantic(self) -> Path:
        return self.phase_d17f_dir / "engineering_annotations_semantic.json"

    @property
    def sfr_semantic_validation(self) -> Path:
        return self.phase_d17f_dir / "sfr_semantic_validation.json"

    @property
    def sfr_semantic_summary(self) -> Path:
        return self.phase_d17f_dir / "sfr_semantic_summary.json"

    @property
    def sfr_semantic_report_txt(self) -> Path:
        return self.phase_d17f_dir / "sfr_semantic_report.txt"

    @property
    def sfr_semantic_debug_dxf(self) -> Path:
        return self.phase_d17f_dir / "sfr_semantic_debug.dxf"

    @property
    def engineering_dataset_phase_d17f(self) -> Path:
        return self.phase_d17f_dir / "engineering_dataset_phase_d17f.json"

    # --- Phase D.1.7G ---
    @property
    def phase_d17g_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D1_7G)

    @property
    def sfr_discovery_inventory(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_inventory.json"

    @property
    def sfr_discovery_expected_vs_found(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_expected_vs_found.json"

    @property
    def sfr_discovery_pipeline_loss(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_pipeline_loss.json"

    @property
    def sfr_discovery_root_cause(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_root_cause.json"

    @property
    def sfr_discovery_summary(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_summary.json"

    @property
    def sfr_discovery_validation(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_validation.json"

    @property
    def sfr_discovery_report_txt(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_report.txt"

    @property
    def sfr_discovery_debug_dxf(self) -> Path:
        return self.phase_d17g_dir / "sfr_discovery_debug.dxf"

    # --- Phase D.2 ---
    @property
    def phase_d2_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D2)

    @property
    def parsed_bars(self) -> Path:
        return self.phase_d2_dir / "parsed_bars.json"

    @property
    def parsed_stirrups(self) -> Path:
        return self.phase_d2_dir / "parsed_stirrups.json"

    @property
    def parsed_anchorage(self) -> Path:
        return self.phase_d2_dir / "parsed_anchorage.json"

    @property
    def parsed_side_face_reinf(self) -> Path:
        return self.phase_d2_dir / "parsed_side_face_reinf.json"

    @property
    def parsed_annotations_master(self) -> Path:
        return self.phase_d2_dir / "parsed_annotations_master.json"

    @property
    def annotation_parsing_summary(self) -> Path:
        return self.phase_d2_dir / "annotation_parsing_summary.json"

    @property
    def annotation_parsing_validation(self) -> Path:
        return self.phase_d2_dir / "annotation_parsing_validation.json"

    @property
    def annotation_parsing_report(self) -> Path:
        return self.phase_d2_dir / "annotation_parsing_report.txt"

    @property
    def annotation_parsing_debug_dxf(self) -> Path:
        return self.phase_d2_dir / "annotation_parsing_debug.dxf"

    # --- Phase D.3 ---
    @property
    def phase_d3_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D3)

    @property
    def beam_groups(self) -> Path:
        return self.phase_d3_dir / "beam_groups.json"

    @property
    def beam_group_summary(self) -> Path:
        return self.phase_d3_dir / "beam_group_summary.json"

    @property
    def shared_annotations(self) -> Path:
        return self.phase_d3_dir / "shared_annotations.json"

    @property
    def group_annotation_ownership(self) -> Path:
        return self.phase_d3_dir / "group_annotation_ownership.json"

    @property
    def expanded_group_annotations(self) -> Path:
        return self.phase_d3_dir / "expanded_group_annotations.json"

    @property
    def beam_group_validation(self) -> Path:
        return self.phase_d3_dir / "beam_group_validation.json"

    @property
    def beam_group_report_txt(self) -> Path:
        return self.phase_d3_dir / "beam_group_report.txt"

    @property
    def beam_group_debug_dxf(self) -> Path:
        return self.phase_d3_dir / "beam_group_debug.dxf"

    # --- Phase D.3.1 ---
    @property
    def phase_d31_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D31)

    @property
    def beam_group_confidence(self) -> Path:
        return self.phase_d31_dir / "beam_group_confidence.json"

    @property
    def beam_group_validation_v2(self) -> Path:
        return self.phase_d31_dir / "beam_group_validation_v2.json"

    @property
    def beam_group_validation_report_txt(self) -> Path:
        return self.phase_d31_dir / "beam_group_validation_report.txt"

    @property
    def beam_group_validation_debug_dxf(self) -> Path:
        return self.phase_d31_dir / "beam_group_validation_debug.dxf"

    # --- Phase D.3.2 ---
    @property
    def phase_d32_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D32)

    @property
    def detail_regions(self) -> Path:
        return self.phase_d32_dir / "detail_regions.json"

    @property
    def beam_groups_refined(self) -> Path:
        return self.phase_d32_dir / "beam_groups_refined.json"

    @property
    def detail_region_validation(self) -> Path:
        return self.phase_d32_dir / "detail_region_validation.json"

    @property
    def detail_region_summary(self) -> Path:
        return self.phase_d32_dir / "detail_region_summary.json"

    @property
    def detail_region_report_txt(self) -> Path:
        return self.phase_d32_dir / "detail_region_report.txt"

    @property
    def detail_region_debug_dxf(self) -> Path:
        return self.phase_d32_dir / "detail_region_debug.dxf"

    # --- Phase D.3.3 ---
    @property
    def phase_d33_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D33)

    @property
    def annotation_ownership_master(self) -> Path:
        return self.phase_d33_dir / "annotation_ownership_master.json"

    @property
    def annotation_region_mapping(self) -> Path:
        return self.phase_d33_dir / "annotation_region_mapping.json"

    @property
    def annotation_sketch_mapping(self) -> Path:
        return self.phase_d33_dir / "annotation_sketch_mapping.json"

    @property
    def ownership_confidence(self) -> Path:
        return self.phase_d33_dir / "ownership_confidence.json"

    @property
    def ownership_conflicts(self) -> Path:
        return self.phase_d33_dir / "ownership_conflicts.json"

    @property
    def ownership_validation(self) -> Path:
        return self.phase_d33_dir / "ownership_validation.json"

    @property
    def ownership_summary(self) -> Path:
        return self.phase_d33_dir / "ownership_summary.json"

    @property
    def ownership_report_txt(self) -> Path:
        return self.phase_d33_dir / "ownership_report.txt"

    @property
    def ownership_debug_dxf(self) -> Path:
        return self.phase_d33_dir / "ownership_debug.dxf"

    # --- Phase D.4 ---
    @property
    def phase_d4_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D4)

    @property
    def engineering_objects(self) -> Path:
        return self.phase_d4_dir / "engineering_objects.json"

    @property
    def parsed_longitudinal_bars(self) -> Path:
        return self.phase_d4_dir / "parsed_longitudinal_bars.json"

    @property
    def parsed_stirrups_d4(self) -> Path:
        return self.phase_d4_dir / "parsed_stirrups.json"

    @property
    def parsed_anchorage_d4(self) -> Path:
        return self.phase_d4_dir / "parsed_anchorage.json"

    @property
    def parsed_sfr_d4(self) -> Path:
        return self.phase_d4_dir / "parsed_sfr.json"

    @property
    def engineering_parser_summary(self) -> Path:
        return self.phase_d4_dir / "engineering_parser_summary.json"

    @property
    def engineering_parser_validation(self) -> Path:
        return self.phase_d4_dir / "engineering_parser_validation.json"

    @property
    def engineering_parser_report_txt(self) -> Path:
        return self.phase_d4_dir / "engineering_parser_report.txt"

    @property
    def engineering_parser_debug_dxf(self) -> Path:
        return self.phase_d4_dir / "engineering_parser_debug.dxf"

    # --- Phase D.4.1 ---
    @property
    def phase_d41_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D41)

    @property
    def reinforcement_classification(self) -> Path:
        return self.phase_d41_dir / "reinforcement_classification.json"

    @property
    def reinforcement_summary(self) -> Path:
        return self.phase_d41_dir / "reinforcement_summary.json"

    @property
    def reinforcement_validation(self) -> Path:
        return self.phase_d41_dir / "reinforcement_validation.json"

    @property
    def reinforcement_report_txt(self) -> Path:
        return self.phase_d41_dir / "reinforcement_report.txt"

    @property
    def reinforcement_debug_dxf(self) -> Path:
        return self.phase_d41_dir / "reinforcement_debug.dxf"

    # --- Phase D.4.2 ---
    @property
    def phase_d42_dir(self) -> Path:
        return phase_dir(self.root, PHASE_D42)

    @property
    def longitudinal_geometry_resolution(self) -> Path:
        return self.phase_d42_dir / "longitudinal_geometry_resolution.json"

    @property
    def engineering_objects_enriched(self) -> Path:
        return self.phase_d42_dir / "engineering_objects_enriched.json"

    @property
    def phase_d42_summary(self) -> Path:
        return self.phase_d42_dir / "phase_d42_summary.json"

    @property
    def phase_d42_validation(self) -> Path:
        return self.phase_d42_dir / "phase_d42_validation.json"

    @property
    def phase_d42_debug_dxf(self) -> Path:
        return self.phase_d42_dir / "phase_d42_debug.dxf"


    @property
    def phase_f_dir(self) -> Path:
        return phase_dir(self.root, PHASE_F)

    @property
    def phase_f_1_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_1_FRAMING_GEOMETRY

    @property
    def phase_f_2_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_2_DIMENSION_RESOLUTION

    @property
    def phase_f_3_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_3_SUPPORT_AND_SECTION

    @property
    def phase_f_4_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_4_ENGINEERING_LENGTH

    @property
    def phase_f_5_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_5_KNOWLEDGE_GRAPH

    @property
    def phase_f_6_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_6_ENGINEERING_CONTEXT

    @property
    def phase_f_7_dir(self) -> Path:
        return self.phase_f_dir / PHASE_F_7_PROJECT_WORKSPACE

    @property
    def beam_geometry_model(self) -> Path:
        return self.phase_f_dir / "beam_geometry_model.json"

    @property
    def beam_centerlines(self) -> Path:
        return self.phase_f_1_dir / "beam_centerlines.json"

    @property
    def beam_dimensions(self) -> Path:
        return self.phase_f_1_dir / "beam_dimensions.json"

    @property
    def beam_connectivity(self) -> Path:
        return self.phase_f_1_dir / "beam_connectivity.json"

    @property
    def beam_supports(self) -> Path:
        return self.phase_f_1_dir / "beam_supports.json"

    @property
    def phase_f_summary(self) -> Path:
        return self.phase_f_dir / "phase_f_summary.json"

    @property
    def phase_f_validation(self) -> Path:
        return self.phase_f_1_dir / "phase_f_validation.json"

    @property
    def phase_f_debug_dxf(self) -> Path:
        return self.phase_f_dir / "phase_f_debug.dxf"

    @property
    def beam_dimensions_resolved(self) -> Path:
        return self.phase_f_2_dir / "beam_dimensions_resolved.json"

    @property
    def phase_f_dimension_validation(self) -> Path:
        return self.phase_f_2_dir / "phase_f_dimension_validation.json"

    @property
    def beam_sections(self) -> Path:
        return self.phase_f_3_dir / "beam_sections.json"

    @property
    def support_graph(self) -> Path:
        return self.phase_f_3_dir / "support_graph.json"

    @property
    def structural_nodes(self) -> Path:
        return self.phase_f_3_dir / "structural_nodes.json"

    @property
    def phase_f_support_validation(self) -> Path:
        return self.phase_f_3_dir / "phase_f_support_validation.json"

    @property
    def phase_f_section_validation(self) -> Path:
        return self.phase_f_3_dir / "phase_f_section_validation.json"

    @property
    def beam_length_model(self) -> Path:
        return self.phase_f_4_dir / "beam_length_model.json"

    @property
    def clear_spans(self) -> Path:
        return self.phase_f_4_dir / "clear_spans.json"

    @property
    def effective_spans(self) -> Path:
        return self.phase_f_4_dir / "effective_spans.json"

    @property
    def bearing_lengths(self) -> Path:
        return self.phase_f_4_dir / "bearing_lengths.json"

    @property
    def phase_f_length_validation(self) -> Path:
        return self.phase_f_4_dir / "phase_f_length_validation.json"

    @property
    def framing_knowledge_graph(self) -> Path:
        return self.phase_f_5_dir / "framing_knowledge_graph.json"

    @property
    def engineering_coordinate_system(self) -> Path:
        return self.phase_f_5_dir / "engineering_coordinate_system.json"

    @property
    def beam_stationing(self) -> Path:
        return self.phase_f_5_dir / "beam_stationing.json"

    @property
    def beam_relationships(self) -> Path:
        return self.phase_f_5_dir / "beam_relationships.json"

    @property
    def engineering_status_registry(self) -> Path:
        return self.phase_f_5_dir / "engineering_status_registry.json"

    @property
    def phase_f_graph_validation(self) -> Path:
        return self.phase_f_5_dir / "phase_f_graph_validation.json"

    @property
    def beam_engineering_context(self) -> Path:
        return self.phase_f_6_dir / "beam_engineering_context.json"

    @property
    def engineering_context_registry(self) -> Path:
        return self.phase_f_6_dir / "engineering_context_registry.json"

    @property
    def engineering_dependency_graph(self) -> Path:
        return self.phase_f_6_dir / "engineering_dependency_graph.json"

    @property
    def engineering_dependency_registry(self) -> Path:
        return self.phase_f_6_dir / "engineering_dependency_registry.json"

    @property
    def project_engineering_graph(self) -> Path:
        return self.phase_f_6_dir / "project_engineering_graph.json"

    @property
    def phase_f_context_validation(self) -> Path:
        return self.phase_f_6_dir / "phase_f_context_validation.json"

    @property
    def project_workspace(self) -> Path:
        return self.phase_f_7_dir / "project_workspace.json"

    @property
    def project_registry(self) -> Path:
        return self.phase_f_7_dir / "project_registry.json"

    @property
    def floor_registry(self) -> Path:
        return self.phase_f_7_dir / "floor_registry.json"

    @property
    def engineering_services_registry(self) -> Path:
        return self.phase_f_7_dir / "engineering_services_registry.json"

    @property
    def workspace_manager(self) -> Path:
        return self.phase_f_7_dir / "workspace_manager.json"

    @property
    def phase_f_workspace_validation(self) -> Path:
        return self.phase_f_7_dir / "phase_f_workspace_validation.json"

    def ensure_phase_f_subdirs(self) -> None:
        """Create Phase F root and F.1–F.7 subfolders."""
        self.phase_f_dir.mkdir(parents=True, exist_ok=True)
        for subdir in (
            PHASE_F_1_FRAMING_GEOMETRY,
            PHASE_F_2_DIMENSION_RESOLUTION,
            PHASE_F_3_SUPPORT_AND_SECTION,
            PHASE_F_4_ENGINEERING_LENGTH,
            PHASE_F_5_KNOWLEDGE_GRAPH,
            PHASE_F_6_ENGINEERING_CONTEXT,
            PHASE_F_7_PROJECT_WORKSPACE,
        ):
            (self.phase_f_dir / subdir).mkdir(parents=True, exist_ok=True)

    # --- Phase E ---
    @property
    def phase_e_dir(self) -> Path:
        return phase_dir(self.root, PHASE_E)

    @property
    def general_notes_engineering_rules(self) -> Path:
        return self.phase_e_dir / "general_notes_engineering_rules.json"

    @property
    def development_length_table(self) -> Path:
        return self.phase_e_dir / "development_length_table.json"

    @property
    def cover_table(self) -> Path:
        return self.phase_e_dir / "cover_table.json"

    @property
    def material_specifications(self) -> Path:
        return self.phase_e_dir / "material_specifications.json"

    @property
    def engineering_constants(self) -> Path:
        return self.phase_e_dir / "engineering_constants.json"

    @property
    def phase_e_summary(self) -> Path:
        return self.phase_e_dir / "phase_e_summary.json"

    @property
    def phase_e_validation(self) -> Path:
        return self.phase_e_dir / "phase_e_validation.json"

    @property
    def phase_e_debug_dxf(self) -> Path:
        return self.phase_e_dir / "phase_e_debug.dxf"

    @property
    def project_defaults(self) -> Path:
        return self.phase_e_dir / "project_defaults.json"

    @property
    def project_engineering_report(self) -> Path:
        return self.phase_e_dir / "project_engineering_report.json"

    @property
    def estimator_rules(self) -> Path:
        return self.phase_e_dir / "estimator_rules.json"

    @property
    def project_metadata(self) -> Path:
        return self.phase_e_dir / "project_metadata.json"

    @property
    def engineering_value_registry(self) -> Path:
        return self.phase_e_dir / "engineering_value_registry.json"

    @property
    def engineering_traceability_report(self) -> Path:
        return self.phase_e_dir / "engineering_traceability_report.json"

    def engineering_objects_for_classification(self) -> Path:
        """Prefer D.4.2 enriched objects when Phase D.4.2 has been run."""
        enriched = self.engineering_objects_enriched
        if enriched.exists():
            return enriched
        return self.engineering_objects

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
            PHASE_D1_7E,
            PHASE_D1_7F,
            PHASE_D1_7G,
            PHASE_D2,
            PHASE_D3,
            PHASE_D31,
            PHASE_D32,
            PHASE_D33,
            PHASE_D4,
            PHASE_D41,
            PHASE_D42,
            PHASE_E,
            PHASE_F,
        ):
            phase_dir(self.root, phase).mkdir(parents=True, exist_ok=True)
