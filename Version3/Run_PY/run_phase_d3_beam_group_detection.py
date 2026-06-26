"""Phase D.3 — beam group detection and shared annotation ownership."""

import _bootstrap  # noqa: F401

import argparse
import sys

from loguru import logger

from src.config.input_paths import InputPaths, INPUT_ROOT
from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.grouping.beam_group_pipeline import BeamGroupPipeline


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
        description="Phase D.3 — beam group detection and shared annotation ownership.",
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

    from pathlib import Path

    input_paths = InputPaths(Path(args.input_dir))
    output_paths = OutputPaths(Path(args.output_dir))

    try:
        result = BeamGroupPipeline(input_paths, output_paths).run()
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    summary = result["summary"]
    print("\n--- Phase D.3 Beam Group Detection ---")
    print(f"Beam groups: {summary['beam_group_count']} ({summary['multi_beam_group_count']} multi-beam)")
    print(f"Group-owned annotations: {summary['group_owned_annotation_count']}")
    print(f"Expanded annotations: {summary['expanded_annotation_count']}")
    print(f"Validation: {summary['overall_status']}")
    for entry in summary["multi_beam_groups"]:
        print(f"  {entry['beam_group_id']}: {', '.join(entry['members'])}")
    print("----------------------------------------\n")

    print("Phase D.3 complete. Beam group detection finished. Awaiting review before Phase D.4.")
    return 0 if summary["overall_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
