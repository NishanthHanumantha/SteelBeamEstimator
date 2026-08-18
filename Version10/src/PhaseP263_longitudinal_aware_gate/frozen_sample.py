"""Load the frozen P2.6.1 75-beam sample. Do not resample."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from PhaseP262_selective_vision_candidate_gate.frozen_sample import (
    load_frozen_candidates as _load_cands,
    load_frozen_manifest as _load_manifest,
    load_frozen_observations as _load_obs,
    p261_output_root as _p261_root,
)


def p261_output_root(version10_root: Path) -> Path:
    return _p261_root(version10_root)


def load_frozen_manifest(version10_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _load_manifest(version10_root)


def load_frozen_candidates(version10_root: Path) -> List[Dict[str, Any]]:
    return _load_cands(version10_root)


def load_frozen_observations(version10_root: Path) -> List[Dict[str, Any]]:
    return _load_obs(version10_root)


__all__ = [
    "load_frozen_candidates",
    "load_frozen_manifest",
    "load_frozen_observations",
    "p261_output_root",
]
