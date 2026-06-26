"""Phase D.3.3 — annotation ownership reconciliation."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.input_paths import InputPaths, INPUT_ROOT
from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.ownership.ownership_pipeline import OwnershipPipeline


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
        description="Phase D.3.3 — annotation ownership reconciliation.",
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
        "--dxf",
        type=str,
        default="data/reinforcement/Beam_ReinforcementDetails.dxf",
        help="Reinforcement DXF for leader geometry",
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
    dxf_path = Path(args.dxf)

    try:
        result = OwnershipPipeline(input_paths, output_paths, dxf_path).run()
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    summary = result["summary"]
    print("\n" + "=" * 55)
    print("Phase D.3.3 Complete — Annotation Ownership Reconciliation")
    print("=" * 55)
    print(f"Total annotations: {summary['total_annotations']}")
    print(f"Owned: {summary['owned_count']}")
    print(f"Ambiguous: {summary['ambiguous_count']}")
    print(f"Unassigned: {summary['unassigned_count']}")
    print(f"Conflicts: {summary['ownership_conflict_count']}")
    print(f"Average confidence: {summary['average_confidence']}")
    print(f"Validation: {summary['validation_status']}")
    print(f"Parser ready: {'YES' if summary['parser_ready'] else 'NO'}")
    print("")
    for entry in summary.get("key_regions", []):
        print(
            f"  {entry['region_id']}: "
            f"ann={entry['annotation_count']} "
            f"resolved_contam={entry['resolved_contamination_count']} "
            f"marks={', '.join(entry['resolved_beam_marks'])}"
        )
    print("")
    print("Do NOT begin Phase D.4. Stop after D.3.3 and wait for review.")
    print("=" * 55 + "\n")

    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
