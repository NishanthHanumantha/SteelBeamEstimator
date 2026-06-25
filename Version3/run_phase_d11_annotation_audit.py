"""Phase D.1.1 — annotation ownership audit (read-only validation)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT

from src.annotations.annotation_ownership_auditor import AnnotationOwnershipAuditor
from src.annotations.annotation_ownership_debug_exporter import (
    AnnotationOwnershipDebugExporter,
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
        description="Phase D.1.1 — audit annotation-to-sketch ownership quality.",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=paths.beam_annotations_raw,
        help=f"Raw annotations JSON (default: {paths.beam_annotations_raw})",
    )
    parser.add_argument(
        "--sketches",
        type=Path,
        default=paths.beam_sketches_debug,
        help=f"Sketch geometry JSON (default: {paths.beam_sketches_debug})",
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
    annotations_path: Path,
    sketches_path: Path,
    output_dir: Path,
) -> int:
    if not annotations_path.exists():
        logger.error("Annotations JSON not found: {}", annotations_path)
        return 1
    if not sketches_path.exists():
        logger.error("Sketches JSON not found: {}", sketches_path)
        return 1

    paths = OutputPaths(output_dir)
    paths.phase_d1_1_dir.mkdir(parents=True, exist_ok=True)

    annotations_raw = _load_json(annotations_path)
    sketches = _load_json(sketches_path)
    if not isinstance(annotations_raw, list) or not isinstance(sketches, list):
        logger.error("Expected list inputs for annotations and sketches")
        return 1

    auditor = AnnotationOwnershipAuditor()
    audit_records = auditor.audit(annotations_raw, sketches)
    validation = auditor.build_validation(audit_records)
    summary_text = auditor.build_summary_text(audit_records)

    _write_json(paths.annotation_ownership_audit, audit_records)
    _write_json(paths.annotation_ownership_validation, validation)
    _write_text(paths.annotation_ownership_summary, summary_text)

    AnnotationOwnershipDebugExporter().export(
        audit_records=audit_records,
        sketches=sketches,
        output_path=paths.annotation_ownership_debug_dxf,
    )

    logger.info(
        "Phase D.1.1 complete: {} annotation(s), status={}",
        validation["total_annotations"],
        validation["status"],
    )

    print("\n--- Phase D.1.1 Summary ---")
    print(f"Total annotations: {validation['total_annotations']}")
    print(f"High confidence: {validation['high_confidence']}")
    print(f"Medium confidence: {validation['medium_confidence']}")
    print(f"Low confidence: {validation['low_confidence']}")
    print(f"Suspicious: {validation['suspicious']}")
    print(f"Validation status: {validation['status']}")
    print("\nTop 10 suspicious annotations:")
    for item in validation["suspicious_annotations"][:10]:
        preview = item["annotation"].replace("\\P", " ").strip()
        if preview.startswith("\\A1;"):
            preview = preview[4:]
        if len(preview) > 40:
            preview = preview[:37] + "..."
        print(
            f"  {item['beam_mark']} {item['sketch_id']} "
            f"{preview} — {item['distance_mm']} mm"
        )
    print("---------------------------\n")

    return 0 if validation["status"] != "FAIL" else 1


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(args.annotations, args.sketches, args.output_dir)
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
