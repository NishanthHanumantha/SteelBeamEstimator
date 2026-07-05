"""Excel export types — Phase I.17."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import FrozenSet

PREFIX_EXCEL_EXPORT = "EXCEL_EXPORT"
PREFIX_EXCEL_EXPORT_REGISTRY = "EXCEL_EXPORT_REGISTRY"
NAMESPACE_EXCEL_EXPORT = "EXCEL_EXPORT"

CREATED_PHASE = "I.17"
ENGINE_NAME = "EXCEL_EXPORT_ENGINE"
DETERMINATION_METHOD = "TEMPLATE_POPULATE"
MODEL_VERSION = "5.21.0"

DEFAULT_TEMPLATE_DIR = Path("data") / "Excel_Presentation_Format"
DEFAULT_TEMPLATE_FILENAME = "Galera_SteelBeamEst_SHR&OHT_TopFramingPan_OutputFormat.xlsx"
OUTPUT_WORKBOOK_FILENAME = "Beam_Reinforcement_Schedule.xlsx"
DEFAULT_LOCATION_CODE = "TF"

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_template",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


class ExportState(str, Enum):
    """Excel export lifecycle state."""

    SUCCESS = "SUCCESS"
    FALLBACK = "FALLBACK"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"


VALID_EXPORT_STATES: FrozenSet[str] = frozenset(item.value for item in ExportState)


def format_excel_export_id(sequence: int) -> str:
    return f"{PREFIX_EXCEL_EXPORT}::{sequence:06d}"


def format_excel_export_registry_id() -> str:
    return PREFIX_EXCEL_EXPORT_REGISTRY


def default_template_path(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    return root / DEFAULT_TEMPLATE_DIR / DEFAULT_TEMPLATE_FILENAME
