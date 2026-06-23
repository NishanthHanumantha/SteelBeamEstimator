"""CLI entry point for the DXF entity extraction engine."""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from src.parser.dxf_reader import DxfReader, DxfReadError
from src.parser.entity_extractor import EntityExtractor


DEFAULT_OUTPUT = Path("data/output/entities.json")


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
        description="Extract structural entities from AutoCAD DXF files.",
    )
    parser.add_argument(
        "dxf_path",
        type=Path,
        help="Path to the input DXF file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def save_entities(entities: list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entities": entities, "count": len(entities)}

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    logger.info("Saved {} entities to {}", len(entities), output_path.resolve())


def run(dxf_path: Path, output_path: Path) -> int:
    reader = DxfReader(dxf_path)
    doc = reader.read()

    modelspace = reader.get_modelspace(doc)
    if modelspace is None:
        logger.error("Could not open modelspace")
        return 1

    extractor = EntityExtractor()
    entities = extractor.extract(modelspace)

    save_entities(entities, output_path)
    return 0


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        return run(args.dxf_path, args.output)
    except DxfReadError as exc:
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
