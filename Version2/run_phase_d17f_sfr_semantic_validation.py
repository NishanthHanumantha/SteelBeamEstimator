"""Phase D.1.7F — SFR semantic validation (read-only refinement before Phase E)."""

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.validation.sfr_semantic_validator_runner import run_semantic_validation


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
        description="Phase D.1.7F — semantic validation of SIDE_FACE_REINF annotations.",
    )
    parser.add_argument(
        "--validated-master",
        type=Path,
        default=paths.validated_annotations_master,
        help="Validated annotations master JSON (D.1.7E)",
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


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    paths = OutputPaths(args.output_dir)

    if not args.validated_master.exists():
        logger.error("validated_annotations_master not found: {}", args.validated_master)
        return 1

    result = run_semantic_validation(args.validated_master, paths)
    summary = result["summary"]

    print("\n--- Phase D.1.7F Semantic Validation Summary ---")
    print(f"Total SFR annotations: {summary['total_sfr_annotations']}")
    print(f"Engineering SFR: {summary['engineering_sfr_count']}")
    print(f"Reference notes: {summary['reference_note_count']}")
    print(f"Partial fragments: {summary['partial_sfr_count']}")
    print(f"Unknown: {summary['unknown_count']}")
    print(f"Parser-ready SFR: {summary['parser_ready_sfr_count']}")
    print(f"Ownership-rejected engineering: {summary['ownership_rejected_engineering_count']}")
    print(f"Validation: {summary['validation_status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print("-----------------------------------------------\n")

    logger.info(
        "Phase D.1.7F complete: validation={}, recommendation={}",
        summary["validation_status"],
        summary["recommendation"],
    )
    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
