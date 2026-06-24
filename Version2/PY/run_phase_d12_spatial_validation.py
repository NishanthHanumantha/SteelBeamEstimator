"""Phase D.1.2 — annotation spatial ownership validation (read-only)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.annotation_spatial_debug_exporter import (
    AnnotationSpatialDebugExporter,
)
from src.annotations.annotation_spatial_validator import AnnotationSpatialValidator



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
        description="Phase D.1.2 — validate annotation spatial ownership.",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=paths.beam_annotations_raw,
        help=f"Raw annotations JSON (default: {paths.beam_annotations_raw})",
    )
    parser.add_argument(
        "--sketches",
        type=Path,
        default=paths.beam_sketches_debug,
        help=f"Sketch geometry JSON (default: {paths.beam_sketches_debug})",
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


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    logger.info("Wrote {}", path.resolve())


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote {}", path.resolve())


def run(
    annotations_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    if not annotations_path.exists():
        logger.error("Annotations JSON not found: {}", annotations_path)
        return 1
    if not sketches_path.exists():
        logger.error("Sketches JSON not found: {}", sketches_path)
        return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_2_dir.mkdir(parents=True, exist_ok=True)

    annotations_raw = _load_json(annotations_path)
    sketches = _load_json(sketches_path)
    if not isinstance(annotations_raw, list) or not isinstance(sketches, list):
        logger.error("Expected list inputs for annotations and sketches")
        return 1

    validator = AnnotationSpatialValidator()
    records, summary = validator.validate(annotations_raw, sketches)
    report_text = validator.build_report_text(records, summary)
    high_outside_beams = validator.beam_outside_ratios(records, threshold_pct=25.0)

    _write_json(paths.annotation_spatial_validation, records)
    _write_json(
        paths.annotation_spatial_validation_summary,
        summary,
    )
    _write_text(
        paths.annotation_spatial_validation_report,
        report_text,
    )

    AnnotationSpatialDebugExporter().export(
        records=records,
        sketches=sketches,
        output_path=paths.annotation_spatial_validation_debug_dxf,
    )

    outside_records = [r for r in records if r["classification"] == "OUTSIDE"]
    outside_records.sort(key=lambda r: -r["distance_to_bbox_mm"])

    logger.info(
        "Phase D.1.2 complete: {} annotation(s), status={}",
        summary["total_annotations"],
        summary["status"],
    )

    print("\n--- Phase D.1.2 Summary ---")
    print(f"Total annotations: {summary['total_annotations']}")
    print(f"INSIDE: {summary['inside']}")
    print(f"NEAR_EDGE: {summary['near_edge']}")
    print(f"OUTSIDE: {summary['outside']}")
    print(f"Status: {summary['status']}")
    print("\nTop 15 OUTSIDE annotations:")
    for record in outside_records[:15]:
        preview = validator._preview_text(record["annotation"])
        print(
            f"  {record['beam_mark']} {record['sketch_id']} "
            f"{preview} — {record['distance_to_bbox_mm']} mm"
        )
    if high_outside_beams:
        print("\nBeams with >25% OUTSIDE annotations:")
        for item in high_outside_beams:
            print(
                f"  {item['beam_mark']}: {item['outside']}/{item['total']} "
                f"({item['outside_ratio_pct']}%)"
            )
    else:
        print("\nNo beams with >25% OUTSIDE annotations.")
    print("---------------------------\n")

    return 0 if summary["status"] != "FAIL" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(args.annotations, args.sketches, args.output_dir)
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
