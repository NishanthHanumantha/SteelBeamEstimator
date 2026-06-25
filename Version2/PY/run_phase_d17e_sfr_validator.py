"""Phase D.1.7E — SFR ownership validator (runs after D.1.7D, before D.2)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.validation.sfr_ownership_debug_exporter import SfrOwnershipDebugExporter
from src.validation.sfr_ownership_validator import SfrOwnershipValidator

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
        description="Phase D.1.7E — validate SIDE_FACE_REINF ownership before D.2.",
    )
    parser.add_argument(
        "--engineering-final",
        type=Path,
        default=paths.engineering_annotations_final,
        help="Final engineering annotations JSON (D.1.7D)",
    )
    parser.add_argument(
        "--sketches",
        type=Path,
        default=paths.beam_sketches_debug,
        help="Beam sketches debug JSON (Phase C debug)",
    )
    parser.add_argument(
        "--sketch-ownership",
        type=Path,
        default=paths.sketch_ownership,
        help="Sketch ownership JSON (Phase C.5)",
    )
    parser.add_argument(
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help="Reinforcement detail DXF for geometry classification",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        default="",
        help="Optional comma-separated beam marks for report accuracy only",
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


def _parse_ground_truth(value: str) -> Optional[List[str]]:
    if not value.strip():
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    paths = OutputPaths(args.output_dir)
    paths.phase_d17e_dir.mkdir(parents=True, exist_ok=True)

    for label, path in (
        ("engineering-final", args.engineering_final),
        ("sketches", args.sketches),
        ("sketch-ownership", args.sketch_ownership),
        ("dxf", args.dxf),
    ):
        if not path.exists():
            logger.error("{} not found: {}", label, path)
            return 1

    final_records = _load_json(args.engineering_final)
    sketches = _load_json(args.sketches)
    sketch_ownership = _load_json(args.sketch_ownership)

    if not isinstance(final_records, list):
        logger.error("engineering_annotations_final must be a list")
        return 1

    ground_truth = _parse_ground_truth(args.ground_truth)

    result = SfrOwnershipValidator().validate(
        final_records,
        sketches,
        sketch_ownership,
        str(args.dxf.resolve()),
        ground_truth_beams=ground_truth,
    )

    _write_json(paths.validated_sfr_annotations, result["validated_sfr"])
    _write_json(paths.validated_annotations_master, result["validated_master"])
    _write_json(paths.sfr_validation_report, result["report"])
    _write_text(paths.sfr_validation_report_txt, result["report_text"])

    SfrOwnershipDebugExporter().export(
        result["validated_sfr"],
        sketches,
        paths.sfr_ownership_debug_dxf,
    )

    report = result["report"]
    print("\n--- Phase D.1.7E SFR Validation Summary ---")
    print(f"Total SFR detected: {report['total_sfr_detected']}")
    print(f"Validated: {report['validated']}")
    print(f"Rejected: {report['rejected']}")
    print(f"Ambiguous: {report['ambiguous']}")
    print(f"Curved beam matches: {report['curved_beam_matches']}")
    if report["false_positive_candidates"]:
        print(f"False positive candidates: {', '.join(report['false_positive_candidates'])}")
    if report["false_negative_notes"]:
        print(f"Ground truth gaps: {', '.join(report['false_negative_notes'])}")
    print("-------------------------------------------\n")

    logger.info(
        "Phase D.1.7E complete: validated={}, rejected={}, ambiguous={}",
        report["validated"],
        report["rejected"],
        report["ambiguous"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
