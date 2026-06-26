"""Phase D.1.5 — post-reassignment validation pipeline."""

import _bootstrap  # noqa: F401

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.post_reassignment_debug_exporter import (
    PostReassignmentDebugExporter,
)
from src.annotations.post_reassignment_validator import PostReassignmentValidator



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
        description="Phase D.1.5 — post-reassignment validation.",
    )
    parser.add_argument(
        "--reassigned",
        type=Path,
        default=paths.beam_annotations_reassigned,
        help=f"Reassigned annotations JSON (default: {paths.beam_annotations_reassigned})",
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
        "--sketches",
        type=Path,
        default=paths.beam_sketches_debug,
        help=f"Sketch geometry JSON (default: {paths.beam_sketches_debug})",
    )
    parser.add_argument(
        "--beam-cells",
        type=Path,
        default=paths.beam_cells,
        help=f"Beam cells JSON (default: {paths.beam_cells})",
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
    reassigned_path: Path,
    ownership_path: Path,
    occurrences_path: Path,
    sketches_path: Path,
    beam_cells_path: Path,
    output_dir: Path,
) -> int:
    required = [
        (reassigned_path, "Reassigned annotations JSON"),
        (ownership_path, "Ownership JSON"),
        (occurrences_path, "Header occurrences JSON"),
        (sketches_path, "Sketches JSON"),
        (beam_cells_path, "Beam cells JSON"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_5_dir.mkdir(parents=True, exist_ok=True)

    reassigned = _load_json(reassigned_path)
    ownership = _load_json(ownership_path)
    occurrences = _load_json(occurrences_path)
    sketches = _load_json(sketches_path)
    beam_cells = _load_json(beam_cells_path)

    d13_summary = (
        _load_json(paths.annotation_region_validation_summary)
        if paths.annotation_region_validation_summary.exists()
        else None
    )
    d131_summary = (
        _load_json(paths.boundary_leakage_summary)
        if paths.boundary_leakage_summary.exists()
        else None
    )

    if not all(
        isinstance(data, list)
        for data in (reassigned, ownership, occurrences, sketches, beam_cells)
    ):
        logger.error("Primary inputs must be JSON lists")
        return 1

    validator = PostReassignmentValidator()
    (
        audit_records,
        ownership_validation,
        region_records,
        region_summary,
        leakage_records,
        leakage_summary,
        summary,
        validation,
        regions,
    ) = validator.validate(
        reassigned,
        ownership,
        occurrences,
        sketches,
        beam_cells,
        d13_summary,
        d131_summary,
    )

    report_text = validator.build_report_text(
        summary, audit_records, region_records, leakage_records
    )

    _write_json(paths.post_reassignment_audit, audit_records)
    _write_json(
        paths.post_reassignment_region_validation,
        region_records,
    )
    _write_json(
        paths.post_reassignment_leakage_report,
        leakage_records,
    )
    _write_json(
        paths.post_reassignment_validation_summary,
        summary,
    )
    _write_text(
        paths.post_reassignment_validation_report,
        report_text,
    )
    _write_json(
        paths.post_reassignment_validation_status,
        validation,
    )

    PostReassignmentDebugExporter().export(
        audit_records=audit_records,
        region_records=region_records,
        leakage_records=leakage_records,
        regions=regions,
        output_path=paths.post_reassignment_validation_debug_dxf,
    )

    logger.info(
        "Phase D.1.5 complete: recommendation={}, status={}",
        summary["recommendation"],
        validation["status"],
    )

    print("\n--- Phase D.1.5 Summary ---")
    print(f"Ownership status: {summary['ownership_status']}")
    print(f"Region status: {summary['region_status']}")
    print(f"Total annotations: {summary['total_annotations']}")
    print(f"OUTSIDE_REGION: {summary['outside_region']}")
    print(f"REASSIGN_CANDIDATE: {summary['reassign_candidate']}")
    print(f"Validation status: {validation['status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print("---------------------------\n")

    return 0 if validation["status"] != "FAIL" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.reassigned,
            args.ownership,
            args.occurrences,
            args.sketches,
            args.beam_cells,
            args.output_dir,
        )
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
