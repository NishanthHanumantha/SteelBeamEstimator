"""Phase D.3.2 — detail region detection and beam group refinement."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.input_paths import InputPaths, INPUT_ROOT
from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.detail_regions.detail_region_pipeline import DetailRegionPipeline


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
        description="Phase D.3.2 — detail region detection and group refinement.",
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
        result = DetailRegionPipeline(input_paths, output_paths).run()
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    summary = result["summary"]
    print("\n" + "=" * 50)
    print("Phase D.3.2 Complete")
    print("=" * 50)
    print(f"Total Detail Regions: {summary['total_detail_regions']}")
    print(f"Single-beam Regions: {summary['single_beam_region_count']}")
    print(f"Multi-beam Regions: {summary['multi_beam_region_count']}")
    print(f"Invalid Regions: {summary['invalid_region_count']}")
    print(f"Beam Groups Generated: {summary['beam_groups_generated']}")
    print(f"Validation: {summary['validation_status']}")
    print(f"Parser Ready: {'YES' if summary['parser_ready'] else 'NO'}")
    print("")
    print("Recommendations:")
    for rec in summary.get("recommendations", []):
        print(f"  - {rec}")
    print("")
    print("Do NOT begin Phase D.4. Stop after D.3.2 and wait for review.")
    print("=" * 50 + "\n")

    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
