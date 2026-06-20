"""CLI entry point for drawing region detection (Phase 3A.5)."""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from src.regions.drawing_region_detector import DrawingRegionDetector
from src.utils.entities_loader import EntitiesLoadError

DEFAULT_INPUT = Path("data/output/entities.json")
DEFAULT_ANCHORS_OUTPUT = Path("data/output/drawing_anchors.json")
DEFAULT_REGIONS_OUTPUT = Path("data/output/drawing_regions.json")
DEFAULT_MAP_OUTPUT = Path("data/output/entity_region_map.json")
DEFAULT_REPORT_OUTPUT = Path("data/output/drawing_region_report.json")


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
        description="Detect estimator-style drawing regions (Phase 3A.5).",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input entities JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--anchors-output",
        type=Path,
        default=DEFAULT_ANCHORS_OUTPUT,
        help=f"Drawing anchors JSON (default: {DEFAULT_ANCHORS_OUTPUT})",
    )
    parser.add_argument(
        "--regions-output",
        type=Path,
        default=DEFAULT_REGIONS_OUTPUT,
        help=f"Drawing regions JSON (default: {DEFAULT_REGIONS_OUTPUT})",
    )
    parser.add_argument(
        "--map-output",
        type=Path,
        default=DEFAULT_MAP_OUTPUT,
        help=f"Entity region map JSON (default: {DEFAULT_MAP_OUTPUT})",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help=f"Region report JSON (default: {DEFAULT_REPORT_OUTPUT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def save_json(data: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    logger.info("Saved {}", output_path.resolve())


def run(
    input_path: Path,
    anchors_output: Path,
    regions_output: Path,
    map_output: Path,
    report_output: Path,
) -> int:
    detector = DrawingRegionDetector()
    result = detector.detect(input_path)

    save_json(result["anchors"], anchors_output)
    save_json(result["regions"], regions_output)
    save_json(result["entity_region_map"], map_output)

    report = result["report"]
    report["validation"] = result["validation"]
    save_json(report, report_output)

    return 0 if result["validation"]["passed"] else 2


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.input,
            args.anchors_output,
            args.regions_output,
            args.map_output,
            args.report_output,
        )
    except EntitiesLoadError as exc:
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
