"""Ensure Version10 and src are importable without mutating engineering packages."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
_V10 = _SRC.parent


def ensure_src_on_path() -> Path:
    for path in (str(_V10), str(_SRC)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return _V10


ENGINE_ROOT = _V10
SRC_ROOT = _SRC
