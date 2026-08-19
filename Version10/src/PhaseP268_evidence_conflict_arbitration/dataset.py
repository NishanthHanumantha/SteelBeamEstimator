"""Load frozen P2.6.6 targets and optional P2.6.7 live decisions. Do not resample."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseP267_live_semantic_arbitration.dataset import load_p266_targets, p266_output_root, resolve_crop_path

from .config import P267_OUTPUT_DIRNAME, TARGET_BEAMS


def p267_output_root(version10_root: Path) -> Path:
    return Path(version10_root) / "data" / "output" / P267_OUTPUT_DIRNAME


def load_p267_live_index(version10_root: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    path = p267_output_root(version10_root) / "P2.6.7_LIVE_DECISIONS.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not isinstance(data, list):
        return out
    for row in data:
        if not isinstance(row, dict):
            continue
        out[(str(row.get("set_key") or ""), str(row.get("beam_id") or ""))] = row
    return out


__all__ = [
    "TARGET_BEAMS",
    "load_p266_targets",
    "load_p267_live_index",
    "p266_output_root",
    "p267_output_root",
    "resolve_crop_path",
]
