"""Load the frozen P2.6.1 75-beam sample. Do not resample."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .config import FROZEN_SAMPLE_BEAMS, P261_OUTPUT_DIRNAME, SAMPLE_SEED


def p261_output_root(version10_root: Path) -> Path:
    return Path(version10_root) / "data" / "output" / P261_OUTPUT_DIRNAME


def load_frozen_manifest(version10_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    root = p261_output_root(version10_root)
    path = root / "sampling" / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"frozen P2.6.1 manifest missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    summary = doc.get("summary") or {}
    regions = list(doc.get("regions") or [])
    if int(summary.get("seed") or 0) != SAMPLE_SEED:
        raise ValueError(f"frozen sample seed mismatch: {summary.get('seed')} != {SAMPLE_SEED}")
    if len(regions) != FROZEN_SAMPLE_BEAMS:
        raise ValueError(f"frozen sample size mismatch: {len(regions)} != {FROZEN_SAMPLE_BEAMS}")
    return regions, summary


def load_frozen_candidates(version10_root: Path) -> List[Dict[str, Any]]:
    path = p261_output_root(version10_root) / "candidates" / "all_candidates.json"
    if not path.exists():
        raise FileNotFoundError(f"frozen P2.6.1 candidates missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_frozen_observations(version10_root: Path) -> List[Dict[str, Any]]:
    path = p261_output_root(version10_root) / "benchmark" / "observations.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "load_frozen_candidates",
    "load_frozen_manifest",
    "load_frozen_observations",
    "p261_output_root",
]
