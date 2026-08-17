"""Locate Fourth/Fifth/Sixth ownership, R1.3, crops, and (eval-only) workbooks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator

from .config import SET_KEYS


def drawing_set_name(set_key: str) -> str:
    return f"{set_key} Set Drawings"


def ownership_path(version10_root: Path, set_key: str) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / f"{set_key}_Set_Drawings"
        / "EngineeringSummaries"
        / "BeamOwnership.json"
    )


def crop_path(version10_root: Path, set_key: str, beam_id: str) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / f"{set_key}_Set_Drawings"
        / "RenderedCrops"
        / "shared_renders"
        / f"{beam_id}_render.png"
    )


def production_paths(version10_root: Path, set_key: str) -> Dict[str, Path]:
    locator = ArtefactLocator(version10_root)
    art = locator.locate_set(set_key)
    out_root = art.output_root
    paths: Dict[str, Path] = {}
    if out_root is not None:
        paths.update(
            {
                "r13_models": out_root
                / "PhaseR1.3_pipeline_integration"
                / "beam_reinforcement_models_production.json",
                "model_excel": out_root / "Production_Output" / "Estimation_Output.xlsx",
                "bbs_summary": out_root / "Production_Output" / "bbs_summary.json",
            }
        )
    return paths


def load_ownership(version10_root: Path, set_key: str) -> Dict[str, Any]:
    p = ownership_path(version10_root, set_key)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load_r13_index(version10_root: Path, set_key: str) -> Dict[str, Dict[str, Any]]:
    paths = production_paths(version10_root, set_key)
    r13_path = paths.get("r13_models")
    if r13_path is None or not Path(r13_path).exists():
        return {}
    doc = json.loads(Path(r13_path).read_text(encoding="utf-8"))
    return {m.get("beam_id"): m for m in (doc.get("models") or []) if isinstance(m, dict)}


def fingerprint_production_paths(version10_root: Path) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    for key in SET_KEYS:
        paths = production_paths(version10_root, key)
        prefix = key.lower()
        for name, path in paths.items():
            out[f"{prefix}_{name}"] = path
    return out


__all__ = [
    "crop_path",
    "drawing_set_name",
    "fingerprint_production_paths",
    "load_ownership",
    "load_r13_index",
    "ownership_path",
    "production_paths",
]
