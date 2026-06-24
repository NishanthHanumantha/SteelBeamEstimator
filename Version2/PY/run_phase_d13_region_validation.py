"""Phase D.1.3 — annotation ownership region validation (read-only)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.annotation_region_debug_exporter import (
    AnnotationRegionDebugExporter,
)
from src.annotations.annotation_region_validator import AnnotationRegionValidator



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
        description="Phase D.1.3 — validate annotation ownership regions.",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=paths.beam_annotations_raw,
        help=f"Raw annotations JSON (default: {paths.beam_annotations_raw})",
    )
    parser.add_argument(
        "--ownership",
        type=Path,
        default=paths.sketch_ownership,
        help=f"Sketch ownership JSON (default: {paths.sketch_ownership})",
    )
    parser.add_argument(
        "--occurrences",
        type=Path,
        default=paths.header_occurrences,
        help=f"Header occurrences JSON (default: {paths.header_occurrences})",
    )
    parser.add_argument(
        "--beam-cells",
        type=Path,
        default=paths.beam_cells,
        help=f"Beam cells JSON (default: {paths.beam_cells})",
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
    ownership_path: Path,
    occurrences_path: Path,
    beam_cells_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    required = [
        (annotations_path, "Annotations JSON"),
        (ownership_path, "Ownership JSON"),
        (occurrences_path, "Header occurrences JSON"),
        (beam_cells_path, "Beam cells JSON"),
        (sketches_path, "Sketches JSON"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_3_dir.mkdir(parents=True, exist_ok=True)

    annotations_raw = _load_json(annotations_path)
    ownership = _load_json(ownership_path)
    occurrences = _load_json(occurrences_path)
    beam_cells = _load_json(beam_cells_path)
    sketches = _load_json(sketches_path)

    if not all(
        isinstance(data, list)
        for data in (annotations_raw, ownership, occurrences, beam_cells, sketches)
    ):
        logger.error("All inputs must be JSON lists")
        return 1

    validator = AnnotationRegionValidator()
    records, summary, regions = validator.validate(
        annotations_raw,
        ownership,
        occurrences,
        sketches,
        beam_cells,
    )
    report_text = validator.build_report_text(records, summary)

    _write_json(paths.annotation_region_validation, records)
    _write_json(
        paths.annotation_region_validation_summary,
        summary,
    )
    _write_text(
        paths.annotation_region_validation_report,
        report_text,
    )

    AnnotationRegionDebugExporter().export(
        records=records,
        regions=regions,
        output_path=paths.annotation_region_validation_debug_dxf,
    )

    outside_records = [
        record for record in records if record["classification"] == "OUTSIDE_REGION"
    ]
    outside_records.sort(key=lambda record: -record["distance_to_region_mm"])

    logger.info(
        "Phase D.1.3 complete: {} annotation(s), status={}",
        summary["total_annotations"],
        summary["status"],
    )

    print("\n--- Phase D.1.3 Summary ---")
    print(f"Total annotations: {summary['total_annotations']}")
    print(f"INSIDE_REGION: {summary['inside_region']}")
    print(f"NEAR_REGION_EDGE: {summary['near_region_edge']}")
    print(f"OUTSIDE_REGION: {summary['outside_region']}")
    print(f"Status: {summary['status']}")
    print("\nTop 10 OUTSIDE_REGION annotations:")
    for record in outside_records[:10]:
        preview = validator._preview_text(record["annotation"])
        print(
            f"  {record['beam_mark']} {record['sketch_id']} "
            f"{preview} — {record['distance_to_region_mm']} mm"
        )
    if not outside_records:
        print("  (none)")
    print("---------------------------\n")

    return 0 if summary["status"] == "PASS" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.annotations,
            args.ownership,
            args.occurrences,
            args.beam_cells,
            args.sketches,
            args.output_dir,
        )
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
