"""Phase D.1.7A — DIMENSION text source audit (read-only investigation)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.dimension_source_auditor import DimensionSourceAuditor
from src.annotations.dimension_source_debug_exporter import DimensionSourceDebugExporter
from src.annotations.dimension_source_validator import DimensionSourceValidator

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
        description="Phase D.1.7A — audit DIMENSION entity text sources.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=None,
        help="Reinforcement DXF (default: first *.dxf in data/reinforcement/)",
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


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        dxf_path = resolve_dxf_path(args.dxf)
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        return 1

    required = [
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
    paths.phase_d1_7a_dir.mkdir(parents=True, exist_ok=True)

    ownership = _load_json(args.ownership)
    occurrences = _load_json(args.occurrences)
    sketches = _load_json(args.sketches)
    beam_cells = _load_json(args.beam_cells)

    if not all(
        isinstance(data, list)
        for data in (ownership, occurrences, sketches, beam_cells)
    ):
        logger.error("JSON inputs must be lists")
        return 1

    auditor = DimensionSourceAuditor()
    result = auditor.audit(
        str(dxf_path),
        ownership,
        occurrences,
        sketches,
        beam_cells,
    )

    validation = DimensionSourceValidator().validate(
        result["records"],
        result["summary"],
        result["repeated_values"],
    )

    _write_json(paths.dimension_source_audit, result["records"])
    _write_json(paths.dimension_source_summary, result["summary"])
    _write_json(
        paths.dimension_source_repeated_values,
        result["repeated_values"],
    )
    _write_json(paths.dimension_source_validation, validation)
    _write_text(paths.dimension_source_report, result["report_text"])

    DimensionSourceDebugExporter().export(
        result["records"],
        paths.dimension_source_debug_dxf,
    )

    summary = result["summary"]
    repeated = result["repeated_values"]

    print("\n--- Phase D.1.7A Summary ---")
    print(f"Total DIMENSION entities audited: {summary['total_dimensions']}")
    print(f"ENGINEERING_TEXT: {summary['engineering_text_count']}")
    print(f"MEASUREMENT_VALUE: {summary['measurement_value_count']}")
    print(f"UNKNOWN_SOURCE: {summary['unknown_source_count']}")
    print(f"Validation: {validation['status']}")
    print("\nTop repeated values:")
    for item in repeated[:10]:
        print(f"  {item['value']}: {item['count']} ({item['source_type']})")
    print("\nRoot cause of 687:")
    for item in repeated:
        if item["value"] == "687":
            inv = item["investigation"]
            print(f"  why: {inv['why_appearing']}")
            print(f"  from actual_measurement: {inv['from_actual_measurement']}")
            print(f"  displayed: {inv['displayed_in_drawing']}")
            break
    print(f"\nRecommendation: {result['recommendation']}")
    print("----------------------------\n")

    logger.info(
        "Phase D.1.7A complete: {} audited, status={}",
        summary["total_dimensions"],
        validation["status"],
    )
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
