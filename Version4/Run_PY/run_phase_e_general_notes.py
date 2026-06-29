"""Phase E — General Notes Intelligence Engine runner."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.general_notes.general_notes_pipeline import GeneralNotesPipeline

DEFAULT_INPUT = Path("data/general_notes")
DEFAULT_CONFIG = Path("config/general_notes.yaml")


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase E — General Notes Intelligence Engine.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=str(OUTPUT_ROOT),
        help="Output root (default: data/output)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT),
        help="General Notes DXF file or directory",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help="General notes config YAML path",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    result = GeneralNotesPipeline(
        OutputPaths(Path(args.output_dir)),
        input_path=args.input,
        config_path=args.config,
    ).run()
    summary = result["summary"]
    validation = result["validation"]
    print("\n" + "=" * 50)
    print("Phase E.3 Complete — Engineering Value Provenance & Traceability")
    print("=" * 50)
    print(f"Source: {summary['source_file']}")
    print(f"Project: {summary.get('project_name')} ({summary.get('project_name_source')})")
    print(f"Sheets: {', '.join(summary['sheet_ids'])}")
    print(f"Text entities: {summary['text_entity_count']}")
    print(f"Steel grades: {summary['steel_grade_count']}")
    print(f"Concrete grades: {summary['concrete_grade_count']}")
    print(f"Active LD table: {summary.get('active_development_table')}")
    print(f"Active steel grade: {summary.get('active_steel_grade')}")
    print(f"Structural spacer: {summary.get('structural_spacer_diameter_mm')} mm")
    print(f"Estimator spacer: {summary.get('estimator_spacer_diameter_mm')} mm @ {summary.get('estimator_spacer_spacing_mm')} mm")
    print(f"Ld entries: {summary['development_length_entry_count']}")
    print(f"Cover rows: {summary['cover_row_count']}")
    print(f"Bend rules: {summary['bend_rule_count']}")
    print(f"Anchorage rules: {summary['anchorage_rule_count']}")
    print(f"Validation: {summary['validation_status']}")
    for check in validation.get("checks", []):
        print(f"  {check['name']}: {check['status']}")
    print("=" * 50 + "\n")
    return 0 if summary["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(run())
