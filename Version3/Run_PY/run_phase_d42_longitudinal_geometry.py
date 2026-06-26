"""Phase D.4.2 — longitudinal rebar geometry resolution runner."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.geometry.longitudinal_geometry_pipeline import LongitudinalGeometryPipeline

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")
DEFAULT_CONFIG = Path("config/rebar_geometry.yaml")


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase D.4.2 — longitudinal rebar geometry resolver.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=str(OUTPUT_ROOT),
        help="Output root (default: data/output)",
    )
    parser.add_argument(
        "--dxf",
        type=str,
        default=str(DEFAULT_DXF),
        help="Reinforcement detail DXF path",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help="Rebar geometry config YAML path",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    result = LongitudinalGeometryPipeline(
        OutputPaths(Path(args.output_dir)),
        dxf_path=args.dxf,
        config_path=args.config,
    ).run()
    summary = result["summary"]
    print("\n" + "=" * 50)
    print("Phase D.4.2 Complete — Longitudinal Geometry Resolution")
    print("=" * 50)
    print(f"Longitudinal bars: {summary['longitudinal_bar_count']}")
    print(f"Resolved: {summary['resolved_count']}")
    print(f"Geometry attached: {summary['geometry_attached_count']}")
    print(f"Leader attachments: {summary['leader_attachment_count']}")
    print(f"Nearest-line attachments: {summary['nearest_line_attachment_count']}")
    print(f"Top bars: {summary['top_bar_count']}")
    print(f"Bottom bars: {summary['bottom_bar_count']}")
    print(f"Continuous: {summary['continuous_count']}")
    print(f"Partial: {summary['partial_count']}")
    print(f"Failures: {summary['failure_count']}")
    print(f"Validation: {summary['validation_status']}")
    print("=" * 50 + "\n")
    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
