"""Phase D.4 — engineering annotation parsing."""

import _bootstrap  # noqa: F401

import argparse
import sys

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.parsing.engineering_parser_pipeline import EngineeringParserPipeline


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase D.4 — engineering annotation parsing.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=str(OUTPUT_ROOT),
        help="Output root (default: data/output)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    from pathlib import Path

    result = EngineeringParserPipeline(OutputPaths(Path(args.output_dir))).run()
    summary = result["summary"]
    print("\n" + "=" * 50)
    print("Phase D.4 Complete — Engineering Annotation Parsing")
    print("=" * 50)
    print(f"Engineering objects: {summary['engineering_object_count']}")
    print(f"Longitudinal bars: {summary['longitudinal_bar_count']}")
    print(f"Stirrups: {summary['stirrup_count']}")
    print(f"Anchorage: {summary['anchorage_count']}")
    print(f"SFR: {summary['sfr_count']}")
    print(f"Failed: {summary['failed_parse_count']}")
    print(f"Validation: {summary['validation_status']}")
    print("=" * 50 + "\n")
    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
