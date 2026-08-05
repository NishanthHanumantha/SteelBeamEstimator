"""
T1.7.1 — Capture / locate original beam renders (read-only consumers).
MODEL_VERSION: 9.4.1

Does not modify existing renderer modules. May call them as black boxes.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

MODEL_VERSION = "9.4.1"


def load_dxf_renderer(engine_root: Path):
    """Import PhaseM.1 dxf_renderer without mutating its source."""
    path = (
        Path(engine_root)
        / "src"
        / "PhaseM.1_engineering_vision_dataset"
        / "dxf_renderer.py"
    )
    spec = importlib.util.spec_from_file_location("dxf_renderer_t171", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["dxf_renderer_t171"] = mod
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
        path = alt if alt.exists() else path
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    env = (data.get("by_beam") or {}).get(beam_id) or {}
    ext = env.get("extent")
    if not ext:
        return None
    return (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))


def locate_existing_original(
    output_root: Path,
    engine_root: Path,
    beam_id: str,
) -> Optional[Path]:
    """Prefer existing artefacts; never regenerate unless missing."""
    candidates = [
        Path(output_root)
        / "PhaseT16_entity_ownership"
        / "benchmark_compare"
        / f"{beam_id}_original_crop.png",
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
        / "PhaseT16_entity_ownership"
        / beam_id
        / "filtered_render.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def snapshot_original_render(
    *,
    engine_root: Path,
    run_root: Path,
    output_root: Path,
    beam_id: str,
    dest: Path,
    regenerate_if_missing: bool = True,
) -> Dict[str, Any]:
    """
    Copy or (if missing) black-box regenerate the original crop-driven render
    into *dest*. Existing renderer source is never edited.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = locate_existing_original(output_root, engine_root, beam_id)
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

    if not regenerate_if_missing:
        info["error"] = "no_existing_original"
        return info

    dxf = find_reinforcement_dxf(run_root)
    extent = load_extent(output_root, beam_id, engine_root)
    if not dxf or not extent:
        info["error"] = "missing_dxf_or_extent"
        return info
    mod = load_dxf_renderer(engine_root)
    mod.render_dxf_region_to_png(dxf, dest, extent, render_text=True)
    info["source"] = "regenerated_via_dxf_renderer_blackbox"
    info["regenerated"] = True
    info["extent"] = list(extent)
    return info
