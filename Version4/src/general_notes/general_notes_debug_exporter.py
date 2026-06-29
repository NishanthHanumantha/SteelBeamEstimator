"""Phase E — DXF debug layers for extracted General Notes tables."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import ezdxf
from loguru import logger

from src.general_notes.general_notes_parser import TextAnnotation
from src.general_notes.table_extractor import CoverRow, GridTable

_LAYER_TABLES = "DEBUG_GENERAL_NOTES_TABLES"
_LAYER_RULES = "DEBUG_ENGINEERING_RULES"
_LAYER_LD = "DEBUG_DEVELOPMENT_TABLE"
_LAYER_COVER = "DEBUG_COVER_TABLE"
_LAYER_ACTIVE_LD = "DEBUG_ACTIVE_LD_TABLE"
_LAYER_DEFAULTS = "DEBUG_PROJECT_DEFAULTS"
_LAYER_MEMBER_NORM = "DEBUG_MEMBER_NORMALIZATION"


class GeneralNotesDebugExporter:
    """Highlight extracted table regions in a debug DXF."""

    def export(
        self,
        source_texts: List[TextAnnotation],
        ld_grids: List[GridTable],
        cover_rows: List[CoverRow],
        rule_highlights: List[TextAnnotation],
        output_path: Path,
        active_ld_grid: Optional[GridTable] = None,
        project_defaults: Optional[dict[str, Any]] = None,
        normalized_cover: Optional[List[dict[str, Any]]] = None,
    ) -> None:
        doc = ezdxf.new("R2010")
        for layer in (
            _LAYER_TABLES,
            _LAYER_RULES,
            _LAYER_LD,
            _LAYER_COVER,
            _LAYER_ACTIVE_LD,
            _LAYER_DEFAULTS,
            _LAYER_MEMBER_NORM,
        ):
            if layer not in doc.layers:
                doc.layers.add(layer)

        msp = doc.modelspace()

        for grid in ld_grids:
            self._draw_ld_grid(msp, grid, _LAYER_LD, 3)
        if active_ld_grid:
            self._draw_ld_grid(msp, active_ld_grid, _LAYER_ACTIVE_LD, 1)
            msp.add_text(
                "ACTIVE LD TABLE",
                dxfattribs={
                    "layer": _LAYER_ACTIVE_LD,
                    "height": 14.0,
                    "insert": (1545, active_ld_grid.metadata.get("anchor_y", 820) + 20),
                    "color": 1,
                },
            )

        for row in cover_rows:
            self._draw_cover_row(msp, row, _LAYER_COVER)

        if normalized_cover:
            for index, row in enumerate(normalized_cover):
                y = row.get("y_position", 600 - index * 12)
                msp.add_text(
                    f"{row.get('normalized_member_type')} <= {row.get('original_member_type', '')[:25]}",
                    dxfattribs={
                        "layer": _LAYER_MEMBER_NORM,
                        "height": 8.0,
                        "insert": (1480, float(y)),
                        "color": 6,
                    },
                )

        if project_defaults:
            y_text = 990.0
            for key, value in project_defaults.items():
                msp.add_text(
                    f"{key}: {value}",
                    dxfattribs={
                        "layer": _LAYER_DEFAULTS,
                        "height": 10.0,
                        "insert": (500, y_text),
                        "color": 4,
                    },
                )
                y_text -= 14.0

        for ann in rule_highlights:
            msp.add_circle(
                (ann.x, ann.y),
                15.0,
                dxfattribs={"layer": _LAYER_RULES, "color": 2},
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(str(output_path))
        logger.info("Phase E debug DXF written to {}", output_path)

    def _draw_ld_grid(
        self,
        msp: Any,
        grid: GridTable,
        layer: str,
        color: int,
    ) -> None:
        for row_y in grid.row_positions:
            msp.add_line(
                (1545, row_y),
                (1650, row_y),
                dxfattribs={"layer": layer, "color": color},
            )
        for col_x in grid.column_positions:
            msp.add_line(
                (col_x, grid.row_positions[-1] if grid.row_positions else 780),
                (col_x, grid.row_positions[0] if grid.row_positions else 850),
                dxfattribs={"layer": layer, "color": color},
            )
        for row_index, row_y in enumerate(grid.row_positions):
            label = grid.row_labels[row_index]
            msp.add_text(
                f"D{label}",
                dxfattribs={
                    "layer": layer,
                    "height": 10.0,
                    "insert": (1540, row_y),
                    "color": color,
                },
            )
            for col_index, col_x in enumerate(grid.column_positions):
                value = grid.values[row_index][col_index]
                if value is None:
                    continue
                msp.add_text(
                    str(value),
                    dxfattribs={
                        "layer": layer,
                        "height": 8.0,
                        "insert": (col_x - 5, row_y - 3),
                        "color": color,
                    },
                )
        msp.add_text(
            grid.anchor_text,
            dxfattribs={
                "layer": _LAYER_TABLES,
                "height": 12.0,
                "insert": (1545, grid.metadata.get("anchor_y", 820)),
                "color": 1,
            },
        )

    def _draw_cover_row(self, msp: Any, row: CoverRow, layer: str) -> None:
        msp.add_circle(
            (1612, row.y_position),
            12.0,
            dxfattribs={"layer": layer, "color": 5},
        )
        msp.add_text(
            f"{row.member_type[:30]} = {row.cover_mm}mm",
            dxfattribs={
                "layer": layer,
                "height": 8.0,
                "insert": (1555, row.y_position - 4),
                "color": 5,
            },
        )
