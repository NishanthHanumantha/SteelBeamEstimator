"""Phase D.3.1 — beam group confidence and validation (read-only)."""

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.input_paths import InputPaths, INPUT_ROOT
from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.grouping.beam_group_validation_pipeline import BeamGroupValidationPipeline


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
        description="Phase D.3.1 — beam group confidence validation (read-only).",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=str(INPUT_ROOT),
        help="Input directory (default: data/input)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=str(OUTPUT_ROOT),
        help="Output root directory (default: data/output)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    input_paths = InputPaths(Path(args.input_dir))
    output_paths = OutputPaths(Path(args.output_dir))

    try:
        result = BeamGroupValidationPipeline(input_paths, output_paths).run()
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    validation = result["validation"]
    print("\n========================================")
    print("Phase D.3.1 Complete")
    print("========================================")
    print(f"Total groups: {validation['total_groups']}")
    print(f"HIGH: {validation['high_confidence_count']}")
    print(f"MEDIUM: {validation['medium_confidence_count']}")
    print(f"LOW: {validation['low_confidence_count']}")
    print(f"INVALID: {validation['invalid_group_count']}")
    print(f"Validation: {validation['status']}")
    if validation.get("recommended_corrections"):
        print(f"Recommended corrections: {len(validation['recommended_corrections'])}")
    print(f"Parser Ready: {'YES' if validation['parser_ready'] else 'NO'}")
    print("========================================\n")

    print("Phase D.3.1 complete. Awaiting review before Phase D.3.2.")
    return 0 if validation["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
