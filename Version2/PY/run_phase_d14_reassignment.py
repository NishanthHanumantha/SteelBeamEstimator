"""Phase D.1.4 — ownership reassignment pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.ownership_reassignment_debug_exporter import (
    OwnershipReassignmentDebugExporter,
)
from src.annotations.ownership_reassignment_engine import OwnershipReassignmentEngine



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
        description="Phase D.1.4 — reassign leakage candidate annotations.",
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
        "--leakage",
        type=Path,
        default=paths.boundary_leakage_report,
        help=f"Boundary leakage report JSON (default: {paths.boundary_leakage_report})",
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


def run(
    annotations_path: Path,
    ownership_path: Path,
    occurrences_path: Path,
    leakage_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    required = [
        (annotations_path, "Annotations JSON"),
        (ownership_path, "Ownership JSON"),
        (occurrences_path, "Header occurrences JSON"),
        (leakage_path, "Leakage report JSON"),
        (sketches_path, "Sketches JSON"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_4_dir.mkdir(parents=True, exist_ok=True)

    annotations_raw = _load_json(annotations_path)
    ownership = _load_json(ownership_path)
    occurrences = _load_json(occurrences_path)
    leakage_report = _load_json(leakage_path)
    sketches = _load_json(sketches_path)

    if not all(
        isinstance(data, list)
        for data in (annotations_raw, ownership, occurrences, leakage_report, sketches)
    ):
        logger.error("All inputs must be JSON lists")
        return 1

    engine = OwnershipReassignmentEngine()
    occurrence_records, log_entries, summary, validation, _ = engine.reassign(
        annotations_raw,
        leakage_report,
        ownership,
        sketches,
    )

    _write_json(paths.beam_annotations_reassigned, occurrence_records)
    _write_json(paths.ownership_reassignment_log, log_entries)
    _write_json(paths.ownership_reassignment_summary, summary)
    _write_json(paths.ownership_reassignment_validation, validation)

    OwnershipReassignmentDebugExporter().export(
        log_entries=log_entries,
        occurrences=occurrences,
        output_path=paths.ownership_reassignment_debug_dxf,
    )

    logger.info(
        "Phase D.1.4 complete: {} reassigned, status={}",
        summary["reassigned"],
        validation["status"],
    )

    print("\n--- Phase D.1.4 Summary ---")
    print(f"Total annotations: {summary['total_annotations']}")
    print(f"Reassigned: {summary['reassigned']}")
    print(f"Unchanged: {summary['unchanged']}")
    print(f"Affected beams: {', '.join(summary['affected_beams'])}")
    print(f"Validation status: {validation['status']}")
    print("---------------------------\n")

    return 0 if validation["status"] == "PASS" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.annotations,
            args.ownership,
            args.occurrences,
            args.leakage,
            args.sketches,
            args.output_dir,
        )
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
