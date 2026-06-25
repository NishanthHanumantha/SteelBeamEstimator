"""Run Version 2 Phase A, B, and C extraction pipelines."""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.framing.framing_beam_extractor import FramingBeamExtractor
from src.framing.framing_validator import FramingValidator
from src.grid.beam_cell_builder import BeamCellBuilder
from src.grid.beam_cell_validator import BeamCellValidator
from src.grid.beam_cell_debug_exporter import BeamCellDebugExporter
from src.reinforcement.header_extractor import ReinforcementHeaderExtractor
from src.reinforcement.header_validator import ReinforcementHeaderValidator

DEFAULT_FRAMING_DIR = Path("data/framing")
DEFAULT_REINFORCEMENT_DIR = Path("data/reinforcement")


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
        description="Version 2 — Phase A/B/C extraction (framing, headers, cells).",
    )
    parser.add_argument(
        "--framing-dir",
        type=Path,
        default=DEFAULT_FRAMING_DIR,
        help=f"Framing plan DXF directory (default: {DEFAULT_FRAMING_DIR})",
    )
    parser.add_argument(
        "--reinforcement-dir",
        type=Path,
        default=DEFAULT_REINFORCEMENT_DIR,
        help=f"Reinforcement DXF directory (default: {DEFAULT_REINFORCEMENT_DIR})",
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


def save_json(data: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    logger.info("Wrote {}", path.resolve())


def run(framing_dir: Path, reinforcement_dir: Path, output_dir: Path) -> int:
    paths = OutputPaths(output_dir)
    paths.ensure_phase_dirs()

    framing_beams = FramingBeamExtractor().extract_from_directory(framing_dir)
    framing_validation = FramingValidator().validate(framing_beams)
    save_json(framing_beams, paths.framing_beams)
    save_json(framing_validation, paths.framing_validation)

    header_extractor = ReinforcementHeaderExtractor()
    all_headers = header_extractor.extract_from_directory(reinforcement_dir)
    output_headers = header_extractor.to_output_records(all_headers, dedupe=True)
    header_validation = ReinforcementHeaderValidator().validate(
        all_headers, output_headers
    )
    save_json(output_headers, paths.reinforcement_headers)
    save_json(header_validation, paths.reinforcement_header_validation)

    beam_cells = BeamCellBuilder().build(output_headers)
    cell_validation = BeamCellValidator().validate(beam_cells, output_headers)
    save_json(beam_cells, paths.beam_cells)
    save_json(cell_validation, paths.beam_cells_validation)

    BeamCellDebugExporter().export_all(
        cells_path=paths.beam_cells,
        output_dir=paths.phase_c_debug_dir,
        headers_path=paths.reinforcement_headers,
    )

    logger.info(
        "Phase A–C complete: {} framing beam(s), {} header(s), {} cell(s)",
        len(framing_beams),
        len(output_headers),
        len(beam_cells),
    )
    return 0


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(args.framing_dir, args.reinforcement_dir, args.output_dir)
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
