"""Phase D.1.7 — DIMENSION entity extraction and ownership integration."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.annotation_type_pipeline import AnnotationTypePipeline
from src.annotations.annotation_type_validator import AnnotationTypeValidator
from src.annotations.dimension_annotation_debug_exporter import (
    DimensionAnnotationDebugExporter,
)
from src.annotations.dimension_annotation_extractor import DimensionAnnotationExtractor
from src.annotations.dimension_annotation_integrator import (
    DimensionAnnotationIntegrator,
)
from src.annotations.dimension_annotation_validator import DimensionAnnotationValidator

DEFAULT_DXF_DIR = Path("data/reinforcement")



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
        description="Phase D.1.7 — extract DIMENSION annotations and integrate ownership.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=None,
        help="Reinforcement DXF (default: first *.dxf in data/reinforcement/)",
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


def resolve_dxf_path(arg: Path | None) -> Path:
    if arg is not None:
        return arg.resolve()
    candidates = sorted(DEFAULT_DXF_DIR.glob("*.dxf"))
    if not candidates:
        raise FileNotFoundError(f"No DXF files found in {DEFAULT_DXF_DIR}")
    return candidates[0].resolve()


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


def _top_dimension_annotations(
    assignments: List[dict[str, Any]],
    limit: int = 20,
) -> List[str]:
    lines: List[str] = []
    sorted_assignments = sorted(
        assignments,
        key=lambda item: (
            -float(item["dimension"]["y"]),
            float(item["dimension"]["x"]),
            item["dimension"]["text"],
        ),
    )
    for assignment in sorted_assignments[:limit]:
        dimension = assignment["dimension"]
        owner = (
            f"{assignment['beam_mark']}_H{assignment['occurrence_id']}"
            if assignment["assigned"]
            else "UNASSIGNED"
        )
        lines.append(f"  {dimension['text']} ({dimension['x']}, {dimension['y']}) -> {owner}")
    return lines


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        dxf_path = resolve_dxf_path(args.dxf)
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    required = [
        (args.reassigned, "Reassigned annotations JSON"),
        (args.ownership, "Ownership JSON"),
        (args.occurrences, "Header occurrences JSON"),
        (args.sketches, "Sketches JSON"),
        (args.beam_cells, "Beam cells JSON"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    output_dir = args.output_dir
    paths = OutputPaths(output_dir)
    paths.phase_d1_7_dir.mkdir(parents=True, exist_ok=True)

    reassigned = _load_json(args.reassigned)
    ownership = _load_json(args.ownership)
    occurrences = _load_json(args.occurrences)
    sketches = _load_json(args.sketches)
    beam_cells = _load_json(args.beam_cells)

    if not all(
        isinstance(data, list)
        for data in (reassigned, ownership, occurrences, sketches, beam_cells)
    ):
        logger.error("JSON inputs must be lists")
        return 1

    dimensions = DimensionAnnotationExtractor().extract_from_dxf(str(dxf_path))
    integration = DimensionAnnotationIntegrator().integrate(
        str(dxf_path),
        reassigned,
        dimensions,
        ownership,
        occurrences,
        sketches,
        beam_cells,
    )

    dimension_validation = DimensionAnnotationValidator().validate(
        integration["dimension_assignments"]
    )

    _write_json(
        paths.beam_annotations_extended,
        integration["extended_records"],
    )
    _write_json(
        paths.dimension_extraction_validation,
        dimension_validation,
    )

    DimensionAnnotationDebugExporter().export(
        integration["dimension_assignments"],
        paths.dimension_extraction_debug_dxf,
    )

    pipeline = AnnotationTypePipeline()
    sketch_records, flat_records = pipeline.classify_all(
        integration["extended_records"],
        ownership,
        sketches,
    )

    type_validator = AnnotationTypeValidator()
    type_validation = type_validator.validate(flat_records)
    summary_text = type_validator.build_summary_text(type_validation)

    _write_json(paths.annotation_types_extended, sketch_records)
    _write_json(
        paths.annotation_type_validation_extended,
        type_validation,
    )
    _write_json(
        paths.annotation_type_summary_extended,
        {
            "total_annotations": type_validation["total_annotations"],
            "count_by_type": type_validation["count_by_type"],
            "percentage_by_type": type_validation["percentage_by_type"],
            "unknown_count": type_validation["unknown_count"],
            "unknown_percentage": type_validation["unknown_percentage"],
            "status": type_validation["status"],
        },
    )
    _write_text(paths.annotation_type_summary_extended_txt, summary_text)

    print("\n--- Phase D.1.7 Summary ---")
    print(f"DIMENSION entities extracted: {dimension_validation['dimension_entities_found']}")
    print(f"Stirrup annotations: {dimension_validation['stirrup_annotations_found']}")
    print(f"Anchorage annotations: {dimension_validation['anchorage_annotations_found']}")
    print(f"Numeric dimensions: {dimension_validation['numeric_dimensions_found']}")
    print(f"Ownership assigned: {dimension_validation['ownership_assigned']}")
    print(f"Ownership unassigned: {dimension_validation['ownership_unassigned']}")
    print(f"Extraction validation: {dimension_validation['status']}")
    print("\nExtended annotation type distribution:")
    for type_name, count in type_validation["count_by_type"].items():
        print(f"  {type_name}: {count}")
    print(f"Classification validation: {type_validation['status']}")
    print("\nTop 20 DIMENSION annotations:")
    top_lines = _top_dimension_annotations(integration["dimension_assignments"])
    if top_lines:
        for line in top_lines:
            print(line)
    else:
        print("  (none)")
    print("---------------------------\n")

    logger.info(
        "Phase D.1.7 complete: {} dimensions, extraction={}, classification={}",
        dimension_validation["dimension_entities_found"],
        dimension_validation["status"],
        type_validation["status"],
    )

    if dimension_validation["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
