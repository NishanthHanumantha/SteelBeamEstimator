"""Phase D.1.7C — engineering annotation integrity audit (read-only)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.annotations.engineering_annotation_integrity_auditor import (
    EngineeringAnnotationIntegrityAuditor,
)
from src.annotations.engineering_annotation_integrity_debug_exporter import (
    EngineeringAnnotationIntegrityDebugExporter,
)
from src.annotations.engineering_annotation_integrity_validator import (
    EngineeringAnnotationIntegrityValidator,
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
        description="Phase D.1.7C — integrity audit of engineering annotations.",
    )
    parser.add_argument(
        "--engineering-annotations",
        type=Path,
        default=paths.engineering_annotations,
        help="Engineering annotations JSON (D.1.7B output)",
    )
    parser.add_argument(
        "--rejected-annotations",
        type=Path,
        default=paths.rejected_measurement_annotations,
        help="Rejected measurement annotations JSON",
    )
    parser.add_argument(
        "--types-extended",
        type=Path,
        default=paths.annotation_types_extended,
        help="Extended classification JSON (reference)",
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
    paths.phase_d1_7c_dir.mkdir(parents=True, exist_ok=True)

    required = [
        (args.engineering_annotations, "engineering_annotations.json"),
        (args.rejected_annotations, "rejected_measurement_annotations.json"),
    ]
    for path, label in required:
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    engineering_records = _load_json(args.engineering_annotations)
    rejected_annotations = _load_json(args.rejected_annotations)

    types_extended = None
    if args.types_extended.exists():
        types_extended = _load_json(args.types_extended)

    if not isinstance(engineering_records, list) or not isinstance(
        rejected_annotations, list
    ):
        logger.error("Engineering and rejected inputs must be lists")
        return 1

    audit_result = EngineeringAnnotationIntegrityAuditor().audit(
        engineering_records,
        rejected_annotations,
        types_extended,
    )
    validation = EngineeringAnnotationIntegrityValidator().validate(audit_result)

    integrity_audit_payload = {
        "fragments": audit_result["fragments"],
        "duplicates": audit_result["duplicates"],
        "parser_readiness": audit_result["parser_readiness"],
        "summary": audit_result["summary"],
    }
    _write_json(paths.engineering_annotation_integrity_audit, integrity_audit_payload)
    _write_json(paths.stirrup_integrity_report, audit_result["stirrups"])
    _write_json(paths.anchorage_integrity_report, audit_result["anchorage"])
    _write_json(paths.sfr_integrity_report, audit_result["sfr"])
    _write_json(
        paths.duplicate_engineering_annotations,
        audit_result["duplicates"],
    )
    _write_json(
        paths.type_consistency_report,
        audit_result["type_consistency"],
    )
    _write_json(
        paths.rejected_dataset_review,
        audit_result["rejected_review"],
    )
    _write_json(
        paths.parser_readiness_assessment,
        audit_result["parser_readiness"],
    )
    _write_json(
        paths.engineering_annotation_integrity_summary,
        audit_result["summary"],
    )
    _write_text(
        paths.engineering_annotation_integrity_report,
        audit_result["report_text"],
    )
    _write_json(
        paths.engineering_annotation_integrity_validation,
        validation,
    )

    EngineeringAnnotationIntegrityDebugExporter().export(
        audit_result,
        paths.engineering_annotation_integrity_debug_dxf,
    )

    summary = audit_result["summary"]
    readiness = audit_result["parser_readiness"]

    print("\n--- Phase D.1.7C Integrity Audit Summary ---")
    print(f"1. Truncated fragments found: {summary['truncated_fragments_found']}")
    print(f"   Suspicious fragments: {summary['suspicious_fragments_found']}")
    print(f"2. Incomplete stirrups: {summary['incomplete_stirrups_found']}")
    print(f"   Invalid stirrups: {summary['invalid_stirrups_found']}")
    print(f"3. Invalid anchorage: {summary['invalid_anchorage_entries_found']}")
    print(f"   Suspicious anchorage: {summary['suspicious_anchorage_entries_found']}")
    print(f"4. Invalid SFR: {summary['invalid_sfr_entries_found']}")
    print(f"   Partial SFR: {summary['partial_sfr_entries_found']}")
    print(f"5. Duplicate ownership issues: {summary['duplicate_ownership_issues']}")
    print(f"   Duplicate sketch entries: {summary['duplicate_sketch_entries']}")
    print(f"6. Type mismatches: {summary['type_mismatches']}")
    print(f"7. False rejections: {summary['false_rejections']}")
    print(f"8. Parser readiness score: {summary['parser_readiness_score']}")
    print(f"   Parser-ready: {readiness['parser_ready_annotations']}/{readiness['total_engineering_annotations']}")
    print(f"   Questionable: {readiness['questionable_annotations']} ({readiness['questionable_pct']}%)")
    print(f"9. Validation status: {validation['status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print("--------------------------------------------\n")

    logger.info(
        "Phase D.1.7C complete: readiness={}, recommendation={}",
        summary["parser_readiness_score"],
        summary["recommendation"],
    )
    return 0 if validation["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
