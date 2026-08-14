"""Replay stored P2.5.7 live Vision audits. No Claude call unless --live."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import P257_OUTPUT


def p257_root(version10_root: Path) -> Path:
    return Path(version10_root) / "data" / "output" / P257_OUTPUT


def load_p257_audits(version10_root: Path) -> List[Dict[str, Any]]:
    path = p257_root(version10_root) / "vision_results.json"
    if not path.exists():
        path = p257_root(version10_root) / "vision" / "vision_results.json"
    if not path.exists():
        raise FileNotFoundError(f"P2.5.7 vision_results.json not found under {p257_root(version10_root)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("vision_results.json must be a list")
    return data


def load_p257_status(version10_root: Path) -> Path:
    return p257_root(version10_root) / "P2.5.7_STATUS.md"


__all__ = ["load_p257_audits", "load_p257_status", "p257_root"]
