"""Phase F — Framing Plan Intelligence (F.1–F.7) runner."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.framing.beam_geometry_pipeline import BeamGeometryPipeline

DEFAULT_INPUT = Path("data/framing")
DEFAULT_CONFIG = Path("config/framing.yaml")


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase F — Framing Plan Intelligence (F.1–F.7).",
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
        help="Framing plan DXF file or directory",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help="Framing config YAML path",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    result = BeamGeometryPipeline(
        OutputPaths(Path(args.output_dir)),
        input_path=args.input,
        config_path=args.config,
    ).run()
    workspace_validation = result["workspace_validation"]
    model = result["model"]
    svc = model.get("engineering_services_registry", {})

    print("\n" + "=" * 52)
    print("PHASE F.7")
    print("Project Workspace & Engineering Services")
    print("=" * 52)
    print(f"Projects: {1 if model.get('project_workspace') else 0}")
    print(f"General Notes: {1 if model.get('project_workspace', {}).get('general_notes') else 0}")
    print(f"Floors: {model.get('floor_registry', {}).get('floor_count', 0)}")
    print(f"Beam Contexts: {len(model.get('beam_engineering_contexts', []))}")
    print(f"Engineering Services: {svc.get('service_count', 0)}")
    print(f"Validation: {workspace_validation['status']}")
    print("=" * 52 + "\n")

    failed = any(
        result[k]["status"] == "FAIL"
        for k in (
            "f1_validation",
            "dimension_validation",
            "support_validation",
            "section_validation",
            "length_validation",
            "graph_validation",
            "context_validation",
            "workspace_validation",
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
