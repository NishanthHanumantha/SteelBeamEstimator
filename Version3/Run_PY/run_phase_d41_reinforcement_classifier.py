"""Phase D.4.1 — reinforcement classification engine."""

import _bootstrap  # noqa: F401

import argparse
import sys

from loguru import logger

from src.classification.reinforcement_pipeline import ReinforcementPipeline
from src.config.output_paths import OutputPaths, OUTPUT_ROOT


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase D.4.1 — reinforcement classification.",
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

    result = ReinforcementPipeline(OutputPaths(Path(args.output_dir))).run()
    summary = result["summary"]
    print("\n" + "=" * 50)
    print("Phase D.4.1 Complete — Reinforcement Classification")
    print("=" * 50)
    print(f"Classified: {summary['classified_count']}")
    for cat, count in sorted(summary.get("by_estimator_category", {}).items()):
        print(f"  {cat}: {count}")
    print(f"Validation: {summary['validation_status']}")
    print("=" * 50 + "\n")
    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
