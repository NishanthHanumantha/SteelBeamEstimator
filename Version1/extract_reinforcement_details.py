"""CLI entry point for geometry-driven reinforcement detail extraction (Phase 3B.1)."""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from src.extractor.reinforcement_detail_extractor import ReinforcementDetailExtractor
from src.utils.entities_loader import EntitiesLoadError

DEFAULT_ENTITIES = Path("data/output/entities.json")
DEFAULT_DXF = Path("data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf")
DEFAULT_BEAM_LABELS = Path("data/output/beam_labels.json")
DEFAULT_OUTPUT = Path("data/output/reinforcement_detail_blocks.json")


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
    parser = argparse.ArgumentParser(
        description=(
            "Extract reinforcement detail blocks with sketch validation "
            "and ownership assignment (Phase 3B.3)."
        ),
    )
    parser.add_argument(
        "-e",
        "--entities",
        type=Path,
        default=DEFAULT_ENTITIES,
        help=f"Entities JSON (default: {DEFAULT_ENTITIES})",
    )
    parser.add_argument(
        "-d",
        "--dxf",
        type=Path,
        default=DEFAULT_DXF,
        help=f"Source DXF for geometry (default: {DEFAULT_DXF})",
    )
    parser.add_argument(
        "-b",
        "--beam-labels",
        type=Path,
        default=DEFAULT_BEAM_LABELS,
        help=f"Fallback beam labels JSON (default: {DEFAULT_BEAM_LABELS})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def save_blocks(blocks: list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(blocks, fh, indent=2, ensure_ascii=False)
    logger.info("Saved {} detail blocks to {}", len(blocks), output_path.resolve())


def run(
    entities_path: Path,
    dxf_path: Path,
    beam_labels_path: Path,
    output_path: Path,
) -> int:
    extractor = ReinforcementDetailExtractor()
    blocks = extractor.extract(entities_path, dxf_path, beam_labels_path)
    summary = extractor.build_summary(blocks)
    extractor.log_summary(summary)
    validation = extractor.validate(blocks)

    save_blocks(blocks, output_path)
    return 0 if validation["passed"] else 2


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(
            args.entities,
            args.dxf,
            args.beam_labels,
            args.output,
        )
    except (EntitiesLoadError, FileNotFoundError) as exc:
        logger.error("{}", exc)
        return 1
    except OSError as exc:
        logger.error("Failed to write output: {}", exc)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error: {}", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
