"""Phase D.1.6B — DXF entity-type survey (read-only investigation)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.dxf.dxf_entity_type_debug_exporter import DxfEntityTypeDebugExporter
from src.dxf.dxf_entity_type_survey import DxfEntityTypeSurvey

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
        description="Phase D.1.6B — survey text-bearing DXF entity types.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=None,
        help="Reinforcement DXF file (default: first *.dxf in data/reinforcement/)",
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


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    logger.info("Wrote {}", path.resolve())


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    logger.info("Wrote {}", path.resolve())


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        dxf_path = resolve_dxf_path(args.dxf)
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    if not dxf_path.exists():
        logger.error("DXF file not found: {}", dxf_path)
        return 1

    output_dir = args.output_dir
    paths = OutputPaths(output_dir)
    paths.phase_d1_6b_dir.mkdir(parents=True, exist_ok=True)

    survey = DxfEntityTypeSurvey()
    result = survey.survey(str(dxf_path))

    _write_json(paths.dxf_entity_type_inventory, result["inventory"])
    _write_json(paths.dxf_text_inventory, result["text_inventory"])
    _write_json(paths.dxf_pattern_search, result["pattern_search"])

    summary_output = dict(result["summary"])
    _write_json(paths.dxf_entity_type_summary, summary_output)
    _write_text(paths.dxf_entity_type_report, result["report_text"])
    _write_json(
        paths.dxf_entity_type_validation, result["validation"]
    )

    DxfEntityTypeDebugExporter().export(
        result["pattern_search"],
        paths.dxf_entity_type_debug_dxf,
    )

    validation = result["validation"]
    summary = result["summary"]
    inventory = result["inventory"]

    print("\n--- Phase D.1.6B Summary ---")
    print(f"DXF: {dxf_path.name}")
    print("Entity inventory:")
    for entity_type, count in inventory.items():
        print(f"  {entity_type}: {count}")
    print(f"Total text-bearing entities: {validation['total_text_entities_found']}")
    print(f"Pattern matches found: {validation['pattern_matches_found']}")
    print(f"Stirrup entity types: {', '.join(summary['stirrup_entity_types']) or 'none'}")
    print(
        f"Anchorage entity types: {', '.join(summary['anchorage_entity_types']) or 'none'}"
    )
    print(
        f"Dimension entity types: {', '.join(summary['dimension_entity_types']) or 'none'}"
    )
    print(f"D.1 extracts: {', '.join(summary['extracted_by_d1']) or 'none'}")
    print(
        f"Not extracted by D.1: {', '.join(summary['not_extracted_by_d1']) or 'none'}"
    )
    print(f"Recommendation: {summary['recommendation']}")
    print(f"Status: {validation['status']}")
    print("----------------------------\n")

    logger.info(
        "Phase D.1.6B complete: {} text entities, status={}",
        validation["total_text_entities_found"],
        validation["status"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
