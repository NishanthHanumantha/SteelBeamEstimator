"""
T1.8.1 — Locate manual benchmark crops + DXF black-box helpers.
MODEL_VERSION: 9.5.1

Read-only consumers. Never edits existing renderer modules.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

MODEL_VERSION = "9.5.1"


def load_dxf_renderer(engine_root: Path):
    path = (
        Path(engine_root)
        / "src"
        / "PhaseM.1_engineering_vision_dataset"
        / "dxf_renderer.py"
    )
    spec = importlib.util.spec_from_file_location("dxf_renderer_t181", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["dxf_renderer_t181"] = mod
    spec.loader.exec_module(mod)
    return mod


def find_reinforcement_dxf(run_root: Path) -> Optional[Path]:
    for p in Path(run_root).rglob("*.dxf"):
        if "reinforc" in p.parent.name.lower() or "reinforc" in p.name.lower():
            return p
    return None


def load_extent(
    output_root: Path, beam_id: str, engine_root: Optional[Path] = None
) -> Optional[Tuple[float, float, float, float]]:
    path = (
        Path(output_root)
        / "PhaseT1_geometric_stirrup_evidence"
        / "geometry_envelopes.json"
    )
    if not path.exists() and engine_root:
        alt = (
            Path(engine_root)
            / "data"
            / "output"
            / "Track1_geometric_evidence"
            / "geometry_envelopes_Set1_benchmark.json"
        )
        if alt.exists():
            path = alt
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    env = (data.get("by_beam") or {}).get(beam_id) or {}
    ext = env.get("extent")
    if not ext:
        return None
    return (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))


def locate_manual_crop(
    output_root: Path, engine_root: Path, beam_id: str
) -> Optional[Path]:
    """Prefer T1.6 original crops / OpenCV crops as AutoCAD benchmark proxies."""
    candidates = [
        Path(engine_root)
        / "data"
        / "output"
        / "Track1_geometric_evidence"
        / "PhaseT16_entity_ownership"
        / "benchmark_compare"
        / f"{beam_id}_original_crop.png",
        Path(engine_root)
        / "data"
        / "output"
        / "Track1_geometric_evidence"
        / "t15_benchmark"
        / "after"
        / f"{beam_id}_crop.png",
        Path(output_root)
        / "PhaseT1_geometric_stirrup_evidence"
        / "opencv_renders"
        / f"{beam_id}_crop.png",
        Path(output_root)
        / "PhaseT171_graph_render_validation"
        / beam_id
        / "Original_Render.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def export_manual_image(
    *,
    engine_root: Path,
    run_root: Path,
    output_root: Path,
    beam_id: str,
    dest: Path,
) -> Dict[str, Any]:
    """Copy manual/benchmark crop into Comparison/{beam}_manual.png."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = locate_manual_crop(output_root, engine_root, beam_id)
    info: Dict[str, Any] = {
        "beam_id": beam_id,
        "path": str(dest),
        "source": None,
        "regenerated": False,
    }
    if src:
        shutil.copy2(src, dest)
        info["source"] = str(src)
        return info

    # Fallback: black-box DXF region with text (AutoCAD-like crop proxy)
    dxf = find_reinforcement_dxf(run_root)
    extent = load_extent(output_root, beam_id, engine_root)
    if not dxf or not extent:
        info["error"] = "missing_manual_and_dxf"
        return info
    mod = load_dxf_renderer(engine_root)
    mod.render_dxf_region_to_png(dxf, dest, extent, render_text=True)
    info["source"] = "regenerated_dxf_text_crop"
    info["regenerated"] = True
    info["extent"] = list(extent)
    return info
