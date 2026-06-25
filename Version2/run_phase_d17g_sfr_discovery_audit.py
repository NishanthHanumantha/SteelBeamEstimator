"""Phase D.1.7G — SFR discovery audit (read-only investigation)."""

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.validation.sfr_discovery_runner import run_discovery_audit

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")


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
        description="Phase D.1.7G — read-only SFR discovery audit.",
    )
    parser.add_argument(
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help="Reinforcement detail DXF",
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

    try:
        result = run_discovery_audit(paths, args.dxf)
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    summary = result["summary"]
    validation = result["validation"]

    print("\n--- Phase D.1.7G SFR Discovery Audit ---")
    print(f"Total SFR entities in DXF: {summary['total_sfr_entities_in_dxf']}")
    print(f"Parser-ready SFR (D.1.7F): {summary['parser_ready_sfr_count']}")
    print(f"Missing parser-ready beams: {', '.join(summary['missing_beams']) or 'none'}")
    print(f"Validation: {validation['status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print("--------------------------------------\n")

    print(
        "Phase D.1.7G complete. Read-only SFR Discovery Audit finished. "
        "Awaiting review before implementing any extraction or ownership fixes."
    )

    logger.info(
        "Phase D.1.7G complete: validation={}, recommendation={}",
        validation["status"],
        summary["recommendation"],
    )
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
