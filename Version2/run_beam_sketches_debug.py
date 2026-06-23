"""Generate reinforcement sketch debug visualization."""

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.grid.beam_sketch_debug_exporter import BeamSketchDebugExporter

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")
DEFAULT_OUTPUT_DIR = Path("data/output")
DEFAULT_CELLS = DEFAULT_OUTPUT_DIR / "beam_cells.json"


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
        default=DEFAULT_CELLS,
        help=f"Ownership cells JSON for fallback (default: {DEFAULT_CELLS})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
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

    if not args.dxf.exists():
        logger.error("DXF not found: {}", args.dxf)
        return 1

    try:
        result = BeamSketchDebugExporter().export_all(
            dxf_path=args.dxf,
            output_dir=args.output_dir,
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
