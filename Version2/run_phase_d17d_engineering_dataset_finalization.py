"""Phase D.1.7D — engineering dataset finalization for Phase D.2."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.annotations.engineering_dataset_debug_exporter import (
    EngineeringDatasetDebugExporter,
)
from src.annotations.engineering_dataset_finalizer import EngineeringDatasetFinalizer
from src.annotations.engineering_dataset_validator import EngineeringDatasetValidator
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
        description="Phase D.1.7D — finalize engineering dataset for D.2.",
    )
    parser.add_argument(
        "--engineering-annotations",
        type=Path,
        default=paths.engineering_annotations,
        help="Engineering annotations JSON (D.1.7B)",
    )
    parser.add_argument(
        "--rejected-review",
        type=Path,
        default=paths.rejected_dataset_review,
        help="Rejected dataset review (D.1.7C)",
    )
    parser.add_argument(
        "--sfr-integrity",
        type=Path,
        default=paths.sfr_integrity_report,
        help="SFR integrity report (D.1.7C)",
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
    paths.phase_d1_7d_dir.mkdir(parents=True, exist_ok=True)

    if not args.engineering_annotations.exists():
        logger.error("engineering_annotations.json not found: {}", args.engineering_annotations)
        return 1

    engineering_records = _load_json(args.engineering_annotations)
    rejected_review = (
        _load_json(args.rejected_review) if args.rejected_review.exists() else None
    )
    sfr_integrity = (
        _load_json(args.sfr_integrity) if args.sfr_integrity.exists() else None
    )

    if not isinstance(engineering_records, list):
        logger.error("engineering_annotations must be a list")
        return 1

    result = EngineeringDatasetFinalizer().finalize(
        engineering_records,
        rejected_review,
        sfr_integrity,
    )
    validation = EngineeringDatasetValidator().validate(
        result,
        result["final_records"],
    )

    _write_json(paths.engineering_annotations_final, result["final_records"])
    _write_json(paths.fragment_resolution_report, result["fragment_resolution"])
    _write_json(paths.sfr_parsing_policy, result["sfr_parsing_policy"])
    _write_json(paths.d2_parser_policy, result["d2_parser_policy"])
    _write_json(paths.engineering_dataset_final_validation, validation)
    _write_json(paths.engineering_dataset_final_summary, result["summary"])
    _write_text(paths.engineering_dataset_final_report, result["report_text"])

    EngineeringDatasetDebugExporter().export(
        result["final_records"],
        result["deduplicated_entries"],
        result["fragment_resolution"].get("resolutions", []),
        paths.engineering_dataset_final_debug_dxf,
    )

    summary = result["summary"]
    print("\n--- Phase D.1.7D Finalization Summary ---")
    print(f"Total input annotations: {summary['total_input_annotations']}")
    print(f"Parser-ready annotations: {summary['parser_ready_annotations']}")
    print(f"Ignored fragments: {summary['ignored_fragments']}")
    print(f"Deduplicated entries removed: {summary['deduplicated_entries_removed']}")
    print(f"BAR: {summary['bar_count']}")
    print(f"STIRRUP: {summary['stirrup_count']}")
    print(f"ANCHORAGE: {summary['anchorage_count']}")
    print(f"SIDE_FACE_REINF: {summary['side_face_reinf_count']}")
    print(f"Questionable annotations: {summary['questionable_annotations']}")
    print(f"Readiness status: {summary['readiness_status']}")
    print(f"Validation: {validation['status']}")
    for check_name, passed in validation["checks"].items():
        print(f"  {check_name}: {'PASS' if passed else 'FAIL'}")
    print("----------------------------------------\n")

    logger.info(
        "Phase D.1.7D complete: readiness={}, validation={}",
        summary["readiness_status"],
        validation["status"],
    )
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
