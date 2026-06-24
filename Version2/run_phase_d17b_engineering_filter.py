"""Phase D.1.7B — engineering annotation filter pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.annotations.engineering_annotation_debug_exporter import (
    EngineeringAnnotationDebugExporter,
)
from src.annotations.engineering_annotation_filter import EngineeringAnnotationFilter
from src.annotations.engineering_annotation_validator import (
    EngineeringAnnotationValidator,
)
from src.config.output_paths import OutputPaths, OUTPUT_ROOT


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
        description="Phase D.1.7B — filter engineering-only annotations for D.2.",
    )
    parser.add_argument(
        "--types-extended",
        type=Path,
        default=paths.annotation_types_extended,
        help="Extended classification JSON",
    )
    parser.add_argument(
        "--annotations-extended",
        type=Path,
        default=paths.beam_annotations_extended,
        help="Extended annotations JSON",
    )
    parser.add_argument(
        "--dimension-source-audit",
        type=Path,
        default=paths.dimension_source_audit,
        help="Dimension source audit JSON",
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


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    paths = OutputPaths(args.output_dir)
    paths.phase_d1_7b_dir.mkdir(parents=True, exist_ok=True)

    required = [
        (args.types_extended, "annotation_types_extended.json"),
        (args.annotations_extended, "beam_annotations_extended.json"),
        (args.dimension_source_audit, "dimension_source_audit.json"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    types_extended = _load_json(args.types_extended)
    annotations_extended = _load_json(args.annotations_extended)
    dimension_source_audit = _load_json(args.dimension_source_audit)

    if not all(isinstance(data, list) for data in (
        types_extended,
        annotations_extended,
        dimension_source_audit,
    )):
        logger.error("All JSON inputs must be lists")
        return 1

    result = EngineeringAnnotationFilter().filter(
        types_extended,
        annotations_extended,
        dimension_source_audit,
    )

    validation = EngineeringAnnotationValidator().validate(
        result["summary"],
        result["engineering"],
        result["geometry"],
        result["rejected"],
    )

    _write_json(paths.engineering_annotations, result["engineering"])
    _write_json(paths.geometry_dimension_annotations, result["geometry"])
    _write_json(paths.rejected_measurement_annotations, result["rejected"])
    _write_json(paths.engineering_annotation_summary, result["summary"])
    _write_json(paths.engineering_annotation_validation, validation)
    _write_text(paths.engineering_annotation_report, result["report_text"])

    EngineeringAnnotationDebugExporter().export(
        result["engineering"],
        paths.engineering_annotation_debug_dxf,
    )

    summary = result["summary"]
    print("\n--- Phase D.1.7B Summary ---")
    print(f"Total input annotations: {summary['total_input_annotations']}")
    print(f"Engineering annotations retained: {summary['engineering_annotations']}")
    print(f"Geometry dimensions retained: {summary['geometry_dimensions']}")
    print(f"AutoCAD measurements rejected: {summary['rejected_measurements']}")
    print("\nEngineering counts by type:")
    for type_name, count in summary["count_by_type"].items():
        print(f"  {type_name}: {count}")
    print(f"\nValidation: {validation['status']}")
    for check_name, passed in validation["checks"].items():
        print(f"  {check_name}: {'PASS' if passed else 'FAIL'}")
    print("----------------------------\n")

    logger.info(
        "Phase D.1.7B complete: {} engineering, status={}",
        summary["engineering_annotations"],
        validation["status"],
    )
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
