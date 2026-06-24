"""Phase D.1.3.1 — boundary leakage audit (read-only)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.boundary_leakage_analyzer import BoundaryLeakageAnalyzer
from src.annotations.boundary_leakage_debug_exporter import BoundaryLeakageDebugExporter



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
        description="Phase D.1.3.1 — boundary leakage report for outside annotations.",
    )
    parser.add_argument(
        "--region-validation",
        type=Path,
        default=paths.annotation_region_validation,
        help=f"Region validation JSON (default: {paths.annotation_region_validation})",
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
    region_validation_path: Path,
    ownership_path: Path,
    occurrences_path: Path,
    beam_cells_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    required = [
        (region_validation_path, "Region validation JSON"),
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
    paths.phase_d1_3_1_dir.mkdir(parents=True, exist_ok=True)

    region_validation = _load_json(region_validation_path)
    ownership = _load_json(ownership_path)
    occurrences = _load_json(occurrences_path)
    beam_cells = _load_json(beam_cells_path)
    sketches = _load_json(sketches_path)

    if not all(
        isinstance(data, list)
        for data in (region_validation, ownership, occurrences, beam_cells, sketches)
    ):
        logger.error("All inputs must be JSON lists")
        return 1

    analyzer = BoundaryLeakageAnalyzer()
    records, summary, validation, regions = analyzer.analyze(
        region_validation,
        ownership,
        occurrences,
        sketches,
        beam_cells,
    )
    report_text = analyzer.build_report_text(records, summary)

    _write_json(paths.boundary_leakage_report, records)
    _write_json(paths.boundary_leakage_summary, summary)
    _write_text(paths.boundary_leakage_report_txt, report_text)
    _write_json(paths.boundary_leakage_validation, validation)

    BoundaryLeakageDebugExporter().export(
        records=records,
        regions=regions,
        output_path=paths.boundary_leakage_debug_dxf,
    )

    logger.info(
        "Phase D.1.3.1 complete: {} outside annotation(s), status={}",
        summary["total_outside_annotations"],
        validation["status"],
    )

    print("\n--- Phase D.1.3.1 Summary ---")
    print(f"Total outside annotations: {summary['total_outside_annotations']}")
    print(f"Retain: {summary['retain']}")
    print(f"Review: {summary['review']}")
    print(f"Reassign candidate: {summary['reassign_candidate']}")
    print(f"Validation status: {validation['status']}")
    print("-------------------------------\n")

    return 0 if validation["status"] == "PASS" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.region_validation,
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
