"""Generate beam cell debug outputs (JSON + DXF) from beam_cells.json."""

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.grid.beam_cell_debug_exporter import BeamCellDebugExporter


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>",
        level=level,
    )


def parse_args() -> argparse.Namespace:
    paths = OutputPaths()
    parser = argparse.ArgumentParser(
        description="Export beam ownership cell debug artifacts.",
    )
    parser.add_argument(
        "-i",
        "--cells",
        type=Path,
        default=paths.beam_cells,
        help=f"Input beam_cells.json (default: {paths.beam_cells})",
    )
    parser.add_argument(
        "--headers",
        type=Path,
        default=paths.reinforcement_headers,
        help=f"Optional reinforcement_headers.json (default: {paths.reinforcement_headers})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT,
        help=f"Output root directory (default: {OUTPUT_ROOT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    paths = OutputPaths(args.output_dir)

    if not args.cells.exists():
        logger.error("beam_cells.json not found: {}", args.cells)
        return 1

    try:
        exporter = BeamCellDebugExporter()
        result = exporter.export_all(
            cells_path=args.cells,
            output_dir=paths.phase_c_debug_dir,
            headers_path=args.headers,
        )
        validation = result["validation"]
        logger.info(
            "Debug export complete: {} cell(s), status={}",
            result["total_cells"],
            validation["status"],
        )
        return 0
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
