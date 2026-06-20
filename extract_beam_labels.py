"""CLI entry point for beam label extraction (Phase 2A)."""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from src.extractor.beam_label_extractor import (
    BeamLabelExtractor,
    BeamLabelValidationError,
)

DEFAULT_INPUT = Path("data/output/entities.json")
DEFAULT_OUTPUT = Path("data/output/beam_labels.json")


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
        description="Extract beam labels from parsed DXF entities (Phase 2A).",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input entities JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output beam labels JSON (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def save_beam_labels(labels: list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(labels, fh, indent=2, ensure_ascii=False)
    logger.info("Saved {} beam labels to {}", len(labels), output_path.resolve())


def run(input_path: Path, output_path: Path) -> int:
    extractor = BeamLabelExtractor()
    labels = extractor.extract(input_path)
    summary = extractor.build_summary(labels)
    extractor.log_summary(summary)

    save_beam_labels(labels, output_path)
    return 0


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(args.input, args.output)
    except BeamLabelValidationError as exc:
        logger.error("{}", exc)
        return 1
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
