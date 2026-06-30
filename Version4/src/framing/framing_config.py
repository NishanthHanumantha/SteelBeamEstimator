"""Load framing plan pipeline configuration."""

from pathlib import Path
from typing import Any

from loguru import logger

DEFAULT_CONFIG = Path("config/framing.yaml")


def _parse_value(raw: str) -> Any:
    value = raw.strip()
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if "," in value:
        return [part.strip() for part in value.split(",") if part.strip()]
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def load_framing_config(config_path: Path | str = DEFAULT_CONFIG) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "detect_connectivity": True,
        "detect_supports": True,
        "extract_dimensions": True,
        "generate_debug_dxf": True,
        "beam_line_layers": ["STR-BEAM"],
        "beam_label_layers": ["S-BEAM-IDEN"],
        "column_layers": ["S-COLUMN", "S-COL HATCH"],
        "wall_layers": ["Wall", "STR-RC WALL"],
        "min_beam_segment_mm": 500.0,
        "max_label_segment_distance_mm": 3000.0,
        "support_detection_tolerance_mm": 350.0,
        "connectivity_tolerance_mm": 250.0,
        "parallel_width_min_mm": 80.0,
        "parallel_width_max_mm": 800.0,
        "orthogonal_tolerance_deg": 5.0,
        "dimension_resolution": {
            "enable": True,
            "use_label_dimensions": True,
            "use_parallel_edge_measurement": True,
            "use_attribute_dimensions": True,
            "use_geometry_measurement": True,
            "geometry_tolerance_mm": 20.0,
            "minimum_reasonable_width": 100,
            "maximum_reasonable_width": 600,
            "minimum_reasonable_depth": 150,
            "maximum_reasonable_depth": 1500,
            "generate_debug_dimensions": True,
        },
        "support_resolution": {
            "enable": True,
            "detection_tolerance_mm": 350.0,
            "column_confidence": 0.97,
            "wall_confidence": 0.94,
            "beam_confidence": 0.93,
            "slab_edge_confidence": 0.91,
            "free_end_confidence": 0.85,
            "unknown_confidence": 0.0,
            "slab_edge_layers": [],
            "generate_debug_supports": True,
        },
        "beam_section": {
            "enable": True,
            "deep_section_ratio": 2.0,
            "property_tolerance": 0.5,
            "generate_debug_section": True,
        },
        "engineering_length": {
            "enable": True,
            "beam_half_width_fallback_mm": 100.0,
            "effective_span_min_face_confidence": 0.85,
            "generate_debug_lengths": True,
        },
        "knowledge_graph": {
            "enable": True,
            "junction_tolerance_mm": 250.0,
            "continuous_angle_tolerance_deg": 5.0,
            "phase_e_rules_path": "data/output/phase_e/general_notes_engineering_rules.json",
            "generate_debug_graph": True,
        },
        "engineering_context": {
            "enable": True,
            "knowledge_version": "1.0",
            "generate_debug_context": True,
            "generate_debug_dependencies": True,
            "generate_debug_project_graph": True,
        },
        "workspace": {
            "enable": True,
            "generate_debug_workspace": True,
            "default_floor": {
                "name": "Ground Floor",
                "slug": "GROUND_FLOOR",
            },
        },
        "reinforcement_loading": {
            "enable": True,
            "generate_debug_reinforcement": True,
        },
        "reinforcement_drawings": {
            "ground_floor": "data/framing/Beam_Reinforcement_Details.dxf",
        },
        "drawing_identity": {
            "enable": True,
            "generate_debug_drawing_identity": True,
            "general_notes_path": "data/general_notes/SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf",
        },
        "drawing_set": {
            "enable": True,
            "generate_debug_drawing_set": True,
        },
        "drawing_set_lifecycle": {
            "enable": True,
            "generate_debug_drawing_set_state": True,
        },
        "reinforcement_geometry": {
            "enable": True,
            "generate_debug_reinforcement_geometry": True,
            "region_header_layers": ["SEC TEXT", "S-BEAM-IDEN"],
            "row_tolerance_mm": 2500.0,
            "header_merge_distance_mm": 4000.0,
            "detail_band_below_mm": 4500.0,
            "detail_band_above_mm": 1500.0,
            "strip_width_mm": 300.0,
            "continuity_gap_mm": 800.0,
            "geometry_overlap_ratio": 0.12,
            "shared_bar_threshold": 1,
            "shared_leader_threshold": 0.3,
            "whitespace_threshold": 0,
            "region_growth_radius": 12000.0,
            "region_margin_y_above_mm": 2500.0,
            "region_margin_y_below_mm": 9000.0,
            "allow_multibeam_regions": True,
            "continuity_min_score": 0.75,
            "min_strip_entities_for_continuity": 4,
            "duplicate_mark_detection": True,
            "enable_multiview_detection": True,
            "duplicate_merge_distance_mm": 250.0,
            "min_duplicate_confidence": 0.85,
            "reinforcement_layers": ["-STR-REINF", "-STR-BEAM", "-S-STIRUP"],
            "stirrup_layers": ["-S-STIRUP"],
            "beam_layers": ["-STR-BEAM"],
            "arrow_layers": ["-S-ARROW"],
            "sketch_cluster_tolerance_mm": 1200.0,
            "sketch_min_geometry_count": 2,
            "detail_context_enable": True,
            "detail_context_generate_debug": True,
            "detail_identity_enable": True,
            "detail_identity_generate_debug": True,
            "beam_candidate_enable": True,
            "beam_candidate_generate_debug": True,
            "match_decision_enable": True,
            "match_decision_generate_debug": True,
            "match_decision_quality_enable": True,
            "match_decision_quality_generate_debug": True,
            "beam_matching_enable": True,
            "beam_matching_generate_debug": True,
            "ownership_resolver_enable": True,
            "ownership_resolver_generate_debug": True,
        },
    }
    path = Path(config_path)
    if not path.exists():
        logger.warning("Framing config not found — using defaults: {}", path)
        return defaults

    data = dict(defaults)
    nested_blocks = {
        "dimension_resolution": dict(defaults["dimension_resolution"]),
        "support_resolution": dict(defaults["support_resolution"]),
        "beam_section": dict(defaults["beam_section"]),
        "engineering_length": dict(defaults["engineering_length"]),
        "knowledge_graph": dict(defaults["knowledge_graph"]),
        "engineering_context": dict(defaults["engineering_context"]),
        "workspace": dict(defaults["workspace"]),
        "reinforcement_loading": dict(defaults["reinforcement_loading"]),
        "reinforcement_drawings": dict(defaults["reinforcement_drawings"]),
            "drawing_identity": dict(defaults["drawing_identity"]),
            "drawing_set": dict(defaults["drawing_set"]),
            "drawing_set_lifecycle": dict(defaults["drawing_set_lifecycle"]),
            "reinforcement_geometry": dict(defaults["reinforcement_geometry"]),
        }
    active_block: str | None = None
    block_indent = 0

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue

        stripped = raw_line.lstrip()
        indent = len(raw_line) - len(stripped)
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key in nested_blocks and not value:
            active_block = key
            block_indent = indent
            continue

        if active_block and indent > block_indent:
            nested_blocks[active_block][key] = _parse_value(value)
            continue

        active_block = None
        data[key] = _parse_value(value)

    data.update(nested_blocks)
    return data
