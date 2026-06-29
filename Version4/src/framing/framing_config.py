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
            "reinforcement_status": "NOT_LOADED",
            "generate_debug_workspace": True,
            "default_floor": {
                "name": "Ground Floor",
                "slug": "GROUND_FLOOR",
            },
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
