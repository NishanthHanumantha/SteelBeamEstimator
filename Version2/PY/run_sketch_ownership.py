"""Phase C.5 — sketch ownership validation pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.grid.header_occurrence_exporter import HeaderOccurrenceExporter
from src.grid.sketch_ownership_auditor import SketchOwnershipAuditor
from src.grid.sketch_ownership_builder import SketchOwnershipBuilder
from src.grid.sketch_ownership_debug_exporter import SketchOwnershipDebugExporter
from src.grid.sketch_ownership_validator import SketchOwnershipValidator

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")


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
        description="Phase C.5 — validate sketch ownership per header occurrence.",
    )
    parser.add_argument(
        "-i",
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help=f"Reinforcement DXF (default: {DEFAULT_DXF})",
    )
    parser.add_argument(
        "--sketches",
        type=Path,
        default=paths.beam_sketches_debug,
        help=f"Input beam_sketches_debug.json (default: {paths.beam_sketches_debug})",
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


def run(
    dxf_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    paths = OutputPaths(output_dir)
    paths.phase_c5_dir.mkdir(parents=True, exist_ok=True)

    if not dxf_path.exists():
        logger.error("DXF not found: {}", dxf_path)
        return 1
    if not sketches_path.exists():
        logger.error("Sketches JSON not found: {}", sketches_path)
        return 1

    occurrences = HeaderOccurrenceExporter().extract_from_dxf(dxf_path)
    sketches = _load_json(sketches_path)
    if not isinstance(sketches, list):
        logger.error("Expected list in {}", sketches_path)
        return 1

    ownership, assignments = SketchOwnershipBuilder().assign(occurrences, sketches)

    auditor = SketchOwnershipAuditor()
    enriched_ownership, audits = auditor.enrich_ownership(
        ownership, occurrences, sketches
    )
    audit_stats = auditor.compute_stats(audits)
    warnings = auditor.find_long_distance_warnings(enriched_ownership)

    validation = SketchOwnershipValidator().validate(
        sketches,
        assignments,
        enriched_ownership,
        audit_stats,
        warnings,
        audits,
    )

    _write_json(paths.header_occurrences, occurrences)
    _write_json(paths.sketch_ownership, enriched_ownership)
    _write_json(paths.sketch_ownership_validation, validation)

    SketchOwnershipDebugExporter().export(
        occurrences=occurrences,
        sketches=sketches,
        ownership=enriched_ownership,
        output_path=paths.sketch_ownership_debug_dxf,
    )

    logger.info(
        "Phase C.5 complete: {} occurrence(s), {} sketch(s), "
        "ownership={}, audit={}",
        len(occurrences),
        validation["total_sketches"],
        validation["ownership_status"],
        validation["audit_status"],
    )
    return 0


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(args.dxf, args.sketches, args.output_dir)
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
