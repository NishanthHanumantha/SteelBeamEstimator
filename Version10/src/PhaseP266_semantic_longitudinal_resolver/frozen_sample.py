"""Load frozen P2.6.1 sample and parent P2.6.5 artefacts. Do not resample."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PhaseP264_selective_role_gap_gate.frozen_sample import (
    load_frozen_candidates as _load_cands,
    load_frozen_manifest as _load_manifest,
    load_frozen_observations as _load_obs,
    p261_output_root as _p261_root,
)

from .config import P265_OUTPUT_DIRNAME


def p261_output_root(version10_root: Path) -> Path:
    return _p261_root(version10_root)


def p265_output_root(version10_root: Path) -> Path:
    return Path(version10_root) / "data" / "output" / P265_OUTPUT_DIRNAME


def load_frozen_manifest(version10_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _load_manifest(version10_root)


def load_frozen_candidates(version10_root: Path) -> List[Dict[str, Any]]:
    return _load_cands(version10_root)


def load_frozen_observations(version10_root: Path) -> List[Dict[str, Any]]:
    return _load_obs(version10_root)


def load_p265_decisions(version10_root: Path) -> List[Dict[str, Any]]:
    path = p265_output_root(version10_root) / "gate_decisions.json"
    if not path.exists():
        raise FileNotFoundError(f"missing P2.6.5 decisions: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("P2.6.5 gate_decisions.json is not a list")
    return data


def candidates_for_beam(
    frozen_candidates: List[Dict[str, Any]], set_key: str, beam_id: str
) -> List[Dict[str, Any]]:
    return [
        c
        for c in frozen_candidates
        if c.get("set_key") == set_key and c.get("beam_id") == beam_id
    ]


__all__ = [
    "candidates_for_beam",
    "load_frozen_candidates",
    "load_frozen_manifest",
    "load_frozen_observations",
    "load_p265_decisions",
    "p261_output_root",
    "p265_output_root",
]
