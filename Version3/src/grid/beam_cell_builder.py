"""Phase C — build beam ownership cells from reinforcement headers."""

from typing import List, Tuple, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key, estimate_text_half_width
from src.reinforcement.header_extractor import ReinforcementHeader

ROW_Y_TOLERANCE_MM = 1000.0
DEFAULT_ROW_HALF_HEIGHT_MM = 5000.0
DEFAULT_EDGE_MARGIN_MM = 5000.0


class BeamCell(TypedDict):
    beam_mark: str
    row_id: int
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    header_x: float
    header_y: float


class _HeaderExtents:
    __slots__ = ("header", "x_left", "x_right")

    def __init__(self, header: ReinforcementHeader) -> None:
        self.header = header
        label = f"{header['beam_mark']}({header['width_mm']}X{header['depth_mm']})"
        half_width = estimate_text_half_width(label)
        self.x_left = header["x"] - half_width
        self.x_right = header["x"] + half_width


class BeamCellBuilder:
    """Cluster headers into rows and assign horizontal ownership cells."""

    def __init__(
        self,
        row_y_tolerance_mm: float = ROW_Y_TOLERANCE_MM,
        row_half_height_mm: float = DEFAULT_ROW_HALF_HEIGHT_MM,
        edge_margin_mm: float = DEFAULT_EDGE_MARGIN_MM,
    ) -> None:
        self._row_y_tolerance = row_y_tolerance_mm
        self._row_half_height = row_half_height_mm
        self._edge_margin = edge_margin_mm

    def build(self, headers: List[ReinforcementHeader]) -> List[BeamCell]:
        if not headers:
            return []

        rows = self._cluster_rows(headers)
        logger.info("Built {} header row(s) from {} beam(s)", len(rows), len(headers))

        cells: List[BeamCell] = []
        row_ys = [sum(item.header["y"] for item in row) / len(row) for row in rows]
        row_bounds = self._row_vertical_bounds(row_ys)

        for row_index, row in enumerate(rows, start=1):
            row.sort(key=lambda item: item.header["x"])
            x_bounds = self._horizontal_bounds(row)
            ymin, ymax = row_bounds[row_index - 1]

            for item, (xmin, xmax) in zip(row, x_bounds):
                header = item.header
                cells.append(
                    BeamCell(
                        beam_mark=header["beam_mark"],
                        row_id=row_index,
                        xmin=round(xmin, 3),
                        xmax=round(xmax, 3),
                        ymin=round(ymin, 3),
                        ymax=round(ymax, 3),
                        header_x=round(header["x"], 3),
                        header_y=round(header["y"], 3),
                    )
                )

        cells.sort(key=lambda cell: (cell["row_id"], beam_mark_sort_key(cell["beam_mark"])))
        return cells

    def _cluster_rows(
        self, headers: List[ReinforcementHeader]
    ) -> List[List[_HeaderExtents]]:
        sorted_headers = sorted(
            [_HeaderExtents(header) for header in headers],
            key=lambda item: (-item.header["y"], item.header["x"]),
        )

        rows: List[List[_HeaderExtents]] = []
        for item in sorted_headers:
            placed = False
            for row in rows:
                row_y = sum(ext.header["y"] for ext in row) / len(row)
                if abs(item.header["y"] - row_y) <= self._row_y_tolerance:
                    row.append(item)
                    placed = True
                    break
            if not placed:
                rows.append([item])

        rows.sort(
            key=lambda row: sum(ext.header["y"] for ext in row) / len(row),
            reverse=True,
        )
        return rows

    def _row_vertical_bounds(
        self, row_ys: List[float]
    ) -> List[Tuple[float, float]]:
        bounds: List[Tuple[float, float]] = []
        for index, row_y in enumerate(row_ys):
            if index == 0:
                ymax = row_y + self._row_half_height
            else:
                ymax = (row_y + row_ys[index - 1]) / 2.0

            if index == len(row_ys) - 1:
                ymin = row_y - self._row_half_height
            else:
                ymin = (row_y + row_ys[index + 1]) / 2.0

            bounds.append((ymin, ymax))
        return bounds

    def _horizontal_bounds(
        self, row: List[_HeaderExtents]
    ) -> List[Tuple[float, float]]:
        if not row:
            return []

        bounds: List[Tuple[float, float]] = []
        for index, item in enumerate(row):
            if index == 0:
                xmin = item.x_left - self._edge_margin
            else:
                left = row[index - 1]
                xmin = (left.x_right + item.x_left) / 2.0

            if index == len(row) - 1:
                xmax = item.x_right + self._edge_margin
            else:
                right = row[index + 1]
                xmax = (item.x_right + right.x_left) / 2.0

            bounds.append((xmin, xmax))

        return bounds
