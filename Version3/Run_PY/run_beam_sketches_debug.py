"""Generate reinforcement sketch debug visualization."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.grid.beam_sketch_debug_exporter import BeamSketchDebugExporter

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")


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
        description="Export reinforcement sketch debug JSON and DXF.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help=f"Reinforcement DXF (default: {DEFAULT_DXF})",
    )
    parser.add_argument(
        "--cells",
        type=Path,
        default=paths.beam_cells,
        help=f"Ownership cells JSON for fallback (default: {paths.beam_cells})",
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

    if not args.dxf.exists():
        logger.error("DXF not found: {}", args.dxf)
        return 1

    try:
        result = BeamSketchDebugExporter().export_all(
            dxf_path=args.dxf,
            output_dir=paths.phase_c_debug_dir,
            cells_path=args.cells,
        )
        validation = result["validation"]
        logger.info(
            "Sketch debug export: {} sketch(s), status={}",
            validation["total_sketches"],
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
