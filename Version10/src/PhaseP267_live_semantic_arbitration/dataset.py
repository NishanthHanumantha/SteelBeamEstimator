"""Load the frozen P2.6.6 29-beam target population. Do not resample."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import crop_path as qa30_crop_path

from .config import (
    COVER_FULL,
    COVER_LAYER,
    FULLY_COVERED_DIAGNOSTIC_BEAMS,
    P266_OUTPUT_DIRNAME,
    ROLE_COVERAGE_GAP_BEAMS,
    TARGET_BEAMS,
)


def p266_output_root(version10_root: Path) -> Path:
    return Path(version10_root) / "data" / "output" / P266_OUTPUT_DIRNAME


def load_p266_targets(version10_root: Path) -> List[Dict[str, Any]]:
    path = p266_output_root(version10_root) / "target_records.json"
    if not path.exists():
        raise FileNotFoundError(f"missing P2.6.6 target manifest: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("P2.6.6 target_records.json is not a list")
    if len(data) != TARGET_BEAMS:
        raise ValueError(f"P2.6.6 target population is {len(data)}, expected {TARGET_BEAMS}")
    gap = sum(1 for r in data if r.get("longitudinal_coverage") == COVER_LAYER)
    full = sum(1 for r in data if r.get("longitudinal_coverage") == COVER_FULL)
    if gap != ROLE_COVERAGE_GAP_BEAMS or full != FULLY_COVERED_DIAGNOSTIC_BEAMS:
        raise ValueError(
            f"P2.6.6 coverage mix gap={gap} full={full}, "
            f"expected {ROLE_COVERAGE_GAP_BEAMS}/{FULLY_COVERED_DIAGNOSTIC_BEAMS}"
        )
    return data


def resolve_crop_path(version10_root: Path, target: Dict[str, Any]) -> Path:
    explicit = target.get("crop_path") or (target.get("context") or {}).get("crop_path")
    if explicit:
        p = Path(str(explicit))
        if p.exists():
            return p
    return qa30_crop_path(
        Path(version10_root),
        str(target.get("set_key") or ""),
        str(target.get("beam_id") or ""),
    )


def reference_class(target: Dict[str, Any]) -> str:
    sem = target.get("semantic") or {}
    return str(sem.get("decision") or "")


__all__ = [
    "load_p266_targets",
    "p266_output_root",
    "reference_class",
    "resolve_crop_path",
]
