"""Phase F — Framing Plan Intelligence (F.1–F.7) and G.1 runner."""

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
        description="Phase F (F.1–F.7) and Phase G.1 reinforcement loading.",
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
    reinforcement_validation = result.get("reinforcement_validation", {})
    drawing_identity_validation = result.get("drawing_identity_validation", {})
    drawing_set_validation = result.get("drawing_set_validation", {})
    drawing_set_state_validation = result.get("drawing_set_state_validation", {})
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
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1")
    print("Floor Reinforcement Loading")
    print("=" * 52)
    reg = model.get("reinforcement_registry", {})
    print(f"Reinforcement Workspaces: {len(model.get('reinforcement_workspaces', []))}")
    print(f"Documents Loaded: {reg.get('document_count', 0)}")
    print(f"Validation: {reinforcement_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1.1")
    print("Drawing Identity & Floor Detection")
    print("=" * 52)
    drawing_reg = model.get("drawing_registry", {})
    ws_mgr = model.get("workspace_manager", {})
    print(f"Drawings Identified: {drawing_reg.get('drawing_count', 0)}")
    print(f"Floor Source: {ws_mgr.get('floor_source', '?')}")
    floors = model.get("project_workspace", {}).get("floors", [])
    if floors:
        print(f"Detected Floor: {floors[0].get('floor_name', '?')} ({floors[0].get('floor_id', '?')})")
    print(f"Validation: {drawing_identity_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1.2")
    print("Drawing Set Architecture")
    print("=" * 52)
    set_reg = model.get("drawing_set_registry", {})
    print(f"Drawing Sets: {set_reg.get('drawing_set_count', 0)}")
    for ds in model.get("drawing_sets", []):
        print(f"  {ds.get('drawing_set_id')} — {ds.get('floor_name')} ({ds.get('status')})")
    print(f"Validation: {drawing_set_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1.3")
    print("Drawing Set Lifecycle & Beam Index")
    print("=" * 52)
    indices = model.get("beam_indices", [])
    total_beams = sum(i.get("beam_count", 0) for i in indices)
    print(f"Drawing Sets: {len(model.get('drawing_sets', []))}")
    print(f"Beams Indexed: {total_beams}")
    for ds in model.get("drawing_sets", []):
        ver = ds.get("drawing_set_version", {})
        print(
            f"  {ds.get('drawing_set_id')} v{ver.get('drawing_set_version', '?')} "
            f"loading={ds.get('loading_state', '?')}"
        )
    print(f"Validation: {drawing_set_state_validation.get('status', 'SKIP')}")
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
    if reinforcement_validation.get("status") == "FAIL":
        failed = True
    if drawing_identity_validation.get("status") == "FAIL":
        failed = True
    if drawing_set_validation.get("status") == "FAIL":
        failed = True
    if drawing_set_state_validation.get("status") == "FAIL":
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
