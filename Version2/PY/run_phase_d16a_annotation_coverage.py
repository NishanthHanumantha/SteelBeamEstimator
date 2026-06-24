"""Phase D.1.6A — annotation coverage audit (read-only)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.annotation_coverage_auditor import AnnotationCoverageAuditor
DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")

from src.annotations.annotation_coverage_debug_exporter import (
    AnnotationCoverageDebugExporter,
)



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
        description="Phase D.1.6A — audit annotation coverage in ownership regions.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help=f"Reinforcement DXF (default: {DEFAULT_DXF})",
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
    dxf_path: Path,
    reassigned_path: Path,
    ownership_path: Path,
    occurrences_path: Path,
    sketches_path: Path,
    beam_cells_path: Path,
    output_dir: Path,
) -> int:
    required = [
        (dxf_path, "Reinforcement DXF"),
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
    paths.phase_d1_6a_dir.mkdir(parents=True, exist_ok=True)

    reassigned = _load_json(reassigned_path)
    ownership = _load_json(ownership_path)
    occurrences = _load_json(occurrences_path)
    sketches = _load_json(sketches_path)
    beam_cells = _load_json(beam_cells_path)

    if not all(
        isinstance(data, list)
        for data in (reassigned, ownership, occurrences, sketches, beam_cells)
    ):
        logger.error("JSON inputs must be lists")
        return 1

    auditor = AnnotationCoverageAuditor()
    occurrence_records, summary, validation, all_missing = auditor.audit(
        str(dxf_path.resolve()),
        reassigned,
        ownership,
        occurrences,
        sketches,
        beam_cells,
    )
    dxf_stats = {
        "dxf_text_entity_count": summary["dxf_text_entity_count"],
        "dxf_stirrup_spacing_count": summary["dxf_stirrup_spacing_count"],
        "dxf_anchorage_count": summary["dxf_anchorage_count"],
        "dxf_dimension_count": summary["dxf_dimension_count"],
    }
    report_text = auditor.build_report_text(
        occurrence_records, dxf_stats
    )

    _write_json(paths.annotation_coverage_audit, occurrence_records)
    _write_json(paths.annotation_coverage_summary, summary)
    _write_text(paths.annotation_coverage_report, report_text)
    _write_json(paths.annotation_coverage_validation, validation)

    AnnotationCoverageDebugExporter().export(
        missing_annotations=all_missing,
        output_path=paths.annotation_coverage_debug_dxf,
    )

    logger.info(
        "Phase D.1.6A complete: {:.1f}% coverage, status={}",
        validation["coverage_percent"],
        validation["status"],
    )

    top_missing = sorted(
        all_missing,
        key=lambda item: (-item["y"], item["x"], item["type"]),
    )[:20]

    print("\n--- Phase D.1.6A Summary ---")
    print(f"Total region texts: {validation['total_region_texts']}")
    print(f"Total owned annotations: {validation['owned_annotations']}")
    print(f"Total missing annotations: {validation['missing_annotations']}")
    print(f"Coverage: {validation['coverage_percent']}%")
    print(f"Status: {validation['status']}")
    print(f"DXF TEXT/MTEXT entities: {summary['dxf_text_entity_count']}")
    print(f"Stirrup spacing (@/C/C) in DXF: {summary['dxf_stirrup_spacing_count']}")
    print(f"Anchorage (Ld) in DXF: {summary['dxf_anchorage_count']}")
    print(f"Dimension-only texts in DXF: {summary['dxf_dimension_count']}")
    print(f"Texts outside ownership regions: {summary['texts_outside_regions']}")
    print("\nMissing by type:")
    for type_name, count in summary["missing_by_type"].items():
        if count:
            print(f"  {type_name}: {count}")
    print("\nTop 20 missing annotations:")
    for item in top_missing:
        display = item["clean_text"] or item["raw_text"]
        print(f"  [{item['type']}] {display} ({item['x']}, {item['y']})")
    if not top_missing:
        print("  (none)")
    print("----------------------------\n")

    return 0 if validation["status"] != "FAIL" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.dxf,
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
