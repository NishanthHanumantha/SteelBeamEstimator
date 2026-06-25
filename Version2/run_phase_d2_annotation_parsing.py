"""Phase D.2 — annotation parsing and normalization pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.parsing.annotation_parsing_debug_exporter import AnnotationParsingDebugExporter
from src.parsing.annotation_parsing_pipeline import AnnotationParsingPipeline
from src.parsing.annotation_parsing_validator import AnnotationParsingValidator


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
        description="Phase D.2 — parse engineering annotations into structured objects.",
    )
    parser.add_argument(
        "--engineering-final",
        type=Path,
        default=paths.engineering_dataset_phase_d17f,
        help="Engineering dataset JSON (D.1.7F; falls back to D.1.7E / D.1.7D)",
    )
    parser.add_argument(
        "--parser-policy",
        type=Path,
        default=paths.d2_parser_policy,
        help="D.2 parser policy JSON",
    )
    parser.add_argument(
        "--sfr-policy",
        type=Path,
        default=paths.sfr_parsing_policy,
        help="SFR parsing policy JSON",
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
    paths.phase_d2_dir.mkdir(parents=True, exist_ok=True)

    if not args.engineering_final.exists():
        fallback_e = paths.validated_annotations_master
        fallback_d = paths.engineering_annotations_final
        if fallback_e.exists():
            logger.warning(
                "engineering_dataset_phase_d17f not found; using D.1.7E validated master: {}",
                fallback_e,
            )
            args.engineering_final = fallback_e
        elif fallback_d.exists():
            logger.warning(
                "No D.1.7F/D.1.7E input found; using D.1.7D final dataset: {}",
                fallback_d,
            )
            args.engineering_final = fallback_d
        else:
            logger.error(
                "No annotation input found (D.1.7F, D.1.7E, or D.1.7D): {}",
                args.engineering_final,
            )
            return 1

    final_records = _load_json(args.engineering_final)
    sfr_policy = _load_json(args.sfr_policy) if args.sfr_policy.exists() else None

    if not isinstance(final_records, list):
        logger.error("engineering_annotations_final must be a list")
        return 1

    result = AnnotationParsingPipeline().parse(final_records, sfr_policy)
    validation = AnnotationParsingValidator().validate(result)

    _write_json(paths.parsed_bars, result["bars"])
    _write_json(paths.parsed_stirrups, result["stirrups"])
    _write_json(paths.parsed_anchorage, result["anchorage"])
    _write_json(paths.parsed_side_face_reinf, result["side_face_reinf"])
    _write_json(paths.parsed_annotations_master, result["master"])
    _write_json(paths.annotation_parsing_summary, result["summary"])
    _write_json(paths.annotation_parsing_validation, validation)
    _write_text(paths.annotation_parsing_report, result["report_text"])

    parsed_for_debug = [r for r in result["master"] if r.get("parser_status") == "PARSED"]
    AnnotationParsingDebugExporter().export(parsed_for_debug, paths.annotation_parsing_debug_dxf)

    summary = result["summary"]
    print("\n--- Phase D.2 Parsing Summary ---")
    print(f"Parser-ready input: {summary['parser_ready_input_count']}")
    print(f"Parsed successfully: {summary['parsed_successfully']}")
    print(f"Failed parses: {summary['failed_parses']}")
    print(f"Coverage: {summary['coverage_pct']}%")
    print(f"BAR: {summary['bar_count']}")
    print(f"STIRRUP: {summary['stirrup_count']}")
    print(f"ANCHORAGE: {summary['anchorage_count']}")
    print(f"SIDE_FACE_REINF: {summary['side_face_reinf_count']}")
    print(f"Validation: {validation['status']}")
    print(f"READY_FOR_PHASE_E: {validation['ready_for_phase_e']}")
    print("---------------------------------\n")

    logger.info(
        "Phase D.2 complete: parsed={}, coverage={}%, status={}",
        summary["parsed_successfully"],
        summary["coverage_pct"],
        validation["status"],
    )
    return 0 if validation["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
