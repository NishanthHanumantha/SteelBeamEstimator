"""Phase D.1.6 — annotation type classification pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.annotation_type_debug_exporter import AnnotationTypeDebugExporter
from src.annotations.annotation_type_pipeline import AnnotationTypePipeline
from src.annotations.annotation_type_validator import AnnotationTypeValidator



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
        description="Phase D.1.6 — classify annotation engineering types.",
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
    reassigned_path: Path,
    ownership_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    required = [
        (reassigned_path, "Reassigned annotations JSON"),
        (ownership_path, "Ownership JSON"),
        (sketches_path, "Sketches JSON"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_6_dir.mkdir(parents=True, exist_ok=True)

    reassigned = _load_json(reassigned_path)
    ownership = _load_json(ownership_path)
    sketches = _load_json(sketches_path)

    if not all(isinstance(data, list) for data in (reassigned, ownership, sketches)):
        logger.error("All inputs must be JSON lists")
        return 1

    pipeline = AnnotationTypePipeline()
    sketch_records, flat_records = pipeline.classify_all(
        reassigned, ownership, sketches
    )

    validator = AnnotationTypeValidator()
    validation = validator.validate(flat_records)
    summary_text = validator.build_summary_text(validation)

    _write_json(paths.annotation_types, sketch_records)
    _write_json(paths.annotation_type_validation, validation)
    _write_text(paths.annotation_type_summary, summary_text)

    AnnotationTypeDebugExporter().export(
        classified_records=flat_records,
        output_path=paths.annotation_type_debug_dxf,
    )

    unknown_records = [
        r for r in flat_records if r["annotation_type"] == "UNKNOWN"
    ]

    logger.info(
        "Phase D.1.6 complete: {} classified, status={}",
        validation["total_annotations"],
        validation["status"],
    )

    print("\n--- Phase D.1.6 Summary ---")
    print(f"Total annotations: {validation['total_annotations']}")
    for type_name, count in validation["count_by_type"].items():
        print(f"  {type_name}: {count}")
    print(f"UNKNOWN: {validation['unknown_count']} ({validation['unknown_percentage']}%)")
    print(f"Validation: {validation['status']}")
    print("\nTop UNKNOWN annotations:")
    for record in unknown_records[:20]:
        print(f"  {record['raw_text']!r} -> {record['clean_text']!r}")
    if not unknown_records:
        print("  (none)")
    print("---------------------------\n")

    return 0 if validation["status"] != "FAIL" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.reassigned,
            args.ownership,
            args.sketches,
            args.output_dir,
        )
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
