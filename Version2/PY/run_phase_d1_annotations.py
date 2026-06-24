"""Phase D.1 — raw annotation extraction pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List

from loguru import logger

from src.annotations.annotation_debug_exporter import AnnotationDebugExporter
from src.annotations.annotation_validator import AnnotationValidator
from src.annotations.raw_annotation_extractor import RawAnnotationExtractor
from src.config.output_paths import OutputPaths, OUTPUT_ROOT

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")
_DEFAULT_PATHS = OutputPaths()


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
        description="Phase D.1 — extract raw annotations from owned sketches.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help=f"Reinforcement DXF (default: {DEFAULT_DXF})",
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
        "--occurrences",
        type=Path,
        default=paths.header_occurrences,
        help=f"Header occurrences JSON (default: {paths.header_occurrences})",
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


def _expected_sketch_ids(ownership: List[dict[str, Any]]) -> List[str]:
    sketch_ids: List[str] = []
    for record in ownership:
        for owned in record.get("owned_sketches", []):
            if isinstance(owned, dict):
                sketch_ids.append(str(owned["sketch_id"]))
            else:
                sketch_ids.append(str(owned))
    return sorted(sketch_ids)


def run(
    dxf_path: Path,
    ownership_path: Path,
    sketches_path: Path,
    occurrences_path: Path,
    output_dir: Path,
) -> int:
    if not dxf_path.exists():
        logger.error("DXF not found: {}", dxf_path)
        return 1
    if not ownership_path.exists():
        logger.error("Ownership JSON not found: {}", ownership_path)
        return 1
    if not sketches_path.exists():
        logger.error("Sketches JSON not found: {}", sketches_path)
        return 1
    if not occurrences_path.exists():
        logger.error("Header occurrences JSON not found: {}", occurrences_path)
        return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_dir.mkdir(parents=True, exist_ok=True)

    ownership = _load_json(ownership_path)
    sketches = _load_json(sketches_path)
    occurrences = _load_json(occurrences_path)

    if not isinstance(ownership, list) or not isinstance(sketches, list):
        logger.error("Ownership and sketches JSON must be lists")
        return 1
    if not isinstance(occurrences, list):
        logger.error("Header occurrences JSON must be a list")
        return 1

    expected_ids = _expected_sketch_ids(ownership)
    extraction_failed = False
    records: List[Any] = []

    try:
        records = RawAnnotationExtractor().extract_from_dxf(
            str(dxf_path.resolve()),
            ownership,
            sketches,
            occurrences,
        )
    except Exception as exc:
        logger.exception("Annotation extraction failed: {}", exc)
        extraction_failed = True

    validation = AnnotationValidator().validate(
        expected_ids,
        records,
        extraction_failed=extraction_failed,
    )

    _write_json(paths.beam_annotations_raw, records)
    _write_json(paths.beam_annotations_validation, validation)

    if records:
        AnnotationDebugExporter().export(
            records=records,
            sketches=sketches,
            output_path=paths.beam_annotations_debug_dxf,
        )

    total_sketches = validation["total_sketches"]
    processed = validation["processed_sketches"]
    total_annotations = validation["total_annotations"]
    avg = round(total_annotations / processed, 1) if processed else 0.0
    empty_count = len(validation["empty_sketches"])

    logger.info(
        "Phase D.1 complete: {} sketch(s), {} annotation(s), status={}",
        processed,
        total_annotations,
        validation["status"],
    )

    print("\n--- Phase D.1 Summary ---")
    print(f"Total Sketches: {total_sketches}")
    print(f"Processed Sketches: {processed}")
    print(f"Total Annotations: {total_annotations}")
    print(f"Average Annotations Per Sketch: {avg}")
    print(f"Empty Sketches: {empty_count}")
    print(f"Validation Status: {validation['status']}")
    print("-------------------------\n")

    return 0 if validation["status"] == "PASS" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.dxf,
            args.ownership,
            args.sketches,
            args.occurrences,
            args.output_dir,
        )
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
